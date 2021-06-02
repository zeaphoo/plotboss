import math
import os
import re
import platform
import string
import random

GB = 1_000_000_000

def df_b(d):
    'Return free space for directory (in bytes)'
    stat = os.statvfs(d)
    return stat.f_frsize * stat.f_bavail

def get_k32_plotsize():
    return 108 * GB

def get_plotsize(k=32):
    return 108 * GB

def human_format(num, precision=1):
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return (('%.' + str(precision) + 'f%s') %
            (num, ['', 'K', 'M', 'G', 'T', 'P'][magnitude]))

def time_format(sec):
    if sec is None:
        return '-'
    if sec < 60:
        return '%ds' % sec
    elif sec < 3600:
        return '%dm' % (int(sec/ 60))
    else:
        return '%dh%02dm' % (int(sec / 3600), int((sec % 3600) / 60))

def list_k32_plots(d):
    'List completed k32 plots in a directory (not recursive)'
    plots = []
    for plot in os.listdir(d):
        if re.match(r'^plot-k32-.*plot$', plot):
            plot = os.path.join(d, plot)
            if os.stat(plot).st_size > (0.95 * get_k32_plotsize()):
                plots.append(plot)

    return plots


def gen_job_id():
    return 'pj' + ''.join(random.choice(string.ascii_lowercase) for _ in range(10))

def is_windows():
    return platform.system() == 'Windows'

def is_macos():
    return platform.system() == 'Darwin'

def is_linux():
    return platform.system() == 'Linux'