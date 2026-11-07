"""Run one hms-commander example notebook on one DSS backend (H-NB qualification).

Usage: python run_nb.py <notebook.ipynb> <backend> <run_root> [cell_timeout_s]

Copies the notebook into <run_root>/<backend>/<stem>/ and executes it there with
nbclient (cwd = that folder), with HMS_COMMANDER_DSS_BACKEND=<backend> (and
RAS_COMMANDER_DSS_BACKEND, for the one RasDss call in 14a). A final cell is appended
that writes the backend, engine version and shadow summary/records to
_hnb_backend.json. The executed notebook is saved as executed.ipynb next to
_hnb_run.json (status, failing cell, wall time).
"""
import json
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

PROBE = r'''
import json as _j, importlib.metadata as _md
from hms_commander import HmsDss as _H
from hms_commander.dss import _backend as _b
_out = {"backend": _H.get_backend(), "summary": _H.get_shadow_summary()}
try:
    _out["engine_version"] = _md.version("ras-commander-fast-dss")
except Exception as _e:
    _out["engine_version"] = repr(_e)
_out["records_not_identical"] = [r for r in list(_b.SHADOW_RECORDS) if r.get("outcome") != "identical"]
_out["n_records"] = len(_b.SHADOW_RECORDS)
open(_HNB_OUT, "w").write(_j.dumps(_out, indent=1, default=str))
print("HNB_PROBE", _j.dumps(_out["summary"]))
'''


def main():
    nb_path, backend, run_root = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    timeout = int(sys.argv[4]) if len(sys.argv) > 4 else 3600
    # Optional 5th arg: run inside another notebook's folder (14b uses 14a's outputs).
    shared = sys.argv[5] if len(sys.argv) > 5 else None
    work = run_root / backend / (shared or nb_path.stem)
    if shared is None and work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)
    tag = f"_{nb_path.stem}" if shared else ""
    nb = nbformat.read(nb_path, as_version=4)
    nb.cells.append(nbformat.v4.new_code_cell(f'_HNB_OUT = "_hnb_backend{tag}.json"\n' + PROBE))
    os.environ["HMS_COMMANDER_DSS_BACKEND"] = backend
    os.environ["RAS_COMMANDER_DSS_BACKEND"] = backend
    os.environ["MPLBACKEND"] = "Agg"
    client = NotebookClient(nb, timeout=timeout, kernel_name="python3",
                            resources={"metadata": {"path": str(work)}})
    t0 = time.time()
    status, err, failing_cell = "pass", None, None
    try:
        client.execute()
    except CellExecutionError as e:
        status, err = "fail", str(e)[-4000:]
    except Exception as e:  # timeouts, dead kernel
        status, err = "error", "".join(traceback.format_exception(e))[-4000:]
    wall = time.time() - t0
    for i, c in enumerate(nb.cells):
        if c.cell_type == "code" and any(o.get("output_type") == "error" for o in c.get("outputs", [])):
            failing_cell = i
            break
    nbformat.write(nb, work / f"executed{tag}.ipynb")
    rec = {"notebook": nb_path.name, "backend": backend, "status": status,
           "failing_cell": failing_cell, "error": err, "wall_s": round(wall, 1)}
    (work / f"_hnb_run{tag}.json").write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: rec[k] for k in ("notebook", "backend", "status", "failing_cell", "wall_s")}))


if __name__ == "__main__":
    main()
