"""Compare H-NB notebook runs across the java, native and shadow backends.

Usage: python compare.py <runs_root> <out.json>

For each notebook folder present under every backend:
  * status / failing cell / wall time per backend (from _hnb_run*.json);
  * cell text outputs, normalized (absolute paths, timestamps, timings, memory
    addresses removed), compared to java cell by cell;
  * every *.dss file with the same relative path: the catalog, then every record,
    read once with the java backend (HEC Monolith, the oracle) in this process.
    Time series and paired data compare values (NaN-aware, exact) and units/type;
    grids compare cells (exact, NaN-aware) and metadata. HEC-HMS writes its own
    results, so equal-valued records are expected; any byte-level difference in
    DSS files written by HEC-HMS is not attributable to the backend.
  * shadow summary per backend (from _hnb_backend*.json).
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

os.environ["HMS_COMMANDER_DSS_BACKEND"] = "java"

import numpy as np  # noqa: E402
import nbformat  # noqa: E402

BACKENDS = ("java", "native", "shadow")
NORM = [
    (re.compile(r"[A-Za-z]:[\\/][^\s'\"]*"), "<PATH>"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(\.\d+)?"), "<DATETIME>"),
    (re.compile(r"\b\d+(\.\d+)?\s*(s|sec|seconds|ms|min)\b"), "<DUR>"),
    (re.compile(r"0x[0-9a-fA-F]+"), "<ADDR>"),
    (re.compile(r"\b\d+(\.\d+)?\s*(KB|MB|kB|bytes)\b"), "<SIZE>"),
    (re.compile(r"(Workflow (started|completed)|Started|Completed|Elapsed|elapsed|Runtime|runtime)[^\n]*"), "<TIMELINE>"),
]


def norm(text):
    for rx, rep in NORM:
        text = rx.sub(rep, text)
    return text


def cell_texts(nb_file):
    nb = nbformat.read(nb_file, as_version=4)
    out = []
    for i, c in enumerate(nb.cells):
        if c.cell_type != "code":
            continue
        parts = []
        for o in c.get("outputs", []):
            if o.get("output_type") == "stream" and o.get("name") == "stdout":
                parts.append(o.get("text", ""))
            elif o.get("output_type") in ("execute_result", "display_data"):
                d = o.get("data", {})
                if "text/plain" in d and "image/png" not in d:
                    parts.append(d["text/plain"])
                if "image/png" in d:
                    parts.append("<IMAGE>")
            elif o.get("output_type") == "error":
                parts.append(f"ERROR {o.get('ename')}: {o.get('evalue')}")
        out.append((i, norm("".join(parts))))
    return out


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def read_records(dss):
    from hms_commander import HmsDss
    from hms_commander.dss.core import DssCore

    recs = {}
    cat = list(HmsDss.get_catalog(str(dss)))
    for pn in cat:
        c = pn.split("/")[3].upper() if pn.count("/") >= 7 else ""
        try:
            if re.search(r"/\d\d\w\w\w\d{4}:\d{4}/\d\d\w\w\w\d{4}:\d{4}/", pn):
                g = DssCore.read_grid(str(dss), pn)
                recs[pn] = ("grid", np.asarray(g["data"], dtype=np.float64),
                            {k: str(g.get(k)) for k in ("units", "data_type", "grid_type", "cell_size", "lower_left_cell", "shape", "start_time", "end_time")})
                continue
        except Exception as e:  # not a grid after all
            recs[pn] = ("grid-error", None, repr(e)[:200])
            continue
        try:
            df = HmsDss.read_timeseries(str(dss), pn)
            recs[pn] = ("ts", df["value"].to_numpy(dtype=np.float64),
                        {"n": len(df), "first": str(df.index[0]) if len(df) else None,
                         "last": str(df.index[-1]) if len(df) else None,
                         "units": str(df.attrs.get("units")), "type": str(df.attrs.get("type"))})
            continue
        except Exception as e:
            ts_err = repr(e)[:160]
        try:
            pd_ = HmsDss.read_paired_data(str(dss), pn)
            if pd_ is None:
                recs[pn] = ("not-ts-or-pd", None, ts_err)
            else:
                recs[pn] = ("pd", np.concatenate([np.ravel(np.asarray(pd_["x_values"], dtype=np.float64)),
                                                  np.ravel(np.asarray(pd_["y_values"], dtype=np.float64))]),
                            {k: str(pd_.get(k)) for k in ("x_units", "y_units", "x_label", "y_label")})
        except Exception as e:
            recs[pn] = ("unreadable", None, ts_err + " | " + repr(e)[:160])
    return cat, recs


def eq(a, b):
    if a is None or b is None:
        return a is None and b is None
    if a.shape != b.shape:
        return False
    return bool(np.array_equal(a, b, equal_nan=True))


def main():
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    names = sorted({p.name for b in BACKENDS for p in (root / b).glob("*") if p.is_dir()})
    report = {}
    for name in names:
        r = {"runs": {}, "shadow": {}, "cell_diffs": {}, "dss": {}}
        for b in BACKENDS:
            d = root / b / name
            for f in d.glob("_hnb_run*.json"):
                j = json.loads(f.read_text())
                r["runs"][f"{b}:{j['notebook']}"] = {k: j[k] for k in ("status", "failing_cell", "wall_s")}
            for f in d.glob("_hnb_backend*.json"):
                j = json.loads(f.read_text())
                r["shadow"][f"{b}:{f.stem}"] = {"backend": j["backend"], "summary": j["summary"],
                                                 "n_records": j["n_records"],
                                                 "not_identical": j["records_not_identical"]}
        # cell outputs vs java
        jdir = root / "java" / name
        for nbf in jdir.glob("executed*.ipynb"):
            jt = dict(cell_texts(nbf))
            for b in ("native", "shadow"):
                other = root / b / name / nbf.name
                if not other.exists():
                    r["cell_diffs"][f"{b}:{nbf.name}"] = "missing"
                    continue
                ot = dict(cell_texts(other))
                diffs = {i: {"java": jt.get(i, "")[:1500], b: ot.get(i, "")[:1500]}
                         for i in sorted(set(jt) | set(ot)) if jt.get(i) != ot.get(i)}
                r["cell_diffs"][f"{b}:{nbf.name}"] = diffs
        # DSS files
        rels = sorted({str(p.relative_to(root / b / name)) for b in BACKENDS
                       for p in (root / b / name).rglob("*.dss")})
        for rel in rels:
            entry = {}
            base = None
            for b in BACKENDS:
                p = root / b / name / rel
                if not p.exists():
                    entry[b] = "missing"
                    continue
                try:
                    cat, recs = read_records(p)
                except Exception as e:
                    entry[b] = f"read error {e!r}"[:300]
                    continue
                info = {"sha": sha(p), "size": p.stat().st_size, "n_catalog": len(cat)}
                if base is None:
                    base = (b, cat, recs)
                else:
                    bb, bcat, brecs = base
                    info["catalog_equal_to_" + bb] = sorted(cat) == sorted(bcat)
                    only_here = sorted(set(cat) - set(bcat))
                    only_base = sorted(set(bcat) - set(cat))
                    vdiff = []
                    for pn in sorted(set(cat) & set(bcat)):
                        k1, v1, m1 = brecs[pn]
                        k2, v2, m2 = recs[pn]
                        if k1 != k2 or not eq(v1, v2) or m1 != m2:
                            vdiff.append({"pathname": pn, base[0]: [k1, str(m1)[:300]], b: [k2, str(m2)[:300]],
                                          "values_equal": eq(v1, v2)})
                    info.update(only_here=only_here[:20], only_base=only_base[:20],
                                n_value_diffs=len(vdiff), value_diffs=vdiff[:20])
                info["kinds"] = {k: sum(1 for v in recs.values() if v[0] == k) for k in {v[0] for v in recs.values()}}
                entry[b] = info
            r["dss"][rel] = entry
        report[name] = r
    out.write_text(json.dumps(report, indent=1, default=str))
    # terse console summary
    for name, r in report.items():
        print("==", name)
        for k, v in r["runs"].items():
            print("  run", k, v)
        for k, v in r["shadow"].items():
            print("  shadow", k, v["backend"], v["summary"])
        for k, v in r["cell_diffs"].items():
            print("  celldiff", k, "missing" if v == "missing" else sorted(v))
        for rel, e in r["dss"].items():
            print("  dss", rel, {b: (x if isinstance(x, str) else {kk: x[kk] for kk in x if kk in ("sha", "n_catalog", "n_value_diffs", "kinds") or kk.startswith("catalog_equal")}) for b, x in e.items()})


if __name__ == "__main__":
    main()
