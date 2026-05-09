"""Generate CLB-536 HEC-HMS PRECIP-INC ground-truth CSV fixtures.

This script builds a temporary HEC-HMS 4.13 project from the bundled Castro
sample, computes the CLB-536 storm validation runs with the HMS engine, extracts the
Subbasin-1 PRECIP-INC DSS records, and writes durable CSV fixtures. It can also
extract from an existing GUI-computed project with ``--existing-project-dir``
and ``--skip-compute``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from hms_commander import FrequencyStorm, HmsJython, ScsTypeStorm
from hms_commander.dss import DssCore


HMS_INSTALL = Path("C:/Program Files/HEC/HEC-HMS/4.13")
SAMPLES_ZIP = HMS_INSTALL / "samples.zip"
DEFAULT_ARTIFACT_ROOT = Path("H:/Symphony/hms-commander/CLB-536/hms-ground-truth-work")
DEFAULT_FIXTURE_DIR = Path("tests/fixtures/clb536_storm_ground_truth")
DEFAULT_METHOD = "HEC-HMS 4.13 compute run from Castro sample project; PRECIP-INC extracted from output DSS"
LINEAR_ISSUE = "CLB-536"
DATE_TEXT = "9 May 2026"
TIME_TEXT = "09:00:00"
SUBBASINS = ("Subbasin-1", "Subbasin-2", "Subbasin-3", "Subbasin-4")
HEC_EPOCH = pd.Timestamp("1899-12-31 00:00:00")


@dataclass(frozen=True)
class Case:
    test_id: str
    storm_type: str
    total_depth_inches: float
    duration_hours: int
    interval_minutes: int
    met_name: str
    control_name: str
    run_name: str
    scs_type: str | None = None
    frequency_depths: tuple[float, ...] | None = None

    @property
    def fixture_name(self) -> str:
        return f"{self.test_id.lower()}_{self.run_name.lower()}.csv"


CASES = (
    Case(
        test_id="T01",
        storm_type="SCS Type I",
        total_depth_inches=10.0,
        duration_hours=24,
        interval_minutes=60,
        met_name="T01_SCS_TYPE_I_10IN_24HR_60MIN",
        control_name="CLB536_60MIN_24HR",
        run_name="T01_SCS_TYPE_I_10IN_24HR_60MIN",
        scs_type="I",
    ),
    Case(
        test_id="T02",
        storm_type="SCS Type I",
        total_depth_inches=10.0,
        duration_hours=24,
        interval_minutes=5,
        met_name="T02_SCS_TYPE_I_10IN_24HR_5MIN",
        control_name="CLB536_5MIN_24HR",
        run_name="T02_SCS_TYPE_I_10IN_24HR_5MIN",
        scs_type="I",
    ),
    Case(
        test_id="T03",
        storm_type="SCS Type IA",
        total_depth_inches=10.0,
        duration_hours=24,
        interval_minutes=60,
        met_name="T03_SCS_TYPE_IA_10IN_24HR_60MIN",
        control_name="CLB536_60MIN_24HR",
        run_name="T03_SCS_TYPE_IA_10IN_24HR_60MIN",
        scs_type="IA",
    ),
    Case(
        test_id="T04",
        storm_type="SCS Type IA",
        total_depth_inches=10.0,
        duration_hours=24,
        interval_minutes=5,
        met_name="T04_SCS_TYPE_IA_10IN_24HR_5MIN",
        control_name="CLB536_5MIN_24HR",
        run_name="T04_SCS_TYPE_IA_10IN_24HR_5MIN",
        scs_type="IA",
    ),
    Case(
        test_id="T05",
        storm_type="SCS Type II",
        total_depth_inches=10.0,
        duration_hours=24,
        interval_minutes=60,
        met_name="T05_SCS_TYPE_II_10IN_24HR_60MIN",
        control_name="CLB536_60MIN_24HR",
        run_name="T05_SCS_TYPE_II_10IN_24HR_60MIN",
        scs_type="II",
    ),
    Case(
        test_id="T06",
        storm_type="SCS Type II",
        total_depth_inches=10.0,
        duration_hours=24,
        interval_minutes=5,
        met_name="T06_SCS_TYPE_II_10IN_24HR_5MIN",
        control_name="CLB536_5MIN_24HR",
        run_name="T06_SCS_TYPE_II_10IN_24HR_5MIN",
        scs_type="II",
    ),
    Case(
        test_id="T07",
        storm_type="SCS Type III",
        total_depth_inches=10.0,
        duration_hours=24,
        interval_minutes=60,
        met_name="T07_SCS_TYPE_III_10IN_24HR_60MIN",
        control_name="CLB536_60MIN_24HR",
        run_name="T07_SCS_TYPE_III_10IN_24HR_60MIN",
        scs_type="III",
    ),
    Case(
        test_id="T08",
        storm_type="SCS Type III",
        total_depth_inches=10.0,
        duration_hours=24,
        interval_minutes=5,
        met_name="T08_SCS_TYPE_III_10IN_24HR_5MIN",
        control_name="CLB536_5MIN_24HR",
        run_name="T08_SCS_TYPE_III_10IN_24HR_5MIN",
        scs_type="III",
    ),
    Case(
        test_id="T09",
        storm_type="Frequency Storm (TP-40)",
        total_depth_inches=13.20,
        duration_hours=24,
        interval_minutes=5,
        met_name="T09_FREQUENCY_TP40_13_20IN_24HR_5MIN",
        control_name="CLB536_5MIN_24HR",
        run_name="T09_FREQUENCY_TP40_13_20IN_24HR_5MIN",
        frequency_depths=(1.2, 1.731, 2.1, 3.178, 4.3, 5.7, 6.7, 8.9, 10.8, 13.2),
    ),
)


def _write_text(path: Path, text: str) -> None:
    path.write_text(text.replace("\n", "\r\n"), encoding="utf-8")


def _extract_castro_project(work_dir: Path) -> Path:
    if not SAMPLES_ZIP.exists():
        raise FileNotFoundError(f"HEC-HMS samples archive not found: {SAMPLES_ZIP}")

    project_dir = work_dir / "castro"
    project_dir.mkdir(parents=True, exist_ok=True)
    prefix = "samples/samples/castro/"

    with zipfile.ZipFile(SAMPLES_ZIP) as archive:
        for member in archive.infolist():
            if not member.filename.startswith(prefix) or member.is_dir():
                continue

            relative = Path(member.filename[len(prefix) :])
            if not relative.parts:
                continue

            target = project_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as dest:
                shutil.copyfileobj(source, dest)

    return project_dir


def _control_text(control_name: str, interval_minutes: int) -> str:
    return f"""Control: {control_name}
     Last Modified Date: {DATE_TEXT}
     Last Modified Time: {TIME_TEXT}
     Version: 4.13
     Start Date: 1 January 2000
     Start Time: 00:00
     End Date: 2 January 2000
     End Time: 00:00
     Time Interval: {interval_minutes}
End:
"""


def _subbasin_blocks(extra_lines: Iterable[str] = ()) -> str:
    extra = "".join(f"     {line}\n" for line in extra_lines)
    blocks = []
    for subbasin in SUBBASINS:
        blocks.append(
            f"""Subbasin: {subbasin}
     Last Modified Date: {DATE_TEXT}
     Last Modified Time: {TIME_TEXT}
{extra}End:
"""
        )
    return "\n".join(blocks)


def _scs_met_text(case: Case) -> str:
    return f"""Meteorology: {case.met_name}
     Description: {LINEAR_ISSUE} ground truth {case.test_id} {case.storm_type}
     Last Modified Date: {DATE_TEXT}
     Last Modified Time: {TIME_TEXT}
     Version: 4.13
     Unit System: English
     Set Missing Data to Default: Yes
     Precipitation Method: Hypothetical Storm
     Air Temperature Method: None
     Atmospheric Pressure Method: None
     Dew Point Method: None
     Wind Speed Method: None
     Shortwave Radiation Method: None
     Longwave Radiation Method: None
     Snowmelt Method: None
     Evapotranspiration Method: No Evapotranspiration
     Use Basin Model: Castro 1
End:

Precip Method Parameters: Hypothetical Storm
     Last Modified Date: {DATE_TEXT}
     Last Modified Time: {TIME_TEXT}
     Precipitation Method: Point Depth
     Storm Depth: {case.total_depth_inches:.3f}
     Storm Type: SCS Type {case.scs_type}
     Depth-Area Reduction Method: No Reduction
     Uniform Depth: Yes
End:

{_subbasin_blocks()}
"""


def _frequency_met_text(case: Case) -> str:
    if case.frequency_depths is None:
        raise ValueError("Frequency case is missing depth-duration values")

    depth_names = (5, 10, 15, 30, 60, 120, 180, 360, 720, 1440)
    depth_lines = "\n".join(
        f"     Depth {duration}: {depth:.6f}"
        for duration, depth in zip(depth_names, case.frequency_depths)
    )
    blank_depths = [f"Depth {duration}: " for duration in (*depth_names, 2880, 4320, 5760, 10080, 14400)]

    return f"""Meteorology: {case.met_name}
     Description: {LINEAR_ISSUE} ground truth {case.test_id} TP-40 Frequency Storm
     Last Modified Date: {DATE_TEXT}
     Last Modified Time: {TIME_TEXT}
     Version: 4.13
     Unit System: English
     Set Missing Data to Default: Yes
     Precipitation Method: Frequency Based Hypothetical
     Air Temperature Method: None
     Atmospheric Pressure Method: None
     Dew Point Method: None
     Wind Speed Method: None
     Shortwave Radiation Method: None
     Longwave Radiation Method: None
     Snowmelt Method: None
     Evapotranspiration Method: No Evapotranspiration
     Use Basin Model: Castro 1
End:

Precip Method Parameters: Frequency Based Hypothetical
     Last Modified Date: {DATE_TEXT}
     Last Modified Time: {TIME_TEXT}
     Storm Type: Hydro-35/TP-40/TP-49
     Single Hypothetical Storm Size: Yes
     Uniform Depth Duration Curve: Yes
     User Specified Storm Area: Yes
     Storm Size: 0.01
     Re-sort Storm Symmetrically: No
     Total Duration: 1440
     Time Interval: 5
     Percent of Duration Before Peak Rainfall: 67
     Depth-Area Reduction Method: TP-40/TP-49
{depth_lines}
     Depth 2880:
     Depth 4320:
     Depth 5760:
     Depth 10080:
     Depth 14400:
End:

{_subbasin_blocks(blank_depths)}
"""


def _configure_project(project_dir: Path) -> None:
    hms_file = project_dir / "castro.hms"
    run_file = project_dir / "castro.run"
    hms_text = hms_file.read_text(encoding="utf-8")
    run_text = run_file.read_text(encoding="utf-8")

    controls = {
        "CLB536_60MIN_24HR": 60,
        "CLB536_5MIN_24HR": 5,
    }
    for control_name, interval in controls.items():
        _write_text(project_dir / f"{control_name}.control", _control_text(control_name, interval))
        hms_text += (
            f"\nControl: {control_name}\n"
            f"     FileName: {control_name}.control\n"
            f"     Description: {LINEAR_ISSUE} ground truth {interval} minute control\n"
            "End:\n"
        )

    for case in CASES:
        met_text = _frequency_met_text(case) if case.frequency_depths else _scs_met_text(case)
        _write_text(project_dir / f"{case.met_name}.met", met_text)
        hms_text += (
            f"\nPrecipitation: {case.met_name}\n"
            f"     Filename: {case.met_name}.met\n"
            f"     Description: {LINEAR_ISSUE} ground truth {case.test_id}\n"
            f"     Last Modified Date: {DATE_TEXT}\n"
            f"     Last Modified Time: {TIME_TEXT}\n"
            "End:\n"
        )
        run_text += f"""
Run: {case.run_name}
     Default Description: Yes
     Log File: {case.run_name}.log
     DSS File: {case.run_name}.dss
     Is Save Spatial Results: No
     Last Modified Date: {DATE_TEXT}
     Last Modified Time: {TIME_TEXT}
     Basin: Castro 1
     Precip: {case.met_name}
     Control: {case.control_name}
     Save State Type: None
     Time-Series Output: Save All
     Time Series Results Manager Start:
     Time Series Results Manager End:
End:
"""

    _write_text(hms_file, hms_text)
    _write_text(run_file, run_text)


def _compute_runs(project_dir: Path, timeout: int) -> dict[str, str]:
    logs: dict[str, str] = {}
    for case in CASES:
        script = HmsJython.generate_compute_script(project_dir, case.run_name)
        success, stdout, stderr = HmsJython.execute_script(
            script,
            HMS_INSTALL,
            working_dir=project_dir,
            timeout=timeout,
            max_memory="4G",
        )
        combined = "\n".join(part for part in (stdout, stderr) if part)
        logs[case.test_id] = combined
        if not success or "ERROR" in combined.upper():
            raise RuntimeError(f"HMS compute failed for {case.test_id}\n{combined}")
    return logs


def _generated_values(case: Case) -> np.ndarray:
    if case.scs_type:
        frame = ScsTypeStorm.generate_hyetograph(
            total_depth_inches=case.total_depth_inches,
            scs_type=case.scs_type,
            time_interval_min=case.interval_minutes,
        )
    else:
        frame = FrequencyStorm.generate_hyetograph(
            total_depth_inches=case.total_depth_inches,
            total_duration_min=case.duration_hours * 60,
            time_interval_min=case.interval_minutes,
            peak_position_pct=67.0,
        )
    return frame["incremental_depth"].to_numpy(dtype=float)[1:]


def _select_precip_path(catalog: Iterable[str], run_name: str) -> str:
    paths = [
        path
        for path in catalog
        if "/PRECIP-INC/" in path.upper() and f"MET:{run_name}".upper() in path.upper()
    ]
    if not paths:
        paths = [path for path in catalog if "/PRECIP-INC/" in path.upper()]
    for path in paths:
        parts = path.strip("/").split("/")
        if parts and parts[0].upper() == "SUBBASIN-1":
            return path
    if paths:
        return sorted(paths)[0]
    raise RuntimeError(f"No PRECIP-INC path found in {dss_file}")


def _read_precip_with_hms_jython(dss_file: Path, run_name: str) -> tuple[str, pd.DataFrame]:
    """Read PRECIP-INC using the HMS-bundled Java stack when pyjnius is unavailable."""

    script = f'''
from hec.heclib.dss import HecDss

dss = HecDss.open(r"{str(dss_file).replace(chr(92), "/")}")
catalog = dss.getCatalogedPathnames()
paths = []
for i in range(catalog.size()):
    path = str(catalog.get(i))
    if "/PRECIP-INC/" in path.upper() and "MET:{run_name}".upper() in path.upper():
        paths.append(path)
if not paths:
    for i in range(catalog.size()):
        path = str(catalog.get(i))
        if "/PRECIP-INC/" in path.upper():
            paths.append(path)

selected = None
for path in paths:
    parts = path.strip("/").split("/")
    if len(parts) > 0 and parts[0].upper() == "SUBBASIN-1":
        selected = path
        break
if selected is None and len(paths) > 0:
    paths.sort()
    selected = paths[0]
if selected is None:
    dss.done()
    raise RuntimeError("No PRECIP-INC path found in {dss_file}")

print("SELECTED|" + selected)
container = dss.get(selected, True)
for i in range(len(container.values)):
    print("DATA|%d|%.17g" % (container.times[i], container.values[i]))
dss.done()
'''
    success, stdout, stderr = HmsJython.execute_script(
        script,
        HMS_INSTALL,
        working_dir=dss_file.parent,
        timeout=120,
        max_memory="2G",
    )
    if not success:
        raise RuntimeError(f"HMS Jython DSS extraction failed for {dss_file}\n{stdout}\n{stderr}")

    pathname = None
    hec_times = []
    values = []
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if line.startswith("SELECTED|"):
            pathname = line.split("|", 1)[1]
        elif line.startswith("DATA|"):
            _, time_text, value_text = line.split("|", 2)
            hec_times.append(int(time_text))
            values.append(float(value_text))

    if pathname is None or not values:
        raise RuntimeError(f"No PRECIP-INC data parsed from HMS Jython output for {dss_file}")

    datetimes = [HEC_EPOCH + pd.Timedelta(minutes=time) for time in hec_times]
    return pathname, pd.DataFrame({"datetime": datetimes, "value": values})


def _read_precip_timeseries(dss_file: Path, run_name: str) -> tuple[str, pd.DataFrame]:
    if DssCore.is_available():
        catalog = DssCore.get_catalog(dss_file)
        pathname = _select_precip_path(catalog, run_name)
        return pathname, DssCore.read_timeseries(dss_file, pathname)

    return _read_precip_with_hms_jython(dss_file, run_name)


def _write_fixtures(
    project_dir: Path,
    fixture_dir: Path,
    source_project: Path,
    method: str = DEFAULT_METHOD,
) -> pd.DataFrame:
    fixture_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    metadata_cases = []

    for case in CASES:
        dss_file = project_dir / f"{case.run_name}.dss"
        pathname, precip = _read_precip_timeseries(dss_file, case.run_name)
        values = precip["value"].to_numpy(dtype=float)
        generated = _generated_values(case)
        diff = generated - values

        if len(values) != len(generated):
            raise RuntimeError(f"{case.test_id} length mismatch: HMS={len(values)} Python={len(generated)}")

        time_hours = np.arange(1, len(values) + 1, dtype=float) * case.interval_minutes / 60.0
        fixture = pd.DataFrame(
            {
                "test_id": case.test_id,
                "storm_type": case.storm_type,
                "total_depth_inches": case.total_depth_inches,
                "duration_hours": case.duration_hours,
                "interval_minutes": case.interval_minutes,
                "hms_version": "4.13",
                "source_project": str(source_project),
                "dss_pathname": pathname,
                "datetime": precip["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S"),
                "hour": time_hours,
                "hms_precip_inc": values,
            }
        )
        fixture_path = fixture_dir / case.fixture_name
        fixture.to_csv(fixture_path, index=False, float_format="%.12g")

        max_abs_diff = float(np.max(np.abs(diff)))
        total_diff = float(generated.sum() - values.sum())
        row = {
            "test_id": case.test_id,
            "fixture": fixture_path.name,
            "storm_type": case.storm_type,
            "rows": int(len(values)),
            "hms_total_inches": float(values.sum()),
            "python_total_inches": float(generated.sum()),
            "max_abs_diff_inches": max_abs_diff,
            "total_diff_inches": total_diff,
            "dss_pathname": pathname,
        }
        rows.append(row)
        metadata_cases.append({**row, "dss_file": str(dss_file)})

    summary = pd.DataFrame(rows)
    summary.to_csv(fixture_dir / "summary.csv", index=False, float_format="%.12g")
    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "linear_issue": LINEAR_ISSUE,
        "hms_version": "4.13",
        "hms_install": str(HMS_INSTALL),
        "source_sample": str(SAMPLES_ZIP),
        "source_project_artifact": str(source_project),
        "method": method,
        "acceptance_max_abs_diff_inches": 0.0001,
        "cases": metadata_cases,
    }
    (fixture_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument(
        "--existing-project-dir",
        type=Path,
        help="Existing configured HMS project directory to compute/extract instead of creating a fresh project.",
    )
    parser.add_argument(
        "--skip-compute",
        action="store_true",
        help="Extract fixtures from existing DSS outputs without computing HMS runs.",
    )
    parser.add_argument("--method", default=DEFAULT_METHOD, help="Metadata method string for generated fixtures.")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args(argv)

    if args.existing_project_dir:
        project_dir = args.existing_project_dir
        if not project_dir.exists():
            raise FileNotFoundError(f"Existing project directory not found: {project_dir}")
        work_dir = project_dir.parent
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        work_dir = args.artifact_root / f"castro_ground_truth_{stamp}"
        project_dir = _extract_castro_project(work_dir)
        _configure_project(project_dir)

    logs = {}
    if not args.skip_compute:
        logs = _compute_runs(project_dir, timeout=args.timeout)

    log_dir = work_dir / "compute_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    for test_id, text in logs.items():
        (log_dir / f"{test_id}.log").write_text(text, encoding="utf-8")

    summary = _write_fixtures(project_dir, args.fixture_dir, source_project=project_dir, method=args.method)
    print(summary.to_string(index=False))
    print(f"Source HMS project: {project_dir}")
    print(f"Fixture directory: {args.fixture_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
