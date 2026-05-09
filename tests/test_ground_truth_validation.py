"""Ground-truth validation against HEC-HMS 4.13 PRECIP-INC fixtures."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from hms_commander import Atlas14Storm, FrequencyStorm, ScsTypeStorm


FIXTURE_ROOT = Path(__file__).parent / "fixtures"
CLB536_FIXTURE_DIR = FIXTURE_ROOT / "clb536_storm_ground_truth"
ATLAS14_PRECIP_DIR = FIXTURE_ROOT / "atlas14" / "precip_inc"
ATLAS14_TEMPORAL_CACHE = FIXTURE_ROOT / "atlas14" / "temporal"
ACCEPTANCE_THRESHOLD_INCHES = 0.001


@dataclass(frozen=True)
class GroundTruthCase:
    test_id: str
    generator: str
    fixture_dir: Path
    fixture: str
    expected_rows: int
    total_depth_inches: float
    duration_hours: int
    interval_minutes: int
    scs_type: str | None = None
    atlas_params: dict[str, Any] | None = None

    @property
    def fixture_path(self) -> Path:
        return self.fixture_dir / self.fixture

    @property
    def case_id(self) -> str:
        return f"{self.generator}-{self.test_id}"


def _load_clb536_cases() -> list[GroundTruthCase]:
    metadata = json.loads((CLB536_FIXTURE_DIR / "metadata.json").read_text(encoding="utf-8"))
    cases = []
    for item in metadata["cases"]:
        fixture = pd.read_csv(CLB536_FIXTURE_DIR / item["fixture"], nrows=1)
        storm_type = item["storm_type"]
        if storm_type.startswith("SCS Type "):
            generator = "scs"
            scs_type = storm_type.removeprefix("SCS Type ")
        elif storm_type == "Frequency Storm (TP-40)":
            generator = "frequency"
            scs_type = None
        else:
            raise ValueError(f"Unexpected CLB-536 storm type: {storm_type}")

        cases.append(
            GroundTruthCase(
                test_id=item["test_id"],
                generator=generator,
                fixture_dir=CLB536_FIXTURE_DIR,
                fixture=item["fixture"],
                expected_rows=int(item["rows"]),
                total_depth_inches=float(fixture["total_depth_inches"].iloc[0]),
                duration_hours=int(fixture["duration_hours"].iloc[0]),
                interval_minutes=int(fixture["interval_minutes"].iloc[0]),
                scs_type=scs_type,
            )
        )
    return cases


def _load_atlas14_cases() -> list[GroundTruthCase]:
    metadata = json.loads((ATLAS14_PRECIP_DIR / "metadata.json").read_text(encoding="utf-8"))
    cases = []
    for item in metadata["cases"]:
        if item["storm_type"] != "Atlas 14 Specified Pattern":
            continue
        params = item["storm_params"]
        cases.append(
            GroundTruthCase(
                test_id=item["test_id"],
                generator="atlas14",
                fixture_dir=ATLAS14_PRECIP_DIR,
                fixture=item["csv"],
                expected_rows=int(item["rows"]),
                total_depth_inches=float(params["total_depth_inches"]),
                duration_hours=int(params["duration_hours"]),
                interval_minutes=int(params["interval_minutes"]),
                atlas_params=params,
            )
        )
    return cases


CLB536_CASES = _load_clb536_cases()
ATLAS14_CASES = _load_atlas14_cases()
ALL_CASES = CLB536_CASES + ATLAS14_CASES


def _hms_values_and_hours(case: GroundTruthCase) -> tuple[np.ndarray, np.ndarray]:
    fixture = pd.read_csv(case.fixture_path)
    if "hms_precip_inc" in fixture.columns:
        values = fixture["hms_precip_inc"].to_numpy(dtype=float)
        hours = fixture["hour"].to_numpy(dtype=float)
    else:
        values = fixture["precip_inc_inches"].to_numpy(dtype=float)
        hours = fixture["time_step_minutes"].to_numpy(dtype=float) / 60.0
    return values, hours


def _python_hyetograph(case: GroundTruthCase) -> pd.DataFrame:
    if case.generator == "scs":
        if case.scs_type is None:
            raise AssertionError("SCS ground-truth case is missing scs_type")
        return ScsTypeStorm.generate_hyetograph(
            total_depth_inches=case.total_depth_inches,
            scs_type=case.scs_type,
            time_interval_min=case.interval_minutes,
        )

    if case.generator == "frequency":
        return FrequencyStorm.generate_hyetograph(
            total_depth_inches=case.total_depth_inches,
            total_duration_min=case.duration_hours * 60,
            time_interval_min=case.interval_minutes,
            peak_position_pct=67.0,
        )

    if case.generator == "atlas14":
        if case.atlas_params is None:
            raise AssertionError("Atlas 14 ground-truth case is missing parameters")
        params = case.atlas_params
        return Atlas14Storm.generate_hyetograph(
            total_depth_inches=params["total_depth_inches"],
            state=params["state"],
            region=params["region"],
            duration_hours=params["duration_hours"],
            aep_percent=params["aep_percent"],
            quartile=params["quartile"],
            interval_minutes=params["interval_minutes"],
            cache_dir=ATLAS14_TEMPORAL_CACHE,
            probability_column=params["probability_column"],
        )

    raise AssertionError(f"Unexpected generator type: {case.generator}")


def _python_values_and_hours(case: GroundTruthCase) -> tuple[np.ndarray, np.ndarray]:
    generated = _python_hyetograph(case)
    return (
        generated["incremental_depth"].to_numpy(dtype=float)[1:],
        generated["hour"].to_numpy(dtype=float)[1:],
    )


def test_ground_truth_metadata_is_complete() -> None:
    clb536_metadata = json.loads((CLB536_FIXTURE_DIR / "metadata.json").read_text(encoding="utf-8"))
    atlas14_metadata = json.loads((ATLAS14_PRECIP_DIR / "metadata.json").read_text(encoding="utf-8"))

    assert clb536_metadata["linear_issue"] == "CLB-536"
    assert clb536_metadata["hms_version"] == "4.13"
    assert clb536_metadata["acceptance_max_abs_diff_inches"] <= ACCEPTANCE_THRESHOLD_INCHES
    assert {case.test_id for case in CLB536_CASES} == {case["test_id"] for case in clb536_metadata["cases"]}

    scs_coverage = {
        (case.scs_type, case.interval_minutes)
        for case in CLB536_CASES
        if case.generator == "scs"
    }
    assert scs_coverage == {
        ("I", 5),
        ("I", 60),
        ("IA", 5),
        ("IA", 60),
        ("II", 5),
        ("II", 60),
        ("III", 5),
        ("III", 60),
    }
    assert any(case.generator == "frequency" for case in CLB536_CASES)

    assert atlas14_metadata["hms_version"] == "4.13"
    assert atlas14_metadata["acceptance_max_abs_diff_inches"] <= ACCEPTANCE_THRESHOLD_INCHES
    assert len(ATLAS14_CASES) >= 3
    assert {
        (case.atlas_params["state"], case.atlas_params["region"])
        for case in ATLAS14_CASES
        if case.atlas_params is not None
    } == {("tx", 3)}


@pytest.mark.parametrize("case", ALL_CASES, ids=[case.case_id for case in ALL_CASES])
def test_python_hyetograph_matches_hms_precip_inc(case: GroundTruthCase) -> None:
    hms_values, hms_hours = _hms_values_and_hours(case)
    python_values, python_hours = _python_values_and_hours(case)

    assert len(hms_values) == case.expected_rows
    assert len(python_values) == len(hms_values)
    assert np.allclose(python_hours, hms_hours, atol=1e-9)

    per_interval_diff = np.abs(python_values - hms_values)
    assert float(per_interval_diff.max()) <= ACCEPTANCE_THRESHOLD_INCHES

    assert abs(float(python_values.sum()) - case.total_depth_inches) <= ACCEPTANCE_THRESHOLD_INCHES
    assert abs(float(hms_values.sum()) - case.total_depth_inches) <= ACCEPTANCE_THRESHOLD_INCHES

    python_peak_idx = int(np.argmax(python_values))
    hms_peak_idx = int(np.argmax(hms_values))
    assert hms_values[python_peak_idx] >= hms_values[hms_peak_idx] - ACCEPTANCE_THRESHOLD_INCHES
    assert python_values[hms_peak_idx] >= python_values[python_peak_idx] - ACCEPTANCE_THRESHOLD_INCHES
    assert abs(float(python_values[python_peak_idx] - hms_values[hms_peak_idx])) <= ACCEPTANCE_THRESHOLD_INCHES
