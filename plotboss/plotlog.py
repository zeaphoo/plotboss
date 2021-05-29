import re
import math
import pendulum
import os

class PlotLogParser:
    def __init__(self):
        self.plot_id = 'xxxxx'
        self.pool_key = ''
        self.farmer_key = ''
        self.phase = 0
        self.phase_time = {}  # Map from phase index to time
        self.phase_start_time = {}
        self.phase_subphases = {0:0, 1:0, 2:0, 3:0, 4:0}
        self.buckets_count = 0
        self.start_time = 0
        self.total_time = 0
        self.complete_time = 0
        self.n_sorts = 0
        self.n_uniform = 0
        self.sort_ratio = 0
        self.tmp_dir = ''
        self.tmp2_dir = ''
        self.final_dir = ''
        self.target_path = ''
        self.buckets = 128
        self.completed = False
        self.size = 32
        self.num_threads = 2
        self.buffer = 4000


    @property
    def progress(self):
        phase_offset = {0:0, 1:0, 2:42, 3:61, 4:98}
        phase_total = {0:1, 1:6.1, 2:6, 3:6, 4:2}
        phase_percent = {0:0, 1:42, 2:19, 3:37, 4:2}
        subphase_progress = 0
        if self.phase == 1:
            subphase_progress = min(self.buckets_count/self.buckets, 0.98)
        current = phase_offset[self.phase] + min((self.phase_subphases[self.phase]+subphase_progress)/phase_total[self.phase], 1)*phase_percent[self.phase]
        if current <= 0:
            if self.phase == 1:
                current = 0.3
        if current > 100:
            current = 100
        return current

    def feed(self, lines):
        for line in lines:
            if self.phase == 0:
                m = re.search(r'Starting plot (\d*)/(\d*)', line)
                if m:
                    pass

                # 2021-05-25T20:37:31.267  chia.plotting.create_plots       : [32mINFO    [0m Creating 1 plots of size 32, pool public key:  a846ed9e450637596481301bf4232c5d283843b8799dcccea336f8e6dd1b3faace63978b4988c5cebbb8096bd9f0614b farmer public key: a1d639b7d0c7a1352973dd46547ec8a6128292a45c80f1fe88471492c0d441e84b8b48c01d6cca74a2dbd51e652acf20[0m
                m = re.search(r'.*, pool public key:\s+([0-9a-f]*)\s+farmer public key:\s+([0-9a-f]*)\x1b.*', line)
                if m:
                    self.pool_key = m.group(1).strip()
                    self.farmer_key = m.group(2).strip()

                # Temp dirs.  Sample log line:
                # Starting plotting progress into temporary dirs: /mnt/tmp/01 and /mnt/tmp/a
                m = re.search(r'^Starting plotting.*dirs: (.*) and (.*)', line)
                if m:
                    self.tmp_dir = m.group(1)
                    self.tmp2_dir = m.group(2)

                m = re.match(r'^ID: ([0-9a-f]*)', line)
                if m:
                    self.plot_id = m.group(1)
                    self.found_id = True

                # Plot size is: 32
                # Buffer size is: 4000MiB
                # Using 128 buckets
                # Using 4 threads of stripe size 65536

                m = re.match(r'^Plot size is:\s+(\d+)', line)
                if m:
                    self.size = int(m.group(1))

                m = re.match(r'^Buffer size is: (\d+)MiB', line)
                if m:
                    self.buffer = int(m.group(1))

                m = re.match(r'^Using\s+(\d+)\s+buckets', line)
                if m:
                    self.buckets = int(m.group(1))

                m = re.match(r'^Using (\d+) threads .*', line)
                if m:
                    self.num_threads = int(m.group(1))


            # Phase timing.  Sample log line:
            # Time for phase 1 = 22796.7 seconds. CPU (98%) Tue Sep 29 17:57:19 2020
            for phase in range(self.phase + 1, 5):
                m = re.search(r'^Starting phase {}/4:.*\.\.\. (.*)'.format(phase), line)
                if m:
                    starting_time = pendulum.from_format(m.group(1), 'ddd MMM DD HH:mm:ss YYYY', locale='en', tz='local')
                    if phase == 1:
                        self.start_time = starting_time
                    self.phase_start_time[phase] = starting_time
                    self.phase = phase
                m = re.search(r'^Time for phase {} = (\d+.\d+) seconds..*'.format(phase), line)
                if m:
                    self.phase_time[phase] = float(m.group(1))

            if self.phase == 1:
                # Phase 1: "Computing table 2"
                m = re.match(r'^Computing table (\d).*', line)
                if m:
                    subphase = int(m.group(1))-1
                    if subphase == 1:
                        subphase = 0.1
                    elif subphase > 1:
                        subphase = subphase - 1 + 0.1
                    self.phase_subphases[1] = max(self.phase_subphases[1], subphase)
                    self.buckets_count = 0

                m = re.match(r'^\s+Bucket (\d+) .*', line)
                if m:
                    self.buckets_count += 1

            if self.phase == 2:
                # Phase 2: "Backpropagating on table 2"
                m = re.match(r'^Backpropagating on table (\d).*', line)
                if m:
                    self.phase_subphases[2] = max(self.phase_subphases[2], 7 - int(m.group(1)))

            if self.phase == 3:
                # Phase 3: "Compressing tables 4 and 5"
                m = re.match(r'^Compressing tables (\d) and (\d).*', line)
                if m:
                    self.phase_subphases[3] = max(self.phase_subphases[3], int(m.group(1))-1)

            # Uniform sort.  Sample log line:
            # Bucket 267 uniform sort. Ram: 0.920GiB, u_sort min: 0.688GiB, qs min: 0.172GiB.
            #   or
            # ....?....
            #   or
            # Bucket 511 QS. Ram: 0.920GiB, u_sort min: 0.375GiB, qs min: 0.094GiB. force_qs: 1

            if self.phase == 4:
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
            m = re.search(r'^Total time = (\d+.\d+) seconds. CPU\s+\(.*\)\s+(.*)', line)
            if m:
                self.total_time = float(m.group(1))
                complete_time = pendulum.from_format(m.group(2), 'ddd MMM DD HH:mm:ss YYYY', locale='en', tz='local')
                self.complete_time = complete_time
                self.sort_ratio = 100 * self.n_uniform // self.n_sorts
                self.phase_subphases[4] = 1

            m = re.search(r'^Renamed final file from (.+)\s+to\s+(.+)', line)
            if m:
                self.target_path = m.group(2).strip(' "')
                self.final_dir = os.path.dirname(self.target_path)
                self.phase_subphases[4] = 2
                self.completed = True
