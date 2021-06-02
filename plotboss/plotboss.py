import os
import shutil
import importlib.resources
from typing import final
from plotboss.plotview import PlotView
import time
from basepy.config import settings
from .job import PlotJob
from .plotview import PlotView
from .plotlog import PlotLogParser
import time
import threading
from loguru import logger
import sys
import pendulum
from .utils import time_format, get_k32_plotsize

class PlotBoss():
    def __init__(self):
        self.work_dir = os.path.abspath(settings.main.get('work_dir', './plotboss_data'))
        self.max_jobs = settings.main.get('max_jobs', -1)
        self.final_paths = settings.get('final_dir', [])
        self.init_work_dir()
        self.running_jobs = []
        self.waiting_jobs = []
        self.completed_jobs = []
        self.completed_logs = []
        self.completed_statistics = {}
        self.running_info = {}
        self.plotting_config = {}
        self.load_plotting_config()
        self.temp_drives = set()
        self.final_drives = set()
        self.drive_statistics = {}
        self.job_statistics = {}

    def init_work_dir(self):
        if not os.path.exists(self.work_dir):
            os.makedirs(self.work_dir)
        logs_dir = os.path.join(self.work_dir, 'logs')
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)

    def load_plotting_config(self):
        plotting_config_list = settings.get('jobs', [])
        for conf in plotting_config_list:
            self.plotting_config[conf['tmp_dir']] = conf


    def load_jobs(self):
        jobs = PlotJob.get_running_jobs()
        for job in jobs:
            logger.debug('jobs, {logfile}', logfile=job.logfile)
            if job.logfile != None:
                self.running_jobs.append(job)

    def load_completed(self):
        log_dir = os.path.join(self.work_dir, 'logs')
        log_files = []
        completed_logs = []
        with os.scandir(log_dir) as it:
            for entry in it:
                if entry.name.endswith('.log') and entry.is_file():
                    log_files.append(os.path.join(log_dir, entry.name))
        for logf in log_files:
            with open(logf, 'r') as f:
                logparser = PlotLogParser()
                logparser.feed(f.readlines())
                if logparser.completed:
                    completed_logs.append(logparser)
        self.completed_logs = completed_logs
        self.update_completed_statistics()

    def update_completed_statistics(self):
        logs_num = len(self.completed_logs)
        statistics = {'today':0, 'yesterday':0, 'last_7':0,
            'all':logs_num,
            'days': 0,
            'average_duration': 0}
        if logs_num == 0:
            self.completed_statistics = statistics
            return
        today = pendulum.today()
        today_completed = list(filter(lambda x: x.complete_time >= today, self.completed_logs))
        statistics['today'] = len(today_completed)

        yesterday = pendulum.yesterday()
        yesterday_completed = list(filter(lambda x: x.complete_time >= yesterday and x.complete_time < today, self.completed_logs))
        statistics['yesterday'] = len(yesterday_completed)

        last7 = pendulum.now().subtract(days=7)
        last7_completed = list(filter(lambda x: x.complete_time >= last7, self.completed_logs))
        statistics['last_7'] = len(last7_completed)

        sorted_completed = sorted(self.completed_logs, key=lambda x: x.start_time)
        first_time = sorted_completed[0].start_time
        statistics['days'] = (pendulum.now() - first_time).days + 1

        average_duration = sum(map(lambda x: x.total_time, last7_completed))/len(last7_completed)
        statistics['average_duration'] = time_format(average_duration)

        self.completed_statistics = statistics

    def load_drives(self):
        for final_dir in self.final_paths:
            self.final_drives.add(os.path.splitdrive(final_dir)[0])
        for tmp_dir, conf in self.plotting_config.items():
            tmp_drive = os.path.splitdrive(tmp_dir)[0]
            self.temp_drives.add(tmp_drive)
            tmp2_dir = conf.get('tmp2_dir', None)
            if tmp2_dir:
                tmp2_drive = os.path.splitdrive(tmp2_dir)[0]
                self.temp_drives.add(tmp2_drive)
        for job in self.running_jobs:
            self.temp_drives.add(os.path.splitdrive(job.tmp_dir)[0])
            self.temp_drives.add(os.path.splitdrive(job.tmp2_dir)[0])
            self.final_drives.add(os.path.splitdrive(job.final_dir)[0])


    def update_statistics(self):
        while True:
            drive_statistics = {}
            for drive in self.temp_drives:
                try:
                    total, used, free = shutil.disk_usage(drive)
                except:
                    continue
                usage = used*100/total
                drive_statistics[drive] = {'drive':drive, 'total':total, 'used':used,
                    'free':free, 'type':'tmp', 'usage':usage, 'jobs':set()}
            for drive in self.final_drives:
                if drive in drive_statistics:
                    drive_statistics[drive]['type'] = 'tmp,final'
                    continue
                try:
                    total, used, free = shutil.disk_usage(drive)
                except:
                    continue
                usage = used*100/total
                drive_statistics[drive] = {'drive':drive, 'total':total, 'used':used,
                    'free':free, 'type':'final', 'usage':usage, 'jobs':set()}

            for job in self.running_jobs:
                for some_dir in [job.tmp_dir, job.tmp2_dir, job.final_dir]:
                    some_drive = os.path.splitdrive(some_dir)[0]
                    if some_drive in drive_statistics:
                        drive_statistics[some_drive]['jobs'].add(job.job_id)

            self.drive_statistics = drive_statistics
            time.sleep(10)

    def manage_jobs(self):
        while True:
            self.update()
            new_job_tmp_dir = None
            for tmp_dir, info in self.running_info.items():
                if info['running_jobs'] < info['max_jobs'] and self.can_start_new_job():
                    new_job_tmp_dir = tmp_dir
                    break
            if new_job_tmp_dir:
                if self.try_start_new_job(new_job_tmp_dir):
                    pass
                continue
            time.sleep(3.0)

    def can_start_new_job(self):
        return len(self.running_jobs) < self.max_jobs

    def run(self):
        self.load_jobs()
        self.load_drives()
        self.load_completed()
        # logger.debug('drives:', tmp=list(self.temp_drives), final=list(self.final_drives))
        job_thread = threading.Thread(target=self.manage_jobs)
        job_thread.daemon = True
        job_thread.start()
        statistic_thread = threading.Thread(target=self.update_statistics)
        statistic_thread.daemon = True
        statistic_thread.start()
        view = PlotView(self)
        view.show()

    def try_start_new_job(self, tmp_dir):
        logger.info('try_start_new_job, tmp_dir: {tmp_dir}', tmp_dir=tmp_dir)
        related_jobs = list(filter(lambda x: x.tmp_dir == tmp_dir, self.running_jobs))
        if len(related_jobs) >= self.plotting_config[tmp_dir].get('max_jobs', 1):
            return False
        job_start_mode = self.plotting_config[tmp_dir].get('job_start_mode', 'simple')
        if job_start_mode == 'simple':
            self.do_start_new_job(tmp_dir)
            return True
        elif job_start_mode == 'smart':
            phase1_jobs = list(filter(lambda x: x.phase < 2, related_jobs))
            if len(phase1_jobs) == 0:
                self.do_start_new_job(tmp_dir)
                return True

        return False

    def get_final_dir(self):
        final_dirs = settings.final_dir
        for final_dir in final_dirs:
            final_drive = os.path.splitdrive(final_dir)[0]
            try:
                _, _, free = shutil.disk_usage(final_drive)
                slots_free = free//get_k32_plotsize()
                if slots_free > self.get_final_drive_jobs(final_dir):
                    return final_dir
            except:
                continue

        return None

    def get_final_drive_jobs(self, final_drive):
        jobs = 0
        for job in self.running_jobs:
            drive = os.path.splitdrive(job.final_dir)[0]
            if drive == final_drive:
                jobs += 1
        return jobs

    def do_start_new_job(self, tmp_dir):
        param_keys = ["size", "pool_address", "num_threads", "bukets", "buffer","nobitfield", "farmer_key", "pool_key"]
        conf = self.plotting_config[tmp_dir]
        args = dict(tmp_dir=tmp_dir)
        if 'tmp2_dir' in conf:
            args['tmp2_dir'] = conf['tmp2_dir']
        for key in param_keys:
            if key in conf:
                args[key] = conf[key]
        final_dir = self.get_final_dir()
        if final_dir == None:
            logger.error('Can not found proper final dir when start new job.')
            return None
        args['final_dir'] = final_dir
        job = PlotJob.new(**args)
        job.start()
        self.running_jobs.append(job)
        return job

    def update(self):
        running_info = {}
        running_jobs = []
        for tmp_dir, conf in self.plotting_config.items():
            running_info.setdefault(tmp_dir, {'running_jobs':0, 'max_jobs': conf.get('max_jobs', 1)})
        for job in self.running_jobs:
            job.update()
            if job.completed:
                self.completed_jobs.append(job)
                self.completed_logs.append(job.logparser)
                self.update_completed_statistics()
                continue
            status = job.get_run_status()
            if status.lower() == 'stopped':
                continue
            running_jobs.append(job)
            tmp_dir  = job.tmp_dir
            if tmp_dir not in running_info:
                running_info.setdefault(tmp_dir, {'running_jobs':0, 'max_jobs': 1})
            running_info[tmp_dir]['running_jobs'] += 1
        self.running_jobs = running_jobs
        self.running_info = running_info
        logger.debug('running_info: {info}', info=running_info)


def main():
    try:
        settings.main.get('log_level')
    except:
        setting_template = importlib.resources.path("plotboss", "settings.toml")
        setting_file = 'settings.toml'
        if not os.path.exists(setting_file):
            with setting_template as template_file:
                shutil.copy(template_file, setting_file)
        settings.reload()

    boss = PlotBoss()
    logger.remove()
    logger.add(os.path.join(boss.work_dir, 'plotboss.log'), level=settings.main.get('log_level', 'WARNING'))
    boss.run()