"""Ground-truth validation against HEC-HMS 4.13 PRECIP-INC fixtures."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hms_commander import FrequencyStorm, ScsTypeStorm


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "ground_truth"
THRESHOLD_INCHES = 0.0001


@dataclass(frozen=True)
class GroundTruthCase:
    test_id: str
    fixture: str
    expected_rows: int
    total_depth_inches: float
    interval_minutes: int
    scs_type: str | None = None
    peak_position_pct: float = 67.0


CASES = (
    GroundTruthCase(
        test_id="T01",
        fixture="t01_t01_scs_type_ii_10in_24hr_60min.csv",
        expected_rows=24,
        total_depth_inches=10.0,
        interval_minutes=60,
        scs_type="II",
    ),
    GroundTruthCase(
        test_id="T02",
        fixture="t02_t02_scs_type_ii_10in_24hr_5min.csv",
        expected_rows=288,
        total_depth_inches=10.0,
        interval_minutes=5,
        scs_type="II",
    ),
    GroundTruthCase(
        test_id="T03",
        fixture="t03_t03_scs_type_i_10in_24hr_60min.csv",
        expected_rows=24,
        total_depth_inches=10.0,
        interval_minutes=60,
        scs_type="I",
    ),
    GroundTruthCase(
        test_id="T04",
        fixture="t04_t04_scs_type_iii_10in_24hr_60min.csv",
        expected_rows=24,
        total_depth_inches=10.0,
        interval_minutes=60,
        scs_type="III",
    ),
    GroundTruthCase(
        test_id="T05",
        fixture="t05_t05_frequency_tp40_13_20in_24hr_5min.csv",
        expected_rows=288,
        total_depth_inches=13.20,
        interval_minutes=5,
    ),
)


def _fixture_values(case: GroundTruthCase) -> pd.DataFrame:
    return pd.read_csv(FIXTURE_DIR / case.fixture)


def _python_values(case: GroundTruthCase) -> np.ndarray:
    if case.scs_type:
        generated = ScsTypeStorm.generate_hyetograph(
            total_depth_inches=case.total_depth_inches,
            scs_type=case.scs_type,
            time_interval_min=case.interval_minutes,
        )
    else:
        generated = FrequencyStorm.generate_hyetograph(
            total_depth_inches=case.total_depth_inches,
            total_duration_min=24 * 60,
            time_interval_min=case.interval_minutes,
            peak_position_pct=case.peak_position_pct,
        )

    # HMS DSS PRECIP-INC omits the Python/HMS internal t=0 zero sentinel.
    return generated["incremental_depth"].to_numpy(dtype=float)[1:]


def test_ground_truth_metadata_is_complete() -> None:
    metadata = json.loads((FIXTURE_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["linear_issue"] == "CLB-581"
    assert metadata["hms_version"] == "4.13"
    assert metadata["acceptance_max_abs_diff_inches"] == THRESHOLD_INCHES
    assert {case["test_id"] for case in metadata["cases"]} == {case.test_id for case in CASES}


@pytest.mark.parametrize("case", CASES, ids=[case.test_id for case in CASES])
def test_python_hyetograph_matches_hms_precip_inc(case: GroundTruthCase) -> None:
    fixture = _fixture_values(case)
    hms_values = fixture["hms_precip_inc"].to_numpy(dtype=float)
    python_values = _python_values(case)

    assert len(hms_values) == case.expected_rows
    assert len(python_values) == len(hms_values)
    assert np.allclose(
        fixture["hour"].to_numpy(dtype=float),
        np.arange(1, case.expected_rows + 1) * case.interval_minutes / 60.0,
    )

    max_abs_diff = float(np.max(np.abs(python_values - hms_values)))
    assert max_abs_diff < THRESHOLD_INCHES
