import time

from prodat.core.util.spinner import Spinner

def test_spinner():
    s = Spinner()
    spinner_start = s.start()
    time.sleep(3)
    spinner_stop = s.stop()
    assert spinner_start
    assert spinner_stop