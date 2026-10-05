"""Tests for BalancedFrequencyStorm (HEC-HMS Frequency Storm, balanced hyetograph).

The reference series in ``tests/fixtures/hms_frequency_storm`` were produced by
HEC-HMS 4.13 (see that directory's README.md for provenance and the generator
script).  Pure computation; no HMS install or network needed to run these tests.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pytest

from hms_commander import BalancedFrequencyStorm, FrequencyStorm
from hms_commander.BalancedFrequencyStorm import BalancedFrequencyStorm as Direct

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "hms_frequency_storm"
# Acceptance target for HMS agreement is 0.001 in per interval; the implementation
# actually agrees to ~1e-12, so hold it to a much tighter bound.
HMS_TOLERANCE_IN = 1e-8
TARGET_TOLERANCE_IN = 1e-3

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
LABELS = [
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


def _load_cases():
    return json.loads((FIXTURE_DIR / "cases.json").read_text())["cases"]


def _load_series():
    out = defaultdict(list)
    with open(FIXTURE_DIR / "hms_reference_series.csv", newline="") as fh:
        for row in csv.DictReader(fh):
            out[row["case"]].append(
                (int(row["block"]), float(row["hms_incremental_in"]))
            )
    return {k: np.array([v for _, v in sorted(rows)]) for k, rows in out.items()}


CASES = _load_cases()
SERIES = _load_series()
KERRVILLE_100YR = {
    5: 1.17,
    10: 1.88,
    15: 2.32,
    30: 3.2,
    60: 4.27,
    120: 5.77,
    180: 6.82,
    360: 8.63,
    720: 10.3,
    1440: 12.1,
    2880: 14.3,
    4320: 15.5,
    5760: 16.0,
    10080: 17.0,
    14400: 17.8,
}


def _depths(case):
    d = {int(k): v for k, v in case["depths_in"].items()}
    return {k: v for k, v in d.items() if k not in case["blank_durations"]}


def _generate(case):
    legacy = case["legacy_format"]
    depths = _depths(case)
    if (
        legacy
    ):  # legacy 3.x files carry only these durations; HMS augments 10/30-min on load
        depths = {
            k: v
            for k, v in depths.items()
            if k in (5, 15, 60, 120, 180, 360, 720, 1440, 2880, 5760, 10080, 14400)
        }
    convert = (
        case["convert_to_annual"] == "Yes" and case["convert_from_annual"] != "Yes"
    )
    area = (
        case["storm_area_sqmi"] if case["user_specified_area"] else 10.0
    )  # basin area is 10 sq mi
    method = (
        "none"
        if case["extra"].get("Depth-Area Reduction Method") == "None"
        else "tp40_tp49"
    )
    return BalancedFrequencyStorm.generate_hyetograph(
        depths,
        total_duration_min=case["duration_min"],
        time_interval_min=case["interval_min"],
        peak_position_pct=case["peak_pct"],
        storm_area_sqmi=area,
        exceedance_pct=case["exceedance_pct"],
        convert_partial_to_annual=convert,
        augment=legacy,
        area_reduction=method,
    )


class TestAgainstHecHms413:
    """Per-interval agreement with HEC-HMS 4.13 reference output."""

    def test_fixture_inventory(self):
        assert len(CASES) >= 60
        assert {c["name"] for c in CASES} == set(SERIES)
        for c in CASES:
            assert len(SERIES[c["name"]]) == c["duration_min"] // c["interval_min"]

    @pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
    def test_matches_hms(self, case):
        if case["extra"].get("Re-sort Storm Symmetrically") == "Yes":
            pytest.skip("The public API deliberately does not expose HMS re-sort")
        hyeto = _generate(case)
        mine = hyeto["incremental_depth"].to_numpy()[1:]  # drop t=0 sentinel
        ref = SERIES[case["name"]]
        assert mine.shape == ref.shape
        max_diff = float(np.max(np.abs(mine - ref)))
        assert max_diff <= TARGET_TOLERANCE_IN
        assert (
            max_diff <= HMS_TOLERANCE_IN
        ), f"{case['name']}: max abs diff {max_diff:.3e} in"
        total_diff = abs(float(mine.sum() - ref.sum()))
        assert (
            total_diff <= TARGET_TOLERANCE_IN
        ), f"{case['name']}: total-depth difference {total_diff:.3e} in"

    def test_required_case_coverage(self):
        names = {c["name"] for c in CASES}
        for required in (
            "p24h15m_pk50",
            "p24h15m_pk67",
            "p6h5m_pk50",
            "pda50_24h15m",
            "ann_ann50_24h15m",
            "area50_24h15m_pk50",
            "resort_perturbed_off",
            "resort_perturbed_on",
        ):
            assert required in names

    def test_resort_perturbed_fixtures_distinguish_hms_option(self):
        by_name = {case["name"]: case for case in CASES}
        off_case = by_name["resort_perturbed_off"]
        increments = np.diff(
            np.concatenate(
                [[0.0], Direct.cumulative_depths(_depths(off_case), 360, 15)]
            )
        )
        assert np.any(np.diff(increments) > 0)
        off = SERIES["resort_perturbed_off"]
        on = SERIES["resort_perturbed_on"]
        assert float(np.max(np.abs(off - on))) > TARGET_TOLERANCE_IN


class TestBehavior:
    def test_returns_repo_dataframe_contract(self):
        df = BalancedFrequencyStorm.generate_hyetograph(KERRVILLE_100YR, 1440, 15, 50)
        assert list(df.columns) == ["hour", "incremental_depth", "cumulative_depth"]
        assert len(df) == 1440 // 15 + 1
        assert df["incremental_depth"].iloc[0] == 0.0
        assert df["hour"].iloc[-1] == pytest.approx(24.0)

    def test_total_equals_storm_duration_depth_for_point_storm(self):
        df = BalancedFrequencyStorm.generate_hyetograph(KERRVILLE_100YR, 1440, 15, 67)
        assert df["cumulative_depth"].iloc[-1] == pytest.approx(12.1)

    def test_peak_block_is_interval_duration_depth_and_position(self):
        for pk in (25, 33, 50, 67, 75):
            df = BalancedFrequencyStorm.generate_hyetograph(
                KERRVILLE_100YR, 1440, 15, pk
            )
            inc = df["incremental_depth"].to_numpy()[1:]
            assert inc.max() == pytest.approx(2.32)
            assert int(np.argmax(inc)) == int(np.floor(pk / 100 * 96 + 1e-9))

    def test_nested_depths_are_preserved(self):
        """The largest 1-hr window equals the 1-hr depth of the balanced storm."""
        df = BalancedFrequencyStorm.generate_hyetograph(KERRVILLE_100YR, 1440, 15, 50)
        inc = df["incremental_depth"].to_numpy()[1:]
        window = max(inc[i : i + 4].sum() for i in range(len(inc) - 3))  # noqa: E203
        assert window == pytest.approx(4.27, rel=1e-9)

    def test_input_sequence_matches_mapping(self):
        seq = [KERRVILLE_100YR[d] for d in DURATIONS_MIN]
        a = BalancedFrequencyStorm.generate_hyetograph(seq, 1440, 15, 50)
        b = BalancedFrequencyStorm.generate_hyetograph(KERRVILLE_100YR, 1440, 15, 50)
        assert np.allclose(a["incremental_depth"], b["incremental_depth"])

    def test_sequence_durations_must_be_unique(self):
        with pytest.raises(ValueError, match="duplicates"):
            BalancedFrequencyStorm.generate_hyetograph(
                [1.0, 2.0, 3.0], 30, 15, 50, durations_min=[15, 15, 30]
            )

    def test_sequence_depths_and_durations_must_have_equal_lengths(self):
        with pytest.raises(ValueError, match="equal lengths"):
            BalancedFrequencyStorm.generate_hyetograph(
                [KERRVILLE_100YR[5], KERRVILLE_100YR[15], KERRVILLE_100YR[30]],
                30,
                15,
                durations_min=[5, 15],
            )

    @pytest.mark.parametrize(
        "depths, message",
        [
            ({5: True, 15: 2.32}, "boolean"),
            ({5: np.nan, 15: 2.32}, "finite and positive"),
            ({5: np.inf, 15: 2.32}, "finite and positive"),
            ({5: -1.0, 15: 2.32}, "finite and positive"),
            ({5: 1.17, 15: 2.32, 30: 2.0}, "ERROR 20025"),
        ],
    )
    def test_ddf_depths_must_be_valid_and_nondecreasing(self, depths, message):
        with pytest.raises(ValueError, match=message):
            BalancedFrequencyStorm.generate_hyetograph(depths, 15, 5, 50)

    def test_area_reduction_values(self):
        arf = BalancedFrequencyStorm.areal_reduction_factor
        assert arf(60, 0) == 1.0
        # HMS 4.13: RF(1 hr, 10 sq mi) = 0.951248; RF(24 hr, 100 sq mi) = 0.930082.
        assert arf(60, 10) == pytest.approx(0.951248, abs=1e-6)
        assert arf(1440, 100) == pytest.approx(0.930082, abs=1e-6)
        # durations <= 30 min share the 30-min factor
        assert arf(5, 10) == arf(30, 10) == pytest.approx(0.93314, abs=1e-5)
        assert arf(60, 500) < arf(60, 50) < arf(60, 5) < 1.0

    def test_partial_to_annual_factors(self):
        point = BalancedFrequencyStorm.generate_hyetograph(
            KERRVILLE_100YR, 1440, 15, 50
        )
        for exc, factor in ((50, 0.88), (20, 0.96), (10, 0.99)):
            conv = BalancedFrequencyStorm.generate_hyetograph(
                KERRVILLE_100YR,
                1440,
                15,
                50,
                exceedance_pct=exc,
                convert_partial_to_annual=True,
            )
            assert conv["cumulative_depth"].iloc[-1] == pytest.approx(
                point["cumulative_depth"].iloc[-1] * factor
            )
        # no factor outside 50/20/10 percent, and none unless requested
        for kw in (
            {"exceedance_pct": 1, "convert_partial_to_annual": True},
            {"exceedance_pct": 50, "convert_partial_to_annual": False},
        ):
            other = BalancedFrequencyStorm.generate_hyetograph(
                KERRVILLE_100YR, 1440, 15, 50, **kw
            )
            assert np.allclose(other["incremental_depth"], point["incremental_depth"])

    def test_partial_to_annual_requires_exceedance_probability(self):
        with pytest.raises(ValueError, match="exceedance_pct is required"):
            BalancedFrequencyStorm.generate_hyetograph(
                KERRVILLE_100YR, 1440, 15, 50, convert_partial_to_annual=True
            )

    def test_area_over_documented_curve_limit_warns(self, caplog):
        with caplog.at_level("WARNING"):
            BalancedFrequencyStorm.generate_hyetograph(
                KERRVILLE_100YR, 1440, 15, 50, storm_area_sqmi=401
            )
        assert "400 sq mi" in caplog.text

    def test_hydro35_augmentation(self):
        d = {k: v for k, v in KERRVILLE_100YR.items() if k not in (10, 30)}
        aug = BalancedFrequencyStorm.augment_depths(d)
        assert aug[10] == pytest.approx(0.59 * 2.32 + 0.41 * 1.17)
        assert aug[30] == pytest.approx(0.49 * 4.27 + 0.51 * 2.32)
        # existing user-supplied values are not overwritten
        assert BalancedFrequencyStorm.augment_depths(KERRVILLE_100YR)[30] == 3.2

    def test_alternating_blocks_non_monotone_uses_time_order(self):
        # HMS places blocks in time order (not value order) around the peak
        out = BalancedFrequencyStorm.alternating_blocks(
            np.array([10.0, 4.0, 3.0, 3.5, 1.0]), 50
        )
        assert (
            out[2] == 10.0
            and out[1] == 4.0
            and out[3] == 3.0
            and out[0] == 3.5
            and out[4] == 1.0
        )

    def test_validation_errors(self):
        with pytest.raises(ValueError, match="storm duration"):
            BalancedFrequencyStorm.generate_hyetograph(KERRVILLE_100YR, 1000, 15, 50)
        with pytest.raises(ValueError, match="time interval"):
            BalancedFrequencyStorm.generate_hyetograph(KERRVILLE_100YR, 1440, 20, 50)
        with pytest.raises(ValueError, match="longer"):
            BalancedFrequencyStorm.generate_hyetograph(KERRVILLE_100YR, 15, 15, 50)
        with pytest.raises(ValueError, match="area_reduction"):
            BalancedFrequencyStorm.generate_hyetograph(
                KERRVILLE_100YR, 1440, 15, 50, area_reduction="x"
            )

    def test_exported_from_package(self):
        assert Direct is BalancedFrequencyStorm


class TestExistingFrequencyStormUnchanged:
    def test_legacy_frequency_storm_still_scales_fixed_pattern(self):
        df = FrequencyStorm.generate_hyetograph(13.20)
        assert len(df) == 289
        assert df["cumulative_depth"].iloc[-1] == pytest.approx(13.20, abs=1e-6)
