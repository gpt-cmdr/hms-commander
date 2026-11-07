import sys, numpy as np, ras_commander_fast_dss as f
a, b = sys.argv[1], sys.argv[2]
ca = list(f.get_catalog(a)['pathname']); cb = list(f.get_catalog(b)['pathname'])
print("catalog equal (as sets):", sorted(ca) == sorted(cb), "order equal:", ca == cb, len(ca))
diffs = {}
for pn in ca:
    ga, gb = vars(f.read_grid(a, pn)), vars(f.read_grid(b, pn))
    for k in ga:
        if k in ("dss_file",): continue
        va, vb = ga[k], gb[k]
        if k == "metadata":
            for mk in va:
                if va[mk] != vb.get(mk): diffs.setdefault("metadata." + mk, set()).add((str(va[mk])[:60], str(vb.get(mk))[:60]))
            continue
        if isinstance(va, np.ndarray):
            same = va.shape == vb.shape and np.array_equal(va, vb, equal_nan=True)
        else:
            same = (va == vb) or (isinstance(va, float) and np.isnan(va) and np.isnan(vb))
        if not same: diffs.setdefault(k, set()).add((str(va)[:60], str(vb)[:60]))
for k, v in diffs.items(): print(k, len(v), sorted(v)[:3])
print("fields differing:", sorted(diffs) or "none")
