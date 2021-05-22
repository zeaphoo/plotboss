import pytest
from plotbot.plotlog import PlotLogParser
from datetime import datetime

def test_log_parser():
    p = PlotLogParser()
    with open('./tests/assets/plot.logfile') as f:
        lines = f.readlines()
        p.feed(lines)
        assert p.phase == 4
        assert p.total_time == 39945.08
        assert p.tmp_dir == '/farm/yards/901'
        assert p.tmp2_dir == '/farm/yards/901'
        assert p.start_time == datetime(2021, 4, 4, 19, 0, 50)
        assert p.target_path == "/farm/wagons/801/plot-k32-2021-04-04-19-00-3eb8a37981de1cc76187a36ed947ab4307943cf92967a7e166841186c7899e24.plot"