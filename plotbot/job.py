import contextlib
import os
from plotbot.tail import FileTail
from plotbot.plotlog import PlotLogParser
import random
import re
import sys
from datetime import datetime
import subprocess
import shutil
from pathlib import Path
from basepy.config import settings

import psutil

from .utils import is_windows, gen_job_id, is_macos


class PlotCommand():
    plot_arg_keys = {
            'k': dict(name="size", atype="integer"),
            'r': dict(name="num_threads", atype="integer"),
            'b': dict(name="buffer", atype="integer"),
            'u': dict(name="bukets", atype="integer"),
            't': dict(name="temp_dir"),
            '2': dict(name="temp_dir2"),
            'd': dict(name="final_dir"),
            'n': dict(name="num", atype="integer"),
            'e': dict(name="nobitfield", atype="boolean")
    }
    plot_arg_names = {
        'size': 'k',
        'num_threads': 'r',
        'buffer': 'b',
        'bukets': 'u',
        'temp_dir': 't',
        'temp_dir2': '2',
        'final_dir': 'd',
        'num': 'n',
        'nobitfield': 'e'
    }

    @classmethod
    def parse(cls, cmdline):
        if len(cmdline) < 3:
            return None
        cmd0 = cmdline[0]
        if is_windows() and cmd0.endswith('\\chia.exe'):
            if cmdline[1] == 'plots' and cmdline[2] == 'create':
                return cls.init_from_cmdlines(cmdline[3:])
        return None

    def __init__(self, **kwargs):
        self.cmd_args = {}
        for key in kwargs:
            if key in self.plot_arg_names:
                self.cmd_args[key] = kwargs[key]
        for key, value in self.cmd_args.items():
            setattr(self, key, value)

    @classmethod
    def init_from_cmdlines(cls, cmdlines):
        args = cls._parse_args(cmdlines)
        return cls(**args)

    @classmethod
    def _parse_args(cls, cmdlines):
        args = {}

        for i in range(0, len(cmdlines)):
            c = cmdlines[i]
            if c[0]=='-' and c[1] in cls.plot_arg_keys:
                arg_info = cls.plot_arg_keys[c[1]]
                akey = arg_info['name']
                atype = arg_info.get('atype', 'string')
                avalue = None
                if atype == 'boolean':
                    avalue == True
                else:
                    if len(c) > 2:
                        avalue = c[2:]
                    else:
                        avalue = cmdlines[i+1] if i < len(cmdlines) else None
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

    def get_cmd(self):
        cmd = [self.chia_cmd(), 'plots', 'create']
        for key, value in self.cmd_args.items():
            cmd.append('-{}'.format(self.plot_arg_names[key]))
            if value in [True, False]: continue
            cmd.append(value)
        return cmd

    def chia_cmd(self):
        cmd = shutil.which('chia')
        if not cmd:
            if is_windows():
                cmd = self._find_chia_windows()
        return cmd or 'chia'


    def _find_chia_windows(self):
        home = Path.home()
        chia_root_path = os.path.join(str(home), 'AppData', 'Local', 'chia-blockchain')
        chia_path = None
        if not os.path.exists(chia_root_path): return None
        with os.scandir(chia_root_path) as it:
            for entry in it:
                if entry.name.startswith('app-') and entry.is_dir():
                    chia_path = os.path.join(chia_root_path, entry.name)
        if not chia_path: return None
        chia_path = os.path.join(chia_path, 'resources', 'app.asar.unpacked', 'daemon', 'chia.exe')
        return chia_path


class PlotJob:
    @classmethod
    def get_running_jobs(cls):
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

    @classmethod
    def new(cls, **kwargs):
        plotcmd = PlotCommand(**kwargs)
        return cls(plotcmd)

    def __init__(self, plotcmd, proc=None, status="waiting", logfile=None):
        self.job_id = gen_job_id()
        self.plotcmd = plotcmd
        self.proc =  proc
        self.logfile = logfile
        self.logparser = PlotLogParser()
        self.logtail = None
        if self.logfile:
            self._parse_logfile()


    def _parse_logfile(self):
        '''Read plot ID and job start time from logfile.  Return true if we
           find all the info as expected, false otherwise'''
        assert self.logfile
        if not self.logtail:
            self.logtail = FileTail(self.logfile)
        lines = self.logtail.tail()
        self.logparser.feed(lines)

    def update(self):
        lines = self.logtail.tail()
        if lines:
            self.logparser.feed(lines)

    @property
    def progress(self):
        '''Return a 2-tuple with the job phase and subphase (by reading the logfile)'''
        return self.logparser.progress

    @property
    def temp_dir(self):
        return self.logparser.temp_dir

    @property
    def temp_dir2(self):
        return self.logparser.temp_dir2

    @property
    def final_dir(self):
        return self.plotcmd.final_dir

    def plot_id_prefix(self):
        return self.logparser.plot_id[:8]

    def status_info(self):
        p = self.logparser
        status =  dict(
            plot_id = p.plot_id
        )
        return status

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
            return 'Running'
        elif status == psutil.STATUS_SLEEPING:
            return 'Sleeping'
        elif status == psutil.STATUS_DISK_SLEEP:
            return 'DiskSleep'
        elif status == psutil.STATUS_STOPPED:
            return 'Stopped'
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

    def start(self):
        plot_args = self.plotcmd.get_cmd()
        logfile = self._get_log_path()
        plot_args.append('>')
        plot_args.append(logfile)
        plot_args.append('2>&1')
        p = subprocess.Popen(plot_args,
                shell=True)
        self.proc = psutil.Process(p.pid)
        self.logfile = logfile
        self.logtail = FileTail(self.logfile)

    def get_temp_files(self):
        # Prevent duplicate file paths by using set.
        temp_files = set([])
        for f in self.proc.open_files():
            if self.temp_dir in f.path or self.temp_dir2 in f.path or self.final_dir in f.path:
                temp_files.add(f.path)
        return temp_files

    def _get_log_path(self):
        log_root = os.path.join(settings.main.get('work_dir', './plotbot_data'), 'logs')
        if not os.path.exists(log_root):
            os.makedirs(log_root)
        return os.path.join(log_root, '{}.log'.format(self.job_id))

    def cancel(self):
        #self.proc.resume()
        self.proc.terminate()
