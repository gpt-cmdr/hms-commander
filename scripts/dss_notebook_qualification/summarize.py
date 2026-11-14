import json, sys
r = json.load(open(sys.argv[1]))
for nb, v in r.items():
    issues = []
    for k, d in v["cell_diffs"].items():
        if d == "missing": issues.append(f"{k} missing"); continue
        for i, dd in d.items():
            if "HNB_PROBE" in json.dumps(dd): continue
            issues.append(f"cell {i} differs ({k})")
    nfiles = len(v["dss"]); nrec = 0; vd = 0; bytes_same = 0; kinds = {}
    for rel, e in v["dss"].items():
        shas = {x["sha"] for x in e.values() if isinstance(x, dict)}
        bytes_same += len(shas) == 1
        for b, x in e.items():
            if isinstance(x, str): issues.append(f"{rel} {b}: {x}"); continue
            if b == "java":
                nrec += x["n_catalog"]
                for kk, n in x["kinds"].items(): kinds[kk] = kinds.get(kk, 0) + n
            vd += x.get("n_value_diffs", 0)
            if any(k.startswith("catalog_equal") and not val for k, val in x.items()): issues.append(f"{rel} {b} catalog differs")
    sh = {k.split(":")[0] + ":" + k.split("_hnb_backend")[-1]: s["summary"] for k, s in v["shadow"].items() if s["backend"] == "shadow"}
    print(nb, "| runs:", {k: (x["status"], x["wall_s"]) for k, x in v["runs"].items()})
    print("   dss files:", nfiles, "records(java):", nrec, "kinds:", kinds, "value/metadata diffs:", vd, "byte-identical files:", bytes_same)
    print("   shadow:", sh)
    for s in issues: print("   ISSUE", s)
