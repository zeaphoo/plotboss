import os
import random
from shutil import copyfile
import time
from basepy.config import settings
from .job import PlotJob

class PlotBot():
    def __init__(self):
        self.work_dir = os.path.abspath(settings.main.get('work_dir', './plotbot_data'))
        self.max_jobs = settings.main.get('max_jobs', -1)
        self.final_paths = settings.plots.get('final_path', [])
        self.init_work_dir()
        self.jobs = []
        self.temp_dirs = {}
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
                self.jobs.append(job)

    def run(self):
        pass



def main():
    bot = PlotBot()
    bot.load_jobs()
    bot.run()