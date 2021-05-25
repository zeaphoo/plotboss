import re
import math

class PlotLogParser:
    def __init__(self):
        self.plot_id = 'xxxxx'
        self.phase = 0
        self.phase_time = {}  # Map from phase index to time
        self.phase_start_time = {}
        self.phase_subphases = {0:0, 1:0, 2:0, 3:0, 4:0}
        self.start_time = 0
        self.total_time = 0
        self.n_sorts = 0
        self.n_uniform = 0
        self.sort_ratio = 0
        self.tmp_dir = ''
        self.tmp2_dir = ''
        self.target_path = ''
        self.buckets = 128
        self.completed = False

    @property
    def progress(self):
        phase_offset = {0:0, 1:0, 2:42, 3:61, 4:98}
        phase_total = {0:1, 1:7, 2:6, 3:6, 4:2}
        phase_percent = {0:0, 1:42, 2:19, 3:37, 4:2}
        current = phase_offset[self.phase] + min(self.phase_subphases[self.phase]/phase_total[self.phase], 1)*phase_percent[self.phase]
        if current < 0:
            if self.phase == 1:
                current = 1
        if current > 100:
            current = 100
        return current

    def feed(self, lines):
        for line in lines:
            if self.phase == 0:
                m = re.search(r'Starting plot (\d*)/(\d*)', line)
                if m:
                    pass

                # Temp dirs.  Sample log line:
                # Starting plotting progress into temporary dirs: /mnt/tmp/01 and /mnt/tmp/a
                m = re.search(r'^Starting plotting.*dirs: (.*) and (.*)', line)
                if m:
                    self.tmp_dir = m.group(1)
                    self.tmp2_dir = m.group(2)

                m = re.match('^ID: ([0-9a-f]*)', line)
                if m:
                    self.plot_id = m.group(1)
                    self.found_id = True


            # Phase timing.  Sample log line:
            # Time for phase 1 = 22796.7 seconds. CPU (98%) Tue Sep 29 17:57:19 2020
            for phase in range(self.phase + 1, 5):
                m = re.search(r'^Starting phase {}/4:.*\.\.\. (.*)'.format(phase), line)
                if m:
                    starting_time = pendulum.from_format(m.group(1), 'ddd MMM DD HH:mm:ss YYYY', locale='en', tz=None)
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
                    self.phase_subphases[1] = max(self.phase_subphases[1], int(m.group(1))-1)

                m = re.match(r'\s+Bucket (\d+) .*', line)
                if m:
                    subphase = self.phase_subphases[1] + 1/self.buckets
                    if math.floor(subphase) != math.floor(self.phase_subphases[1]):
                        self.phase_subphases[1] = math.floor(self.phase_subphases[1]) + 0.98
                    else:
                        self.phase_subphases[1] = subphase

            if self.phase == 2:
                # Phase 2: "Backpropagating on table 2"
                m = re.match(r'^Backpropagating on table (\d).*', line)
                if m:
                    self.phase_subphases[2] = max(self.phase_subphases[2], 7 - int(m.group(1)))

                m = re.match(r'sorting table (\d+).*', line)
                if m:
                    subphase = self.phase_subphases[2] + 0.49
                    if math.floor(subphase) != math.floor(self.phase_subphases[2]):
                        self.phase_subphases[2] = math.floor(self.phase_subphases[2]) + 0.98
                    else:
                        self.phase_subphases[1] = subphase

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
            m = re.search(r'^Total time = (\d+.\d+) seconds.*', line)
            if m:
                self.total_time = float(m.group(1))
                self.sort_ratio = 100 * self.n_uniform // self.n_sorts
                self.phase_subphases[4] = 1

            m = re.search(r'^Renamed final file from (.+)\s+to\s+(.+)', line)
            if m:
                self.target_path = m.group(2).strip(' "')
                self.phase_subphases[4] = 2
                self.completed = True
