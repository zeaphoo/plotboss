#!/usr/bin/env python3

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
    def __init__(self, screen, plotbot, name="My Form"):
        super(PlotJobFrame, self).__init__(screen,
                                        screen.height,
                                        screen.width,
                                        has_border=False,
                                        name=name)
        # Internal state required for doing periodic updates
        self._last_frame = 0
        self._reverse = True
        self.plotbot = plotbot

        # Create the basic form layout...
        layout = Layout([1], fill_frame=True)
        self._header = TextBox(1, as_string=True)
        self._header.disabled = True
        self._header.custom_colour = "label"
        self._list = MultiColumnListBox(
            Widget.FILL_FRAME,
            [">12", "<40", ">7", ">7", ">10", ">16", "100%"],
            [],
            titles=["JOB_ID", "TMP_DIR", "PID", "PHASE", "ELAPSED", "PROGRESS", "FINAL_DIR"],
            name="mc_list",
            parser=AsciimaticsParser())
        self.add_layout(layout)
        layout.add_widget(self._header)
        layout.add_widget(self._list)
        layout.add_widget(
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
                print('handle key_code', event.key_code)
                self._reverse = not self._reverse

            # Force a refresh for improved responsiveness
            self._last_frame = 0

        # Now pass on to lower levels for normal handling of the event.
        return super(PlotJobFrame, self).process_event(event)

    def _update(self, frame_no):
        # Refresh the list view if needed
        if frame_no - self._last_frame >= self.frame_update_count or self._last_frame == 0:
            self._last_frame = frame_no

            # Create the data to go in the multi-column list...
            last_selection = self._list.value
            last_start = self._list.start_line
            list_data = []
            running_jobs = self.plotbot.running_jobs
            for job in running_jobs:
                data = [
                    job.job_id,
                    job.tmp_dir,
                    job.pid,
                    job.phase,
                    job.elapsed_time,
                    job.progress,
                    job.final_dir
                ]
                list_data.append(data)

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
                    str(x[6])
                ], idx) for idx, x in enumerate(list_data)
            ]

            self._list.options = new_data
            self._list.value = last_selection
            self._list.start_line = last_start
            self._header.value = (
                "Current {} plot jobs running. {}".format(len(running_jobs), datetime.now()))

        # Now redraw as normal
        super(PlotJobFrame, self)._update(frame_no)

    @property
    def frame_update_count(self):
        # Refresh once every 2 seconds by default.
        return 40


class PlotView():
    def __init__(self, plotbot):
        self.plotbot = plotbot

    def show_plotview(self, screen):
        screen.play([Scene([PlotJobFrame(screen, self.plotbot)], -1)], stop_on_resize=True)


    def show(self):
        while True:
            try:
                Screen.wrapper(self.show_plotview, catch_interrupt=True)
                sys.exit(0)
            except ResizeScreenError:
                pass