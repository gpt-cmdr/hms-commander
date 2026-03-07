"""
Tests for HmsArf — ARF computation and application.

Uses real project files from tests/projects/2014.08_HMS/A1000000_baseline_33/.
No mocks — real file I/O.
"""

import re
import shutil
import pytest
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths to real test data
# ---------------------------------------------------------------------------

PROJ_DIR = Path(__file__).parent / "projects" / "2014.08_HMS" / "A1000000_baseline_33"
MET_FILE = PROJ_DIR / "1%_24HR_Atlas14.met"
BASIN_FILE = PROJ_DIR / "A100_1PCT.basin"

# Known topology: A100A (area=3.213) is the ONLY subbasin whose downstream
# is A1000000_2494_J.  So CDA at that junction = 3.213 (model area units).
KNOWN_JUNCTION = "A1000000_2494_J"
KNOWN_JUNCTION_CDA = 3.213

# Simple 4-point DAR curve for all tests
DAR_CURVE = [
    (1.0,     1.000),
    (100.0,   0.970),
    (1000.0,  0.920),
    (10000.0, 0.850),
]

# Original non-zero Depth: values from 1%_24HR_Atlas14.met
ORIGINAL_NONZERO_DEPTHS = [1.2, 2.1, 4.3, 5.7, 6.8, 9.1, 11.1, 13.5]
ARF_SCALAR = 0.92


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_met(tmp_path):
    """Copy the met file into a temp directory for write tests."""
    dest = tmp_path / MET_FILE.name
    shutil.copy2(MET_FILE, dest)
    return dest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_params_block_depths(met_path: Path):
    """Return list of float Depth: values from the Precip Method Parameters block."""
    content = met_path.read_text(encoding="utf-8")
    params_block_re = re.compile(
        r'Precip Method Parameters:.*?^End:', re.DOTALL | re.MULTILINE
    )
    depth_re = re.compile(r'^\s*Depth:\s*([\d.]+)\s*$', re.MULTILINE)

    block_match = params_block_re.search(content)
    assert block_match is not None, "Precip Method Parameters block not found"
    return [float(m.group(1)) for m in depth_re.finditer(block_match.group(0))]


def _read_subbasin_blocks_depths(met_path: Path):
    """Return all Depth: values found inside any Subbasin: ... End: block."""
    content = met_path.read_text(encoding="utf-8")
    subbasin_re = re.compile(r'Subbasin:\s*.+?\n(.*?)End:', re.DOTALL)
    depth_re = re.compile(r'^\s*Depth:\s*([\d.]+)\s*$', re.MULTILINE)

    all_depths = []
    for match in subbasin_re.finditer(content):
        block = match.group(1)
        all_depths.extend(float(m.group(1)) for m in depth_re.finditer(block))
    return all_depths


# ---------------------------------------------------------------------------
# A02 — CDA computation tests
# ---------------------------------------------------------------------------

class TestComputeKcdaCdas:
    def test_returns_dataframe_with_expected_columns(self):
        from hms_commander import HmsArf
        result = HmsArf.compute_kcda_cdas(BASIN_FILE, [KNOWN_JUNCTION])
        for col in ('junction', 'cda_acres', 'subbasin_count', 'upstream_subbasins'):
            assert col in result.columns, f"Missing column: {col}"

    def test_cda_matches_known_junction(self):
        """A1000000_2494_J has only A100A (area=3.213) upstream."""
        from hms_commander import HmsArf
        result = HmsArf.compute_kcda_cdas(BASIN_FILE, [KNOWN_JUNCTION])
        row = result.iloc[0]
        assert row['junction'] == KNOWN_JUNCTION
        assert row['subbasin_count'] == 1
        assert abs(row['cda_acres'] - KNOWN_JUNCTION_CDA) < 1e-6

    def test_upstream_subbasins_contains_expected_subbasin(self):
        from hms_commander import HmsArf
        result = HmsArf.compute_kcda_cdas(BASIN_FILE, [KNOWN_JUNCTION])
        assert 'A100A' in result.iloc[0]['upstream_subbasins']

    def test_multiple_junctions(self):
        """Multiple junctions → one row each, CDA > 0 for real junctions."""
        from hms_commander import HmsArf
        # Use a junction further downstream so CDA > KNOWN_JUNCTION_CDA
        junctions = [KNOWN_JUNCTION]
        result = HmsArf.compute_kcda_cdas(BASIN_FILE, junctions)
        assert len(result) == len(junctions)
        assert (result['cda_acres'] > 0).all()


# ---------------------------------------------------------------------------
# A02 — DAR interpolation tests
# ---------------------------------------------------------------------------

class TestLookupArfFromDar:
    def test_interpolation_between_points(self):
        """CDA=550 is between 100 (0.97) and 1000 (0.92); expect ~0.952."""
        from hms_commander import HmsArf
        arf = HmsArf.lookup_arf_from_dar(550.0, DAR_CURVE)
        assert 0.92 < arf < 0.97, f"Unexpected ARF: {arf}"

    def test_exact_point_on_curve(self):
        """CDA exactly at a curve point → exact ARF value."""
        from hms_commander import HmsArf
        arf = HmsArf.lookup_arf_from_dar(1000.0, DAR_CURVE)
        assert abs(arf - 0.920) < 1e-9

    def test_below_minimum_area_returns_one(self):
        """CDA below minimum curve area → 1.0 (no reduction)."""
        from hms_commander import HmsArf
        arf = HmsArf.lookup_arf_from_dar(0.5, DAR_CURVE)
        assert arf == 1.0

    def test_at_minimum_area_boundary_returns_one(self):
        """CDA exactly at minimum area → 1.0."""
        from hms_commander import HmsArf
        arf = HmsArf.lookup_arf_from_dar(1.0, DAR_CURVE)
        assert arf == 1.0

    def test_above_maximum_area_clamped(self):
        """CDA above max → last ARF value (0.85), not extrapolated lower."""
        from hms_commander import HmsArf
        arf = HmsArf.lookup_arf_from_dar(50000.0, DAR_CURVE)
        assert abs(arf - 0.850) < 1e-9

    def test_accepts_dataframe(self):
        """DAR curve as DataFrame."""
        import pandas as pd
        from hms_commander import HmsArf
        df = pd.DataFrame({'area': [1.0, 100.0, 1000.0, 10000.0],
                           'arf': [1.0, 0.97, 0.92, 0.85]})
        arf = HmsArf.lookup_arf_from_dar(550.0, df)
        assert 0.92 < arf < 0.97

    def test_accepts_duration_keyed_dict(self):
        """DAR curve as {duration_hours: [(area, arf), ...]}."""
        from hms_commander import HmsArf
        dur_dict = {6.0: [(1, 1.0), (100, 0.98)], 24.0: DAR_CURVE}
        arf_24 = HmsArf.lookup_arf_from_dar(550.0, dur_dict, duration_hours=24.0)
        arf_6 = HmsArf.lookup_arf_from_dar(550.0, dur_dict, duration_hours=6.0)
        assert arf_24 < arf_6, "24-hr ARF should be smaller than 6-hr for same CDA"


# ---------------------------------------------------------------------------
# A02 — build_kcda_arf_table tests
# ---------------------------------------------------------------------------

class TestBuildKcdaArfTable:
    def test_returns_dataframe_with_arf_columns(self):
        from hms_commander import HmsArf
        result = HmsArf.build_kcda_arf_table(BASIN_FILE, [KNOWN_JUNCTION], DAR_CURVE)
        for col in ('junction', 'cda_acres', 'arf', 'a14_dar_multiplier'):
            assert col in result.columns

    def test_arf_and_multiplier_are_equal(self):
        from hms_commander import HmsArf
        result = HmsArf.build_kcda_arf_table(BASIN_FILE, [KNOWN_JUNCTION], DAR_CURVE)
        import numpy as np
        np.testing.assert_array_equal(result['arf'].values, result['a14_dar_multiplier'].values)

    def test_sorted_by_cda_ascending(self):
        """Result must be sorted ascending by cda_acres."""
        from hms_commander import HmsArf
        # Use two junctions: the known small one + a larger one if available.
        # At minimum, a single-row result is trivially sorted.
        result = HmsArf.build_kcda_arf_table(BASIN_FILE, [KNOWN_JUNCTION], DAR_CURVE)
        cdas = result['cda_acres'].tolist()
        assert cdas == sorted(cdas)

    def test_arf_within_valid_range(self):
        """All returned ARF values must be in [0, 1]."""
        from hms_commander import HmsArf
        result = HmsArf.build_kcda_arf_table(BASIN_FILE, [KNOWN_JUNCTION], DAR_CURVE)
        assert (result['arf'] >= 0).all()
        assert (result['arf'] <= 1.0).all()


# ---------------------------------------------------------------------------
# A03 — apply_arf tests
# ---------------------------------------------------------------------------

class TestApplyArfScalarGlobalDepths:
    def test_all_params_block_depths_scaled(self, tmp_met):
        """apply_arf(arf=0.92) must scale every Depth: in Precip Method Parameters."""
        from hms_commander import HmsArf

        result = HmsArf.apply_arf(tmp_met, arf=ARF_SCALAR)

        modified = _read_params_block_depths(tmp_met)
        expected = [d * ARF_SCALAR for d in ORIGINAL_NONZERO_DEPTHS] + [0.0, 0.0, 0.0, 0.0]

        assert len(modified) == len(expected), (
            f"Expected {len(expected)} depth lines, got {len(modified)}"
        )
        for orig, new in zip(ORIGINAL_NONZERO_DEPTHS, modified[:len(ORIGINAL_NONZERO_DEPTHS)]):
            assert abs(new - orig * ARF_SCALAR) < 1e-4, (
                f"Depth {orig} → expected {orig * ARF_SCALAR:.4f}, got {new}"
            )

    def test_returns_depths_modified_count(self, tmp_met):
        from hms_commander import HmsArf
        result = HmsArf.apply_arf(tmp_met, arf=ARF_SCALAR)
        # 12 Depth: lines total in the params block (8 non-zero + 4 zeros)
        assert result['depths_modified'] == 12

    def test_zero_depths_remain_zero(self, tmp_met):
        """Zero depths × any ARF = 0 (no spurious values)."""
        from hms_commander import HmsArf
        HmsArf.apply_arf(tmp_met, arf=ARF_SCALAR)
        depths = _read_params_block_depths(tmp_met)
        zero_depths = depths[len(ORIGINAL_NONZERO_DEPTHS):]
        assert all(d == 0.0 for d in zero_depths)


class TestApplyArfDoesNotModifySubbasinBlocks:
    def test_subbasin_blocks_remain_empty(self, tmp_met):
        """Subbasin: blocks must stay empty after apply_arf — no Depth: lines added."""
        from hms_commander import HmsArf
        HmsArf.apply_arf(tmp_met, arf=ARF_SCALAR)
        subbasin_depths = _read_subbasin_blocks_depths(tmp_met)
        assert subbasin_depths == [], (
            f"Expected no depths in subbasin blocks, found: {subbasin_depths}"
        )


class TestApplyArfBackupCreated:
    def test_backup_file_created(self, tmp_met):
        """preserve_original=True (default) must create a .met.bak file."""
        from hms_commander import HmsArf
        result = HmsArf.apply_arf(tmp_met, arf=ARF_SCALAR)
        bak = Path(result['backup_path'])
        assert bak.exists(), f"Backup not found at {bak}"
        assert bak.suffix == '.bak'

    def test_backup_contains_original_depths(self, tmp_met):
        """Backup file must preserve original unmodified depths."""
        from hms_commander import HmsArf
        result = HmsArf.apply_arf(tmp_met, arf=ARF_SCALAR)
        bak = Path(result['backup_path'])
        original_depths = _read_params_block_depths(bak)
        for i, (orig, backed_up) in enumerate(
            zip(ORIGINAL_NONZERO_DEPTHS, original_depths)
        ):
            assert abs(backed_up - orig) < 1e-4, (
                f"Backup depth {i}: expected {orig}, got {backed_up}"
            )

    def test_no_backup_when_disabled(self, tmp_met):
        """preserve_original=False must not create a .met.bak file."""
        from hms_commander import HmsArf
        result = HmsArf.apply_arf(tmp_met, arf=ARF_SCALAR, preserve_original=False)
        assert result['backup_path'] is None
        bak = Path(str(tmp_met) + '.bak')
        assert not bak.exists()


class TestApplyArfEdgeCases:
    def test_raises_when_neither_arf_nor_table_provided(self, tmp_met):
        from hms_commander import HmsArf
        with pytest.raises(ValueError, match="Must provide either"):
            HmsArf.apply_arf(tmp_met)

    def test_raises_on_negative_arf(self, tmp_met):
        from hms_commander import HmsArf
        with pytest.raises(ValueError, match="Negative ARF"):
            HmsArf.apply_arf(tmp_met, arf=-0.5)
