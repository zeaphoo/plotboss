import os
import re
import statistics
import sys
from . import utils

class PlotLogParser:
    def __init__(self):
        self.phase = 0
        self.phase_time = {}  # Map from phase index to time
        self.total_time = 0
        self.n_sorts = 0
        self.n_uniform = 0
        self.sort_ratio = 0
        self.temp_dir = ''
        self.target_path = ''
        self.completed = False

    def feed(self, lines):
        sl = 'x'         # Slice key

        for line in lines:
            m = re.search(r'Starting plot (\d*)/(\d*)', line)
            if m:
                # (re)-initialize data structures
                sl = 'x'         # Slice key


            # Temp dirs.  Sample log line:
            # Starting plotting progress into temporary dirs: /mnt/tmp/01 and /mnt/tmp/a
            m = re.search(r'^Starting plotting.*dirs: (.*) and (.*)', line)
            if m:
                self.temp_dir = m.group(1)

            # Phase timing.  Sample log line:
            # Time for phase 1 = 22796.7 seconds. CPU (98%) Tue Sep 29 17:57:19 2020
            for phase in ['1', '2', '3', '4']:
                m = re.search(r'^Starting phase '+ phase + '/4:', line)
                if m:
                    self.phase = phase
                m = re.search(r'^Time for phase ' + phase + ' = (\d+.\d+) seconds..*', line)
                if m:
                    self.phase_time[phase] = float(m.group(1))

            # Uniform sort.  Sample log line:
            # Bucket 267 uniform sort. Ram: 0.920GiB, u_sort min: 0.688GiB, qs min: 0.172GiB.
            #   or
            # ....?....
            #   or
            # Bucket 511 QS. Ram: 0.920GiB, u_sort min: 0.375GiB, qs min: 0.094GiB. force_qs: 1
            m = re.search(r'Bucket \d+ ([^\.]+)\..*', line)
            if m and not 'force_qs' in line:
                sorter = m.group(1)
                self.n_sorts += 1
                if sorter == 'uniform sort':
                    self.n_uniform += 1
                elif sorter == 'QS':
                    pass
                else:
                    print ('Warning: unrecognized sort ' + sorter)

            # Job completion.  Record total time in sliced data store.
            # Sample log line:
            # Total time = 49487.1 seconds. CPU (97.26%) Wed Sep 30 01:22:10 2020
            m = re.search(r'^Total time = (\d+.\d+) seconds.*', line)
            if m:
                self.total_time = float(m.group(1))
                self.sort_ratio = 100 * self.n_uniform // self.n_sorts
                self.completed = True
