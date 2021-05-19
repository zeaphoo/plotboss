# TODO do we use all these?
import argparse
import contextlib
import logging
import os
import random
import re
import sys
import threading
import time
from datetime import datetime
from enum import Enum, auto
from subprocess import call

import pendulum
import psutil

from .utils import is_windows


class PlotCommand():

    @classmethod
    def parse(cls, cmdline):
        if len(cmdline) < 3:
            return None
        cmd0 = cmdline[0]
        if is_windows() and cmd0.endswith('\\chia.exe'):
            if cmdline[1] == 'plots' and cmdline[2] == 'create':
                return cls(cmdline[3:])
        return None

    def __init__(self, cmd_args):
        self.cmd_args = self._parse_args(cmd_args)
        for key, value in self.cmd_args.items():
            setattr(self, key, value)

    def _parse_args(self, cmd_args):
        args = {}
        plot_arg_keys = {
            'k': dict(name="size", atype="integer"),
            'r': dict(name="num_threads", atype="integer"),
            'b': dict(name="buffer", atype="integer"),
            'u': dict(name="bukets", atype="integer"),
            't': dict(name="tmp_dir"),
            '2': dict(name="tmp2_dir"),
            'd': dict(name="final_dir"),
            'n': dict(name="num", atype="integer"),
            'e': dict(name="nobitfield", atype="boolean")

        }
        for i in range(0, len(cmd_args)):
            c = cmd_args[i]
            if c[0]=='-' and c[1] in plot_arg_keys:
                arg_info = plot_arg_keys[c[1]]
                akey = arg_info['name']
                atype = arg_info.get('atype', 'string')
                avalue = None
                if atype == 'boolean':
                    avalue == True
                else:
                    if len(c) > 2:
                        avalue = c[2:]
                    else:
                        avalue = cmd_args[i+1] if i < len(cmd_args) else None
                        i += 1
                    if atype == 'integer':
                        try:
                            avalue = int(avalue)
                        except:
                            raise ValueError('Error happened when value {} convert to int.'.format(avalue))

                args[akey] = avalue
            else:
                continue
        return args

def job_phases_for_tmpdir(d, all_jobs):
    '''Return phase 2-tuples for jobs running on tmpdir d'''
    return sorted([j.progress() for j in all_jobs if j.tmpdir == d])

def job_phases_for_dstdir(d, all_jobs):
    '''Return phase 2-tuples for jobs outputting to dstdir d'''
    return sorted([j.progress() for j in all_jobs if j.dstdir == d])

def parse_chia_plot_time(s):
    # This will grow to try ISO8601 as well for when Chia logs that way
    return pendulum.from_format(s, 'ddd MMM DD HH:mm:ss YYYY', locale='en', tz=None)

# TODO: be more principled and explicit about what we cache vs. what we look up
# dynamically from the logfile
class PlotJob:
    'Represents a plotter job'

    # These are constants, not updated during a run.
    k = 0
    r = 0
    u = 0
    b = 0
    n = 0  # probably not used
    tmpdir = ''
    tmp2dir = ''
    dstdir = ''
    logfile = ''
    jobfile = ''
    job_id = 0
    plot_id = '--------'
    proc = None   # will get a psutil.Process
    help = False

    # These are dynamic, cached, and need to be udpated periodically
    phase = (None, None)   # Phase/subphase

    @classmethod
    def get_running_jobs(cls):
        '''Return a list of running plot jobs.  If a cache of preexisting jobs is provided,
           reuse those previous jobs without updating their information.  Always look for
           new jobs not already in the cache.'''
        jobs = []

        for proc in psutil.process_iter(['pid', 'cmdline']):
            # Ignore processes which most likely have terminated between the time of
            # iteration and data access.
            with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                plotcmd = PlotCommand.parse(proc.cmdline())
                if not plotcmd: continue
                jobs.append(cls.init_from_process(plotcmd, proc))

        return jobs

    @classmethod
    def init_from_process(cls, plotcmd, proc):
        logfile = None
        with proc.oneshot():
            for f in proc.open_files():
                if f.path.endswith('.log'):
                    logfile = f.path
                    break
        return cls(plotcmd, proc, status="running", logfile=logfile)

    def __init__(self, plotcmd, proc, status="waiting", logfile=None):
        self.plotcmd = plotcmd
        self.proc =  proc
        self.logfile = logfile
        if self.logfile:
            self._parse_logfile()



    def _parse_logfile(self):
        '''Read plot ID and job start time from logfile.  Return true if we
           find all the info as expected, false otherwise'''
        assert self.logfile


    def progress(self):
        '''Return a 2-tuple with the job phase and subphase (by reading the logfile)'''
        return self.phase

    def plot_id_prefix(self):
        return self.plot_id[:8]

    # TODO: make this more useful and complete, and/or make it configurable
    def status_str_long(self):
        return '{plot_id}\nk={k} r={r} b={b} u={u}\npid:{pid}\ntmp:{tmp}\ntmp2:{tmp2}\ndst:{dst}\nlogfile:{logfile}'.format(
            plot_id = self.plot_id,
            k = self.k,
            r = self.r,
            b = self.b,
            u = self.u,
            pid = self.proc.pid,
            tmp = self.tmpdir,
            tmp2 = self.tmp2dir,
            dst = self.dstdir,
            plotid = self.plot_id,
            logfile = self.logfile
            )

    def get_mem_usage(self):
        return self.proc.memory_info().vms  # Total, inc swapped

    def get_tmp_usage(self):
        total_bytes = 0
        with os.scandir(self.tmpdir) as it:
            for entry in it:
                if self.plot_id in entry.name:
                    try:
                        total_bytes += entry.stat().st_size
                    except FileNotFoundError:
                        # The file might disappear; this being an estimate we don't care
                        pass
        return total_bytes

    def get_run_status(self):
        '''Running, suspended, etc.'''
        status = self.proc.status()
        if status == psutil.STATUS_RUNNING:
            return 'RUN'
        elif status == psutil.STATUS_SLEEPING:
            return 'SLP'
        elif status == psutil.STATUS_DISK_SLEEP:
            return 'DSK'
        elif status == psutil.STATUS_STOPPED:
            return 'STP'
        else:
            return self.proc.status()

    def get_time_wall(self):
        create_time = datetime.fromtimestamp(self.proc.create_time())
        return int((datetime.now() - create_time).total_seconds())

    def get_time_user(self):
        return int(self.proc.cpu_times().user)

    def get_time_sys(self):
        return int(self.proc.cpu_times().system)

    def get_time_iowait(self):
        cpu_times = self.proc.cpu_times()
        iowait = getattr(cpu_times, 'iowait', None)
        if iowait is None:
            return None

        return int(iowait)

    def suspend(self, reason=''):
        self.proc.suspend()
        self.status_note = reason

    def resume(self):
        self.proc.resume()

    def get_temp_files(self):
        # Prevent duplicate file paths by using set.
        temp_files = set([])
        for f in self.proc.open_files():
            if self.tmpdir in f.path or self.tmp2dir in f.path or self.dstdir in f.path:
                temp_files.add(f.path)
        return temp_files

    def cancel(self):
        'Cancel an already running job'
        # We typically suspend the job as the first action in killing it, so it
        # doesn't create more tmp files during death.  However, terminate() won't
        # complete if the job is supsended, so we also need to resume it.
        # TODO: check that this is best practice for killing a job.
        self.proc.resume()
        self.proc.terminate()
