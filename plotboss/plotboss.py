import os
import shutil
from plotboss.plotview import PlotView
import time
from basepy.config import settings
from .job import PlotJob
from .plotview import PlotView
import time
import threading
from basepy.log import logger
import sys

logger.add("stdout", level=settings.main.get('log_level', 'WARNING'))

class PlotBoss():
    def __init__(self):
        self.work_dir = os.path.abspath(settings.main.get('work_dir', './plotboss_data'))
        self.max_jobs = settings.main.get('max_jobs', -1)
        self.final_paths = settings.plots.get('final_dir', [])
        self.init_work_dir()
        self.running_jobs = []
        self.waiting_jobs = []
        self.completed_jobs = []
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

    def load_plotting_config(self):
        plotting_config_list = settings.plots.get('plotting', [])
        for conf in plotting_config_list:
            self.plotting_config[conf['tmp_dir']] = conf


    def load_jobs(self):
        jobs = PlotJob.get_running_jobs()
        for job in jobs:
            logger.debug('jobs, ', logfile=job.logfile)
            if job.logfile != None:
                self.running_jobs.append(job)

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
        drive_statistics = {}
        for drive in self.temp_drives:
            total, used, free = shutil.disk_usage(drive)
            usage = used*100/total
            drive_statistics[drive] = {'drive':drive, 'total':total, 'used':used,
                'free':free, 'type':'tmp', 'usage':usage}
        for drive in self.final_drives:
            if drive in drive_statistics:
                drive_statistics[drive]['type'] = 'tmp,final'
                continue
            total, used, free = shutil.disk_usage(drive)
            usage = used*100/total
            drive_statistics[drive] = {'drive':drive, 'total':total, 'used':used,
                'free':free, 'type':'final', 'usage':usage}
        self.drive_statistics = drive_statistics

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
        logger.info('try_start_new_job, ', tmp_dir=tmp_dir)
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
        final_dirs = settings.plots.final_dir
        return final_dirs[0]

    def do_start_new_job(self, tmp_dir):
        conf = self.plotting_config[tmp_dir]
        args = dict(tmp_dir=tmp_dir)
        if 'tmp2_dir' in conf:
            args['tmp2_dir'] = conf['tmp2_dir']
        for key, value in conf.get('param', {}).items():
            args[key] = value
        args['final_dir'] = self.get_final_dir()
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
        logger.debug('running_info', info=running_info)


def main():
    boss = PlotBoss()
    boss.run()