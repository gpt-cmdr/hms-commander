"""Shadow sweep: read every record of every DSS file under <root> through HmsDss on the
shadow backend (native result returned, compared with Java), and print the summary
plus every non-identical record. Usage: python sweep.py <root> <out.json>"""
import json, os, re, sys, hashlib
from pathlib import Path
os.environ["HMS_COMMANDER_DSS_BACKEND"] = "shadow"
from hms_commander import HmsDss
from hms_commander.dss.core import DssCore
from hms_commander.dss import _backend as B
import ras_commander_fast_dss as f

root, out = Path(sys.argv[1]), Path(sys.argv[2])
seen, files = set(), []
for p in sorted(root.rglob("*.dss")):
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    if h not in seen:
        seen.add(h); files.append(p)
print("unique DSS files:", len(files))
errors = []
for p in files:
    HmsDss.get_catalog(str(p))
    cat = f.get_catalog(str(p))
    for pn, kind in zip(cat["pathname"], cat["record_type_name"]):
        try:
            if kind in ("RTS", "RTD", "ITS", "ITD", "RTS-PATTERN"):
                HmsDss.read_timeseries(str(p), pn)
                DssCore.get_peak_value(str(p), pn)
            elif kind in ("PD", "PDD"):
                HmsDss.read_paired_data(str(p), pn)
            elif "GRID" in kind.upper() or re.search(r"/\d\d\w{3}\d{4}:\d{4}/\d\d\w{3}\d{4}:\d{4}/", pn):
                DssCore.read_grid(str(p), pn)
            else:
                HmsDss.read_timeseries(str(p), pn)
        except Exception as e:
            errors.append({"file": str(p), "pathname": pn, "kind": kind, "error": repr(e)[:300]})
    HmsDss.get_file_version(str(p))
summ = HmsDss.get_shadow_summary()
odd = [r for r in B.SHADOW_RECORDS if r["outcome"] != "identical"]
kinds = {}
for p in files:
    for k in f.get_catalog(str(p))["record_type_name"]:
        kinds[k] = kinds.get(k, 0) + 1
json.dump({"files": [str(p) for p in files], "record_kinds": kinds, "summary": summ,
           "not_identical": odd, "errors": errors}, open(out, "w"), indent=1, default=str)
print("record kinds:", kinds)
print(json.dumps(summ, indent=1))
print("not identical:", len(odd), "errors raised to caller:", len(errors))
for r in odd[:30]: print(" ", r["operation"], r["outcome"], r["label"], r["pathname"], r["diffs"], r["java_error"], r["native_error"])
for e in errors[:30]: print("  ERR", e)
