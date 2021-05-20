import psutil
import contextlib

for proc in psutil.process_iter(['pid', 'cmdline']):
    # Ignore processes which most likely have terminated between the time of
    # iteration and data access.
    with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
        cmdline = proc.cmdline()
        if 'ping' in cmdline:
            print(cmdline)
            print(proc.pid)
            print(proc.ppid())
            print(proc.open_files())