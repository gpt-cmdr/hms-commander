"""Generate HEC-HMS 4.13 Frequency Storm reference fixtures for BalancedFrequencyStorm.

Builds a minimal one-subbasin HMS project (loss method "None" so that
PRECIP-EXCESS equals the met-model incremental precipitation), writes one
Frequency Storm meteorologic model + control spec + run per case, computes every
run headless with HEC-HMS (Jython via ``HmsJython``), reads the subbasin
PRECIP-EXCESS series from each output DSS and writes:

    <fixture_dir>/cases.json                    inputs + provenance
    <fixture_dir>/hms_reference_series.csv      case,block,hms_incremental_in
    <fixture_dir>/kerrville_pds_depths.csv      NOAA Atlas 14 PDS depth table

Requires HEC-HMS 4.13 (Windows), Java for pyjnius (DSS reads) and network access
only if the NOAA CSV is not already in the fixture directory.

Usage:
    python scripts/generate_frequency_storm_hms_fixtures.py
        [--hms-exe PATH] [--work-dir DIR]
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import shutil
import tempfile
import urllib.request
from pathlib import Path

import numpy as np

from hms_commander import HmsJython
from hms_commander.dss import DssCore

NOAA_URL = (
    "https://hdsc.nws.noaa.gov/cgi-bin/new/fe_text_mean.csv"
    "?lat=30.05&lon=-99.14&data=depth&units=english&series=pds"
)
DEFAULT_HMS_EXE = Path(r"C:\Program Files\HEC\HEC-HMS\4.13\HEC-HMS.cmd")
DEFAULT_FIXTURE_DIR = (
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "hms_frequency_storm"
)

DURATION_LABELS = [
    "5-min",
    "10-min",
    "15-min",
    "30-min",
    "60-min",
    "2-hr",
    "3-hr",
    "6-hr",
    "12-hr",
    "24-hr",
    "2-day",
    "3-day",
    "4-day",
    "7-day",
    "10-day",
]
DURATIONS_MIN = [
    5,
    10,
    15,
    30,
    60,
    120,
    180,
    360,
    720,
    1440,
    2880,
    4320,
    5760,
    10080,
    14400,
]
LEGACY_SLOTS_MIN = [5, 15, 60, 120, 180, 360, 720, 1440, 2880, 5760, 10080, 14400]

BASE_PARAMS = {
    "Storm Type": "Hydro-35/TP-40/TP-49",
    "Single Hypothetical Storm Size": "Yes",
    "Uniform Depth Duration Curve": "Yes",
    "User Specified Storm Area": "Yes",
    "Storm Size": 0,
    "Re-sort Storm Symmetrically": "No",
    "Total Duration": 1440,
    "Time Interval": 15,
    "Percent of Duration Before Peak Rainfall": 50,
    "Depth-Area Reduction Method": "TP-40/TP-49",
}

BASIN = """Basin: B1
     Version: 4.13
     Unit System: English
End:

Subbasin: Sub1
     Canvas X: 100.0
     Canvas Y: 100.0
     Area: 10.0
     Canopy: None
     Surface: None
     LossRate: None
     Transform: SCS
     Lag: 60.0
     Baseflow: None
End:
"""


def case(
    name,
    ari=100,
    dur=1440,
    iv=15,
    pk=50,
    area=0.0,
    convert_to=None,
    exc=None,
    convert_from=None,
    extra=None,
    blank=(),
    user_area=True,
    legacy=False,
    custom_depths=None,
):
    out = dict(
        name=name,
        ari=ari,
        duration_min=dur,
        interval_min=iv,
        peak_pct=pk,
        storm_area_sqmi=area,
        convert_to_annual=convert_to,
        exceedance_pct=exc,
        convert_from_annual=convert_from,
        extra=extra or {},
        blank_durations=list(blank),
        user_specified_area=user_area,
        legacy_format=legacy,
    )
    if custom_depths is not None:
        out["custom_depths"] = custom_depths
    return out


def build_cases():
    cs = []
    for pk in (25, 33, 50, 67, 75):
        cs.append(case(f"p24h15m_pk{pk}", pk=pk))
        cs.append(case(f"p6h5m_pk{pk}", dur=360, iv=5, pk=pk))
    cs += [
        case("p24h5m_pk50", iv=5),
        case("p24h5m_pk67", iv=5, pk=67),
        case("p24h30m_pk50", iv=30),
        case("p24h60m_pk33", iv=60, pk=33),
        case("p12h10m_pk50", dur=720, iv=10),
    ]
    for pk in (25, 33, 50, 67, 75):
        cs += [
            case(f"n3_pk{pk}", dur=180, iv=60, pk=pk),
            case(f"n4_pk{pk}", dur=120, iv=30, pk=pk),
            case(f"n6_pk{pk}", dur=360, iv=60, pk=pk),
            case(f"n7_pk{pk}", dur=10080, iv=1440, pk=pk),
            case(f"n10_pk{pk}", dur=14400, iv=1440, pk=pk),
        ]
    cs += [
        case("long3d60m_pk50", dur=4320, iv=60),
        case("long10d60m_pk67", dur=14400, iv=60, pk=67),
    ]
    cs += [
        case("area50_24h15m_pk50", area=50),
        case("area50_24h15m_pk67", area=50, pk=67),
        case("area12p5_6h5m_pk50", dur=360, iv=5, area=12.5),
        case("area250_24h15m_pk50", area=250),
        case("area1000_24h15m_pk50", area=1000),
        case("area100_3d60m_pk50", area=100, dur=4320, iv=60),
        case("area25_10d60m_pk67", area=25, dur=14400, iv=60, pk=67),
        case("area30_24h5m_pk50", area=30, iv=5),
    ]
    cs += [
        case("pda50_24h15m", ari=2, convert_to="Yes", exc=50, convert_from="No"),
        case("pda20_24h15m", ari=5, convert_to="Yes", exc=20, convert_from="No"),
        case(
            "pda10_area25", ari=10, area=25, convert_to="Yes", exc=10, convert_from="No"
        ),
        case("ann_ann50_24h15m", ari=2, convert_to="Yes", exc=50, convert_from="Yes"),
        case("pds_pds50_24h15m", ari=2, convert_to="No", exc=50, convert_from="No"),
        case("ann_pds50_24h15m", ari=2, convert_to="No", exc=50, convert_from="Yes"),
        case("pda1_24h15m", ari=100, convert_to="Yes", exc=1, convert_from="No"),
    ]
    cs += [
        case("blank10_30", blank=(10, 30)),
        case("blank10_30_area20", blank=(10, 30), area=20),
        case("blank30_only_6h5m", dur=360, iv=5, blank=(30,)),
        case("resort_yes", extra={"Re-sort Storm Symmetrically": "Yes"}, pk=67),
        case(
            "resort_perturbed_off",
            dur=360,
            iv=15,
            pk=50,
            custom_depths={
                5: 1.17,
                10: 1.88,
                15: 2.32,
                30: 3.2,
                60: 3.3,
                120: 7.0,
                180: 7.1,
                360: 8.63,
                720: 10.3,
                1440: 12.1,
                2880: 14.3,
                4320: 15.5,
                5760: 16.0,
                10080: 17.0,
                14400: 17.8,
            },
        ),
        case(
            "resort_perturbed_on",
            dur=360,
            iv=15,
            pk=50,
            extra={"Re-sort Storm Symmetrically": "Yes"},
            custom_depths={
                5: 1.17,
                10: 1.88,
                15: 2.32,
                30: 3.2,
                60: 3.3,
                120: 7.0,
                180: 7.1,
                360: 8.63,
                720: 10.3,
                1440: 12.1,
                2880: 14.3,
                4320: 15.5,
                5760: 16.0,
                10080: 17.0,
                14400: 17.8,
            },
        ),
        case("area_from_subbasin_10", user_area=False, area=999),
        case("storm_type_atlas14_area40", extra={"Storm Type": "Atlas 14"}, area=40),
        case(
            "area_method_none_area50",
            extra={"Depth-Area Reduction Method": "None"},
            area=50,
        ),
    ]
    cs += [
        case("leg_24h15m_pk50", legacy=True),
        case("leg_24h15m_pk67_area20", pk=67, area=20, legacy=True),
        case("leg_6h5m_pk50", dur=360, iv=5, legacy=True),
        case("leg_6h5m_pk33_area8", dur=360, iv=5, pk=33, area=8, legacy=True),
    ]
    return cs


def load_noaa_table(path: Path):
    if not path.exists():
        path.write_text(
            urllib.request.urlopen(NOAA_URL).read().decode(), encoding="utf8"
        )
    ari, rows = None, {}
    for line in path.read_text(encoding="utf8").splitlines():
        if line.startswith("by duration"):
            ari = [int(x) for x in line.split(":,")[1].split(",")]
        m = re.match(r"(\d+-(?:min|hr|day)):,(.*)", line)
        if m:
            rows[m.group(1)] = [float(x) for x in m.group(2).split(",")]
    return ari, rows


def depths_for(table, ari_years):
    ari, rows = table
    i = ari.index(ari_years)
    return {m: rows[lab][i] for m, lab in zip(DURATIONS_MIN, DURATION_LABELS)}


def case_depths(table, c):
    """Return the NOAA table depths, or a deliberate fixture perturbation."""
    return c.get("custom_depths") or depths_for(table, c["ari"])


def met_text(c, depths):
    n = c["name"]
    head = (
        f"Meteorology: {n}\n     Version: {'3.3' if c['legacy_format'] else '4.13'}\n"
        "     Unit System: English\n"
        "     Precipitation Method: Frequency Based Hypothetical\n"
        "     Snowmelt Method: None\n     Use Basin Model: B1\nEnd:\n\n"
        "Precip Method Parameters: Frequency Based Hypothetical\n"
    )
    if c["legacy_format"]:
        params = {
            "Exceedence Frequency": 1,
            "Single Hypothetical Storm Size": "Yes",
            "Convert From Annual Series": "No",
            "Convert to Annual Series": "No",
            "Storm Size": c["storm_area_sqmi"],
            "Total Duration": c["duration_min"],
            "Time Interval": c["interval_min"],
            "Percent of Duration Before Peak Rainfall": c["peak_pct"],
        }
        body = "".join(f"     {k}: {v}\n" for k, v in params.items())
        body += "".join(f"     Depth: {depths[m]}\n" for m in LEGACY_SLOTS_MIN)
        return head + body + "End:\n\nSubbasin: Sub1\nEnd:\n"
    p = dict(BASE_PARAMS)
    p.update(
        {
            "Storm Size": c["storm_area_sqmi"],
            "Total Duration": c["duration_min"],
            "Time Interval": c["interval_min"],
            "Percent of Duration Before Peak Rainfall": c["peak_pct"],
        }
    )
    if not c["user_specified_area"]:
        p["User Specified Storm Area"] = "No"
    if c["convert_to_annual"]:
        p["Convert to Annual Series"] = c["convert_to_annual"]
    if c["convert_from_annual"]:
        p["Convert From Annual Series"] = c["convert_from_annual"]
    if c["exceedance_pct"] is not None:
        p["Exceedence Frequency"] = c["exceedance_pct"]
    p.update(c["extra"])
    body = "".join(f"     {k}: {v}\n" for k, v in p.items())
    for m in DURATIONS_MIN:
        v = None if m in c["blank_durations"] else depths[m]
        body += f"     Depth {m}: {'' if v is None else v}\n"
    return head + body + "End:\n\nSubbasin: Sub1\nEnd:\n"


def control_text(c):
    iv, tot = c["interval_min"], c["duration_min"]
    n = int(np.ceil((tot + max(1440, 2 * iv)) / iv))
    end = dt.datetime(2000, 1, 1) + dt.timedelta(minutes=n * iv)
    return (
        f"Control: C_{c['name']}\n     Version: 4.13\n"
        "     Start Date: 1 January 2000\n"
        f"     Start Time: 00:00\n"
        f"     End Date: {end.day} {end.strftime('%B')} {end.year}\n"
        f"     End Time: {end.strftime('%H:%M')}\n     Time Interval: {iv}\nEnd:\n"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hms-exe", type=Path, default=DEFAULT_HMS_EXE)
    ap.add_argument("--work-dir", type=Path, default=None)
    ap.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    args = ap.parse_args()

    fx = args.fixture_dir
    fx.mkdir(parents=True, exist_ok=True)
    table = load_noaa_table(fx / "kerrville_pds_depths.csv")
    work = args.work_dir or Path(tempfile.mkdtemp(prefix="hms_freq_storm_"))
    work.mkdir(parents=True, exist_ok=True)
    cases = build_cases()

    hms = (
        "Project: P1\n     Version: 4.13\n     DSS File Name: P1.dss\nEnd:\n\n"
        "Basin: B1\n     FileName: B1.basin\nEnd:\n\n"
    )
    runs = ""
    (work / "B1.basin").write_text(BASIN)
    for c in cases:
        n = c["name"]
        (work / f"{n}.met").write_text(met_text(c, case_depths(table, c)))
        (work / f"C_{n}.control").write_text(control_text(c))
        hms += (
            f"Precipitation: {n}\n     FileName: {n}.met\nEnd:\n\n"
            f"Control: C_{n}\n     FileName: C_{n}.control\nEnd:\n\n"
        )
        runs += (
            f"Run: {n}\n     Log File: {n}.log\n     DSS File: {n}.dss\n"
            "     Basin: B1\n"
            f"     Precip: {n}\n     Control: C_{n}\nEnd:\n\n"
        )
    (work / "P1.hms").write_text(hms)
    (work / "P1.run").write_text(runs)

    # One HMS session per case. HMS rewrites the project/run files when a session
    # closes, so restore them before every compute and retry transient failures.
    for c in cases:
        script = (
            "from hms.model import JythonHms\n"
            f'JythonHms.OpenProject("P1", r"{work}")\n'
            f'JythonHms.Compute("{c["name"]}")\n'
        )
        for attempt in range(3):
            (work / "P1.hms").write_text(hms)
            (work / "P1.run").write_text(runs)
            ok, _, _ = HmsJython.execute_script(
                script_content=script,
                hms_exe_path=args.hms_exe,
                working_dir=work,
                timeout=1800,
            )
            if ok:
                break
        print(f"{c['name']}: {'ok' if ok else 'FAILED'}", flush=True)
        if not ok:
            raise SystemExit(f"HMS run failed for {c['name']}")

    rows = []
    for c in cases:
        dss = str(work / f"{c['name']}.dss")
        path = [
            p
            for p in DssCore.get_catalog(dss)
            if "/PRECIP-EXCESS/" in p and "CUM" not in p
        ][0]
        series = DssCore.read_timeseries(dss, path)["value"]
        series = series[~series.index.duplicated()].values
        n_blocks = c["duration_min"] // c["interval_min"]
        for k, v in enumerate(series[:n_blocks], start=1):
            rows.append((c["name"], k, f"{float(v):.12g}"))
        c["n_blocks"] = n_blocks
        c["depths_in"] = {str(m): d for m, d in case_depths(table, c).items()}

    with open(fx / "hms_reference_series.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["case", "block", "hms_incremental_in"])
        w.writerows(rows)
    meta = {
        "provenance": {
            "generator": "scripts/generate_frequency_storm_hms_fixtures.py",
            "hms_version": "HEC-HMS 4.13 (build 134654, Java 17.0.11)",
            "generated_utc": dt.datetime.now(dt.timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%SZ"
            ),
            "series": (
                "Sub1 PRECIP-EXCESS (loss method None) from the run output DSS; "
                "first duration/interval blocks"
            ),
            "noaa_source": NOAA_URL,
            "noaa_location": (
                "Kerrville TX 30.05N -99.14W, NOAA Atlas 14 Vol 11 v2, "
                "partial duration series, inches"
            ),
            "basin": (
                "1 subbasin, area 10 sq mi, Loss None, SCS transform, " "Baseflow None"
            ),
            "met_format": (
                "native HMS 4.13 Frequency Based Hypothetical (Depth <min> rows); "
                "legacy_format cases use the 3.x 'Depth:' layout"
            ),
            "control": "time interval = storm time interval, start 1 Jan 2000 00:00",
            "resort_perturbed_cases": (
                "resort_perturbed_off/on use the same positive, nondecreasing "
                "DDF table with non-monotone increments to distinguish the HMS "
                "Re-sort Storm Symmetrically setting"
            ),
        },
        "cases": cases,
    }
    (fx / "cases.json").write_text(json.dumps(meta, indent=1))
    print(f"wrote {len(rows)} reference rows for {len(cases)} cases to {fx}")
    if args.work_dir is None:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
