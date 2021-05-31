#!/usr/bin/env python3
import os
from asciimatics.event import KeyboardEvent
from asciimatics.widgets import Frame, Layout, MultiColumnListBox, Widget, Label, TextBox
from asciimatics.scene import Scene
from asciimatics.screen import Screen
from asciimatics.exceptions import ResizeScreenError, StopApplication
from asciimatics.parsers import AsciimaticsParser
import sys
from collections import defaultdict
import time
from datetime import datetime
from .utils import time_format, human_format
import copy
import psutil

def readable_mem(mem):
    for suffix in ["", "K", "M", "G", "T"]:
        if mem < 10000:
            return "{}{}".format(int(mem), suffix)
        mem /= 1024
    return "{}P".format(int(mem))


def readable_pc(percent):
    if percent < 100:
        return str(round(percent * 10, 0) / 10)
    else:
        return str(int(percent))


class PlotJobFrame(Frame):
    def __init__(self, screen, plotboss, name="My Form"):
        super(PlotJobFrame, self).__init__(screen,
                                        screen.height,
                                        screen.width,
                                        has_border=False,
                                        name=name)
        # Internal state required for doing periodic updates
        self._last_frame = 0
        self._reverse = True
        self.plotboss = plotboss

        # Create the basic form layout...
        layout = Layout([1], fill_frame=False)
        self._header = TextBox(4, as_string=True)
        self._header.disabled = True
        self._header.custom_colour = "label"
        self._list = MultiColumnListBox(
            11, #Widget.FILL_FRAME,
            ["<6", ">12", ">12", "<28", ">8", ">8", ">10", "<32", "100%"],
            [],
            titles=["INDEX", "JOB_ID", "PLOT_ID", "TMP_DIR", "PID", "PHASE", "ELAPSED", "PROGRESS", "FINAL_DIR"],
            name="mc_list",
            parser=AsciimaticsParser())
        self._drive_list = MultiColumnListBox(
            Widget.FILL_FRAME,
            [">12", ">12", ">10", ">10", "<32", "<10"],
            [],
            titles=["DRIVE", "TEMP/FINAL", "TOTAL", "FREE", "USAGE", "JOBS"],
            name="drive_list",
            parser=AsciimaticsParser())
        self._completed_info = TextBox(4, as_string=True)
        self._completed_info.disabled = True
        self._sys_info = TextBox(4, as_string=True)
        self._sys_info.disabled = True
        self.add_layout(layout)
        layout2 = Layout([1], fill_frame=True)
        self.add_layout(layout2)
        layout.add_widget(self._header)
        layout.add_widget(self._list)
        layout2.add_widget(self._drive_list)
        layout2.add_widget(self._completed_info)
        layout2.add_widget(self._sys_info)
        layout2.add_widget(
            Label("Press `r` to toggle order, or `q` to quit."))
        self.fix()

        # Add my own colour palette
        self.palette = defaultdict(
            lambda: (Screen.COLOUR_WHITE, Screen.A_NORMAL, Screen.COLOUR_BLACK))
        for key in ["selected_focus_field", "label"]:
            self.palette[key] = (Screen.COLOUR_WHITE, Screen.A_BOLD, Screen.COLOUR_BLACK)
        self.palette["title"] = (Screen.COLOUR_BLACK, Screen.A_NORMAL, Screen.COLOUR_WHITE)

    def process_event(self, event):
        # Do the key handling for this Frame.
        if isinstance(event, KeyboardEvent):
            if event.key_code in [ord('q'), ord('Q'), Screen.ctrl("c")]:
                raise StopApplication("User quit")
            elif event.key_code in [ord("r"), ord("R")]:
                self._reverse = not self._reverse

            # Force a refresh for improved responsiveness
            self._last_frame = 0

        # Now pass on to lower levels for normal handling of the event.
        return super(PlotJobFrame, self).process_event(event)

    def _update(self, frame_no):
        # Refresh the list view if needed
        if frame_no - self._last_frame >= self.frame_update_count or self._last_frame == 0:
            self._last_frame = frame_no
            running_jobs = self.plotboss.running_jobs

            self._update_running_list()
            self._update_drive_list()

        # Now redraw as normal
        super(PlotJobFrame, self)._update(frame_no)

    def _update_running_list(self):
        # Create the data to go in the multi-column list...
        last_selection = self._list.value
        last_start = self._list.start_line
        list_data = []
        running_jobs = self.plotboss.running_jobs
        for idx, job in enumerate(running_jobs):
            data = [
                idx,
                job.job_id,
                job.plot_id_prefix(),
                job.tmp_dir,
                job.pid,
                job.phase,
                time_format(job.elapsed_time),
                job.progress,
                job.final_dir
            ]
            list_data.append(copy.deepcopy(data))

        # Apply current sort and reformat for humans
        list_data = sorted(list_data,
                            reverse=self._reverse)
        new_data = [
            ([
                str(x[0]),
                str(x[1]),
                str(x[2]),
                str(x[3]),
                str(x[4]),
                str(x[5]),
                str(x[6]),
                self.progress_text(x[7]),
                str(x[8])
            ], idx) for idx, x in enumerate(list_data)
        ]

        self._list.options = new_data
        self._list.value = last_selection
        self._list.start_line = last_start
        self._header.value = '\n'.join([
                "Chia plotboss - plot like a boss",
                "Current [ {} ] plot jobs running. {}".format(len(running_jobs), datetime.now()),
                "Work directory: [ {} ]".format(os.getcwd()),
                ])

    def _update_drive_list(self):
        list_data = []
        last_selection = self._drive_list.value
        last_start = self._drive_list.start_line
        for drive, statistics in self.plotboss.drive_statistics.items():
            data = [
                drive,
                statistics['type'],
                statistics['total'],
                statistics['free'],
                statistics['usage'],
                len(statistics['jobs']),
            ]
            list_data.append(copy.deepcopy(data))

        new_data = [
            ([
                str(x[0]),
                str(x[1]).upper(),
                human_format(x[2]),
                human_format(x[3]),
                self.progress_text(x[4]),
                str(x[5])
            ], idx) for idx, x in enumerate(list_data)
        ]

        self._drive_list.options = new_data
        self._drive_list.value = last_selection
        self._drive_list.start_line = last_start

        completed_statistics = self.plotboss.completed_statistics

        self._completed_info.value = '\n'.join([
            'Plots Completed Today:{}, Yesterday:{}, Last_7_Days:{}'.format(completed_statistics['today'],
                completed_statistics['yesterday'], completed_statistics['last_7']),
            'Plots Average Duration: {}'.format(completed_statistics['average_duration']),
            'Plots Days: {}'.format(completed_statistics['days'])
        ])


        ram_usage = psutil.virtual_memory()

        self._sys_info.value = '\n'.join([
            'CPU Usage: {:.1f}%'.format(psutil.cpu_percent()),
            'RAM Usage: {}/{}, {:.1f}%'.format(human_format(ram_usage.used),
                    human_format(ram_usage.total), ram_usage.percent)
        ])

    def progress_text(self, percent, length = 20, fill = '█'):
        filledLength = int(length * percent/100)
        percent_str = '{:.1f}'.format(percent)
        bar = fill * filledLength + '-' * (length - filledLength)
        return f'|{bar}| {percent_str}%'

    @property
    def frame_update_count(self):
        # Refresh once every 2 seconds by default.
        return 40


class PlotView():
    def __init__(self, plotboss):
        self.plotboss = plotboss

    def show_plotview(self, screen):
        screen.play([Scene([PlotJobFrame(screen, self.plotboss)], -1)], stop_on_resize=True)


    def show(self):
        while True:
            try:
                Screen.wrapper(self.show_plotview, catch_interrupt=True)
                sys.exit(0)
            except ResizeScreenError:
                pass