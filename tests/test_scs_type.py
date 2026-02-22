"""
Unit Tests: ScsTypeStorm Module

Tests the SCS Type I, IA, II, III hyetograph generation functionality.

Tests validate:
1. All 4 SCS types generate correctly (I, IA, II, III)
2. Depth conservation to < 10^-6 inches
3. Peak positions match published TR-55 values
4. Various time intervals work correctly
5. Error handling for invalid inputs
6. Pattern loading and caching

Usage:
    pytest tests/test_scs_type.py -v
    python tests/test_scs_type.py
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

# Add parent directory to path for development
current_file = Path(__file__).resolve()
parent_directory = current_file.parent.parent
sys.path.insert(0, str(parent_directory))

from hms_commander import ScsTypeStorm


class TestScsTypeStormBasic:
    """Basic functionality tests for ScsTypeStorm."""

    def test_import(self):
        """Test that ScsTypeStorm can be imported."""
        from hms_commander import ScsTypeStorm
        assert ScsTypeStorm is not None

    def test_list_types(self):
        """Test listing available SCS types."""
        types = ScsTypeStorm.list_types()
        assert types == ['I', 'IA', 'II', 'III']

    def test_generate_type_ii(self):
        """Test generating SCS Type II hyetograph (most common)."""
        hyeto = ScsTypeStorm.generate_hyetograph(
            total_depth_inches=10.0,
            scs_type='II',
            time_interval_min=60
        )

        assert hyeto is not None
        assert len(hyeto) == 25  # 24 hours / 1 hour + 1 (includes t=0)
        assert hyeto['incremental_depth'].iloc[0] == 0.0  # t=0 should be zero

    def test_case_insensitive(self):
        """Test that SCS type is case-insensitive."""
        hyeto1 = ScsTypeStorm.generate_hyetograph(10.0, 'ii', 60)
        hyeto2 = ScsTypeStorm.generate_hyetograph(10.0, 'II', 60)
        hyeto3 = ScsTypeStorm.generate_hyetograph(10.0, 'Ii', 60)

        assert np.allclose(hyeto1, hyeto2)
        assert np.allclose(hyeto2, hyeto3)


class TestDepthConservation:
    """Tests for depth conservation (critical for hydrologic modeling)."""

    @pytest.mark.parametrize("scs_type", ['I', 'IA', 'II', 'III'])
    def test_depth_conservation_all_types(self, scs_type):
        """Test that all SCS types conserve total depth exactly."""
        total_depth = 17.9  # 100-yr, 24-hr depth for Houston

        hyeto = ScsTypeStorm.generate_hyetograph(
            total_depth_inches=total_depth,
            scs_type=scs_type,
            time_interval_min=60
        )

        # Must match to within 10^-6 inches (HMS precision)
        assert abs(hyeto['cumulative_depth'].iloc[-1] - total_depth) < 1e-6, \
            f"Type {scs_type}: Expected {total_depth}, got {hyeto['cumulative_depth'].iloc[-1]}"

    @pytest.mark.parametrize("interval", [5, 10, 15, 30, 60])
    def test_depth_conservation_all_intervals(self, interval):
        """Test depth conservation at various time intervals."""
        total_depth = 10.0

        hyeto = ScsTypeStorm.generate_hyetograph(
            total_depth_inches=total_depth,
            scs_type='II',
            time_interval_min=interval
        )

        assert abs(hyeto['cumulative_depth'].iloc[-1] - total_depth) < 1e-6, \
            f"Interval {interval}: Expected {total_depth}, got {hyeto['cumulative_depth'].iloc[-1]}"

    @pytest.mark.parametrize("depth", [1.0, 5.0, 10.0, 20.0, 50.0])
    def test_depth_conservation_various_depths(self, depth):
        """Test depth conservation for various total depths."""
        hyeto = ScsTypeStorm.generate_hyetograph(
            total_depth_inches=depth,
            scs_type='II',
            time_interval_min=60
        )

        assert abs(hyeto['cumulative_depth'].iloc[-1] - depth) < 1e-6, \
            f"Depth {depth}: Expected {depth}, got {hyeto['cumulative_depth'].iloc[-1]}"


class TestPeakPositions:
    """Tests for peak position accuracy (matches TR-55)."""

    # Expected peak positions from TR-55 (approximate %)
    EXPECTED_PEAKS = {
        'I': (35, 45),    # ~41% (coastal Pacific)
        'IA': (28, 38),   # ~32% (Pacific Northwest)
        'II': (45, 55),   # ~50% (most of US)
        'III': (45, 55)   # ~50% (Gulf/Atlantic coastal)
    }

    @pytest.mark.parametrize("scs_type,expected_range", [
        ('I', (35, 45)),
        ('IA', (28, 38)),
        ('II', (45, 55)),
        ('III', (45, 55))
    ])
    def test_peak_position(self, scs_type, expected_range):
        """Test that peak positions match TR-55 published values."""
        hyeto = ScsTypeStorm.generate_hyetograph(
            total_depth_inches=10.0,
            scs_type=scs_type,
            time_interval_min=60
        )

        # Find peak position as percentage of storm duration
        peak_idx = hyeto['incremental_depth'].argmax()
        peak_pct = peak_idx / (len(hyeto) - 1) * 100

        # Check within expected range (±5%)
        assert expected_range[0] <= peak_pct <= expected_range[1], \
            f"Type {scs_type}: Peak at {peak_pct:.1f}%, expected {expected_range}"

    def test_peak_position_getter(self):
        """Test get_peak_position() method."""
        for scs_type in ScsTypeStorm.SCS_TYPES:
            pos = ScsTypeStorm.get_peak_position(scs_type)
            assert 0.0 < pos < 1.0, f"Type {scs_type}: Invalid peak position {pos}"


class TestTimeIntervals:
    """Tests for various time intervals."""

    @pytest.mark.parametrize("interval,expected_length", [
        (5, 289),   # 1440/5 + 1
        (10, 145),  # 1440/10 + 1
        (15, 97),   # 1440/15 + 1
        (30, 49),   # 1440/30 + 1
        (60, 25),   # 1440/60 + 1
    ])
    def test_output_length(self, interval, expected_length):
        """Test that output length matches expected for time interval."""
        hyeto = ScsTypeStorm.generate_hyetograph(
            total_depth_inches=10.0,
            scs_type='II',
            time_interval_min=interval
        )

        assert len(hyeto) == expected_length, \
            f"Interval {interval}: Expected {expected_length} values, got {len(hyeto)}"

    def test_t0_is_zero(self):
        """Test that t=0 value is always zero (HMS convention)."""
        for interval in [5, 10, 15, 30, 60]:
            hyeto = ScsTypeStorm.generate_hyetograph(10.0, 'II', interval)
            assert hyeto['incremental_depth'].iloc[0] == 0.0, f"Interval {interval}: t=0 should be 0.0"


class TestAllTypes:
    """Tests for generate_all_types() method."""

    def test_generate_all_types(self):
        """Test generating all 4 SCS types at once."""
        storms = ScsTypeStorm.generate_all_types(
            total_depth_inches=10.0,
            time_interval_min=60
        )

        assert len(storms) == 4
        assert 'I' in storms
        assert 'IA' in storms
        assert 'II' in storms
        assert 'III' in storms

        # Each should conserve depth
        for scs_type, hyeto in storms.items():
            assert abs(hyeto['cumulative_depth'].iloc[-1] - 10.0) < 1e-6

    def test_types_are_different(self):
        """Test that different SCS types produce different hyetographs."""
        storms = ScsTypeStorm.generate_all_types(10.0, 60)

        # Compare Type I vs Type II (should be different)
        assert not np.allclose(storms['I'], storms['II'])

        # Compare Type IA vs Type III (should be different)
        assert not np.allclose(storms['IA'], storms['III'])


class TestPatternInfo:
    """Tests for pattern information methods."""

    @pytest.mark.parametrize("scs_type", ['I', 'IA', 'II', 'III'])
    def test_get_pattern_info(self, scs_type):
        """Test getting pattern info for each type."""
        info = ScsTypeStorm.get_pattern_info(scs_type)

        assert info['scs_type'] == scs_type
        assert info['num_values'] == 1441  # 24hr @ 1min
        assert info['duration_minutes'] == 1440
        assert info['duration_hours'] == 24.0
        assert 0 < info['peak_position'] < 1.0
        assert 0 < info['peak_position_hours'] < 24.0
        assert 'HEC-HMS' in info['source']
        assert 'TR-55' in info['reference']


class TestValidation:
    """Tests for validation against reference data."""

    def test_validate_against_self(self):
        """Test validation method works correctly."""
        hyeto = ScsTypeStorm.generate_hyetograph(10.0, 'II', 60)

        # Compare with itself
        metrics = ScsTypeStorm.validate_against_reference(hyeto, hyeto)

        assert metrics['rmse'] == 0.0
        assert metrics['max_abs_diff'] == 0.0
        assert metrics['total_depth_diff'] == 0.0
        assert metrics['correlation'] == 1.0
        assert metrics['pass_threshold_001'] == True

    def test_validate_different_lengths_error(self):
        """Test that validation fails for different length arrays."""
        hyeto1 = ScsTypeStorm.generate_hyetograph(10.0, 'II', 60)
        hyeto2 = ScsTypeStorm.generate_hyetograph(10.0, 'II', 30)

        with pytest.raises(ValueError, match="Length mismatch"):
            ScsTypeStorm.validate_against_reference(hyeto1, hyeto2)


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_scs_type(self):
        """Test that invalid SCS type raises error."""
        with pytest.raises(ValueError, match="Invalid SCS type"):
            ScsTypeStorm.generate_hyetograph(10.0, 'IV', 60)

    def test_invalid_scs_type_X(self):
        """Test another invalid SCS type."""
        with pytest.raises(ValueError, match="Invalid SCS type"):
            ScsTypeStorm.generate_hyetograph(10.0, 'X', 60)

    def test_invalid_interval_zero(self):
        """Test that zero interval raises error."""
        with pytest.raises(ValueError):
            ScsTypeStorm.generate_hyetograph(10.0, 'II', 0)

    def test_invalid_interval_negative(self):
        """Test that negative interval raises error."""
        with pytest.raises(ValueError):
            ScsTypeStorm.generate_hyetograph(10.0, 'II', -5)

    def test_invalid_interval_not_divisible(self):
        """Test that non-divisible interval raises error."""
        with pytest.raises(ValueError, match="does not evenly divide"):
            ScsTypeStorm.generate_hyetograph(10.0, 'II', 7)  # 1440/7 is not integer

    def test_invalid_peak_position_type(self):
        """Test that invalid type in get_peak_position raises error."""
        with pytest.raises(ValueError, match="Invalid SCS type"):
            ScsTypeStorm.get_peak_position('X')


class TestPatternCaching:
    """Tests for pattern caching functionality."""

    def test_pattern_caching(self):
        """Test that patterns are cached after first load."""
        # Clear cache first
        ScsTypeStorm._pattern_cache.clear()

        # Generate first time (loads pattern)
        ScsTypeStorm.generate_hyetograph(10.0, 'II', 60)

        # Check cache
        assert 'II' in ScsTypeStorm._pattern_cache

        # Generate again (should use cache)
        ScsTypeStorm.generate_hyetograph(10.0, 'II', 60)

        # Cache should still have only one entry for this type
        assert 'II' in ScsTypeStorm._pattern_cache


class TestDurationConstraint:
    """Tests related to 24-hour duration constraint."""

    def test_fixed_24hour_duration(self):
        """Test that duration is always 24 hours (HMS constraint)."""
        assert ScsTypeStorm.DURATION_MINUTES == 1440

        # Any interval should produce 24-hour storm
        for interval in [5, 10, 15, 30, 60]:
            hyeto = ScsTypeStorm.generate_hyetograph(10.0, 'II', interval)
            expected_steps = 1440 // interval + 1
            assert len(hyeto) == expected_steps


def run_all_tests():
    """Run all tests without pytest."""
    print("=" * 80)
    print("ScsTypeStorm Unit Tests")
    print("=" * 80)
    print()

    test_count = 0
    pass_count = 0
    fail_count = 0

    # Basic tests
    print("[TestScsTypeStormBasic]")
    tests = TestScsTypeStormBasic()

    for test_name in ['test_import', 'test_list_types', 'test_generate_type_ii', 'test_case_insensitive']:
        test_count += 1
        try:
            getattr(tests, test_name)()
            print(f"  PASS: {test_name}")
            pass_count += 1
        except Exception as e:
            print(f"  FAIL: {test_name} - {e}")
            fail_count += 1

    # Depth conservation tests
    print("\n[TestDepthConservation]")
    tests = TestDepthConservation()

    for scs_type in ['I', 'IA', 'II', 'III']:
        test_count += 1
        try:
            tests.test_depth_conservation_all_types(scs_type)
            print(f"  PASS: test_depth_conservation_all_types({scs_type})")
            pass_count += 1
        except Exception as e:
            print(f"  FAIL: test_depth_conservation_all_types({scs_type}) - {e}")
            fail_count += 1

    for interval in [5, 10, 15, 30, 60]:
        test_count += 1
        try:
            tests.test_depth_conservation_all_intervals(interval)
            print(f"  PASS: test_depth_conservation_all_intervals({interval})")
            pass_count += 1
        except Exception as e:
            print(f"  FAIL: test_depth_conservation_all_intervals({interval}) - {e}")
            fail_count += 1

    # Peak position tests
    print("\n[TestPeakPositions]")
    tests = TestPeakPositions()

    for scs_type, expected_range in [('I', (35, 45)), ('IA', (28, 38)), ('II', (45, 55)), ('III', (45, 55))]:
        test_count += 1
        try:
            tests.test_peak_position(scs_type, expected_range)
            print(f"  PASS: test_peak_position({scs_type})")
            pass_count += 1
        except Exception as e:
            print(f"  FAIL: test_peak_position({scs_type}) - {e}")
            fail_count += 1

    # All types tests
    print("\n[TestAllTypes]")
    tests = TestAllTypes()

    for test_name in ['test_generate_all_types', 'test_types_are_different']:
        test_count += 1
        try:
            getattr(tests, test_name)()
            print(f"  PASS: {test_name}")
            pass_count += 1
        except Exception as e:
            print(f"  FAIL: {test_name} - {e}")
            fail_count += 1

    # Error handling tests
    print("\n[TestErrorHandling]")
    tests = TestErrorHandling()

    for test_name in ['test_invalid_scs_type', 'test_invalid_interval_zero',
                      'test_invalid_interval_negative', 'test_invalid_interval_not_divisible']:
        test_count += 1
        try:
            getattr(tests, test_name)()
            print(f"  PASS: {test_name}")
            pass_count += 1
        except Exception as e:
            print(f"  FAIL: {test_name} - {e}")
            fail_count += 1

    # Summary
    print()
    print("=" * 80)
    print(f"SUMMARY: {pass_count}/{test_count} tests passed")
    if fail_count > 0:
        print(f"         {fail_count} tests failed")
    print("=" * 80)

    return fail_count == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
