import os
import random
from shutil import copyfile
import time
from basepy.config import settings
from .job import PlotJob

class PlotBot():
    def __init__(self):
        self.work_dir = os.path.abspath(settings.main.get('work_dir', './plotbot_data'))
        self.init_work_dir()

    def init_work_dir(self):
        if not os.path.exists(self.work_dir):
            os.makedirs(self.work_dir)

    def load_jobs(self):
        PlotJob.get_running_jobs()

    def run(self):
        pass


def main():
    bot = PlotBot()
    bot.load_jobs()
    bot.run()