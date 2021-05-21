import os
import random
from shutil import copyfile
import time
from basepy.config import settings
from .job import PlotJob
import time

class PlotBot():
    def __init__(self):
        self.work_dir = os.path.abspath(settings.main.get('work_dir', './plotbot_data'))
        self.max_jobs = settings.main.get('max_jobs', -1)
        self.final_paths = settings.plots.get('final_path', [])
        self.init_work_dir()
        self.running_jobs = []
        self.waiting_jobs = []
        self.completed_jobs = []
        self.running_info = {}
        self.plotting_config = {}
        self.load_plotting_config()

    def init_work_dir(self):
        if not os.path.exists(self.work_dir):
            os.makedirs(self.work_dir)

    def load_plotting_config(self):
        plotting_config_list = settings.plots.get('plotting', [])
        for conf in plotting_config_list:
            self.plotting_config[conf['temp_dir']] = conf


    def load_jobs(self):
        jobs = PlotJob.get_running_jobs()
        for job in jobs:
            if job.logfile != None:
                self.running_jobs.append(job)

    def run(self):
        while True:
            self.update()
            for temp_dir, info in self.running_info.items():
                if info['running_jobs'] < info['max_jobs']:
                    if self.try_start_new_job(temp_dir):
                        continue
            self.report()
            time.sleep(3.0)

    def report(self):
        pass

    def try_start_new_job(self, temp_dir):
        related_jobs = list(filter(lambda x: x.temp_dir == temp_dir, self.running_jobs))
        if len(related_jobs) >= self.plotting_config[temp_dir].get('max_jobs', 1):
            return False
        job_start_mode = self.plotting_config[temp_dir].get('job_start_mode', 'simple')
        if job_start_mode == 'simple':
            self.do_start_new_job(temp_dir)
            return True
        elif job_start_mode == 'smart':
            phase1_jobs = list(filter(lambda x: x.phase < 2, related_jobs))
            if len(phase1_jobs) == 0:
                self.do_start_new_job(temp_dir)
                return True

        return False

    def do_start_new_job(self, temp_dir):
        conf = self.plotting_config[temp_dir]
        args = dict(temp_dir=temp_dir)
        if 'temp_dir2' in conf:
            args['temp_dir2'] = conf['temp_dir2']
        for key, value in conf.get('params', {}).items():
            args[key] = value
        job = PlotJob.new(**args)
        job.start()

    def update(self):
        running_info = {}
        running_jobs = []
        for job in self.running_jobs:
            if job.completed:
                self.completed_jobs.append(job)
                continue
            running_jobs.append(job)
            temp_dir  = job.temp_dir
            max_jobs = self.plotting_config[temp_dir].get('max_jobs', 1)
            info = running_info.setdefault(temp_dir, {'running_jobs':0, 'max_jobs': max_jobs})
            info['running_jobs'] += 1
        self.running_jobs = running_jobs
        self.running_info = running_info


def main():
    bot = PlotBot()
    bot.load_jobs()
    bot.run()