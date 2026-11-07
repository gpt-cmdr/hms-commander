"""Reproducer: a Java (HEC Monolith) time-series read of a DSS6 file can return one block
instead of the whole series while another process catalogs the same file through Java.

Usage: python contention_repro.py <copy-of-a-DSS6-file> <pathname> [seconds]

Starts a child process that calls HmsDss.get_catalog() and get_file_version() in a loop
(java backend), then reads <pathname> repeatedly with HmsDss.read_timeseries() on the
java and on the native backend, in turn, and prints how many reads returned each
(length, first time) result. Use a pathname whose series spans several DSS blocks.
JAVA_HOME must be set. Work on a copy: the file is opened by two processes.
"""
import json, os, subprocess, sys, time

HOLDER = r'''
import os, sys, time
os.environ["HMS_COMMANDER_DSS_BACKEND"] = "java"
from hms_commander import HmsDss
p, t = sys.argv[1], time.time()
while time.time() - t < float(sys.argv[2]):
    try:
        HmsDss.get_catalog(p); HmsDss.get_file_version(p)
    except Exception:
        pass
'''

READER = r'''
import os, sys, time, json
os.environ["HMS_COMMANDER_DSS_BACKEND"] = sys.argv[3]
from hms_commander import HmsDss
p, pn, t, res = sys.argv[1], sys.argv[4], time.time(), {}
while time.time() - t < float(sys.argv[2]):
    try:
        df = HmsDss.read_timeseries(p, pn)
        key = f"{len(df)} values from {df.index[0]}" if len(df) else "empty"
    except Exception as e:
        key = "error " + type(e).__name__
    res[key] = res.get(key, 0) + 1
print(json.dumps(res))
'''


def main():
    dss, pathname = sys.argv[1], sys.argv[2]
    seconds = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    for backend in ("java", "native"):
        holder = subprocess.Popen([sys.executable, "-c", HOLDER, dss, str(seconds + 10)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)
        out = subprocess.run([sys.executable, "-c", READER, dss, str(seconds), backend, pathname],
                             capture_output=True, text=True)
        holder.wait()
        line = [l for l in out.stdout.splitlines() if l.startswith("{")]
        console = sum("Unable to access HEC-DSS file" in l for l in out.stdout.splitlines())
        print(backend, line[-1] if line else out.stderr[-500:], f"| HEC console messages: {console}")


if __name__ == "__main__":
    main()
