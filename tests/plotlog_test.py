import pytest
from plotboss.plotlog import PlotLogParser
from datetime import datetime
import pendulum

def test_log_parser():
    p = PlotLogParser()
    p.buffer = 0
    p.size = 0
    p.buckets = 0
    p.num_threads = 0
    assert p.size == 0
    assert p.buffer == 0
    assert p.buckets == 0
    assert p.num_threads == 0
    with open('./tests/assets/plot.logfile') as f:
        lines = f.readlines()
        p.feed(lines)
        assert p.phase == 4
        assert p.total_time == 39945.08
        assert p.tmp_dir == '/farm/yards/901'
        assert p.tmp2_dir == '/farm/yards/901'
        assert p.pool_key == '0b6f2b9428744d5062a2073e14b3ca9896a71f7ca9850bdcb285f26108fb19f610c788d47e4830c4c7abfa7611e00168'
        assert p.farmer_key == '93222af1a0f7b2ff39f98eb87c1b609fea797798302a60d1f1d6e5152cfdce12c260325d78446e7b8758101b64f43bd5'
        assert p.size == 32
        assert p.buffer == 4000
        assert p.buckets == 128
        assert p.num_threads == 4
        assert p.start_time == pendulum.local(2021, 4, 4, 19, 0, 50)
        assert p.complete_time == pendulum.local(2021, 4, 5, 6, 6, 35)
        assert p.target_path == "/farm/wagons/801/plot-k32-2021-04-04-19-00-3eb8a37981de1cc76187a36ed947ab4307943cf92967a7e166841186c7899e24.plot"
        assert p.final_dir == '/farm/wagons/801'