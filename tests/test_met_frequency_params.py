"""Frequency-storm parsing against a delivered RBFS meteorologic file."""

from pathlib import Path

import pytest

from hms_commander import HmsMet


FIXTURE = Path(__file__).parent / 'fixtures/frequency_storm/01PCT_24hr.met'
DEPTHS = [1.3, 2.58, 5.02, 7.17, 8.74, 11.4, 13.9, 16.4]


def test_delivered_reference_settings_and_subbasin_curve():
    params = HmsMet.get_frequency_storm_params(FIXTURE)
    assert params['storm_size'] is None
    assert params['depths'] == []  # Never silently pick a basin.
    assert params['subbasin_depths'] == {'DBALO': DEPTHS}
    assert params['storm_type'] == 'Hydro-35/TP-40/TP-49'
    assert params['depth_area_reduction_method'] == 'No Reduction'
    assert params['uniform_depth_duration_curve'] is False
    assert params['single_hypothetical_storm_size'] is True
    assert params['user_specified_storm_area'] is False
    assert params['unit_system'] == 'English'
    assert params['total_duration'] == 1440
    assert params['time_interval'] == 5
    assert params['peak_position'] == 50
    assert params['convert_from_annual'] is True
    assert params['convert_to_annual'] is True
    assert HmsMet.get_frequency_storm_params(FIXTURE, subbasin='DBALO')['depths'] == DEPTHS


def test_explicit_selection_with_multiple_basins(tmp_path):
    path = tmp_path / 'two.met'
    path.write_text(FIXTURE.read_text() + '\nSubbasin: Other\n     Depth: 7\nEnd:\n')
    params = HmsMet.get_frequency_storm_params(path)
    assert params['depths'] == []
    assert params['subbasin_depths'] == {'DBALO': DEPTHS, 'Other': [7.0]}
    assert HmsMet.get_frequency_storm_params(path, subbasin='Other')['depths'] == [7.0]
    with pytest.raises(ValueError, match='Subbasin'):
        HmsMet.get_frequency_storm_params(path, subbasin='Missing')


@pytest.mark.parametrize('field', ['Storm Size', 'Total Duration', 'Time Interval',
                                  'Percent of Duration Before Peak Rainfall'])
def test_blank_optional_numeric_fields(tmp_path, field):
    path = tmp_path / 'blank.met'
    text = FIXTURE.read_text()
    lines = [f'     {field}: ' if line.strip().startswith(field + ':') else line
             for line in text.splitlines()]
    path.write_text('\n'.join(lines))
    key = {'Storm Size': 'storm_size', 'Total Duration': 'total_duration',
           'Time Interval': 'time_interval',
           'Percent of Duration Before Peak Rainfall': 'peak_position'}[field]
    assert HmsMet.get_frequency_storm_params(path)[key] is None


@pytest.mark.parametrize('old,new', [('     Storm Size: ', '     Storm Size: invalid'),
                                    ('Depth: 1.3000', 'Depth: invalid')])
def test_invalid_nonblank_numeric_is_not_hidden(tmp_path, old, new):
    path = tmp_path / 'invalid.met'
    path.write_text(FIXTURE.read_text().replace(old, new, 1))
    with pytest.raises(ValueError):
        HmsMet.get_frequency_storm_params(path)


def test_interior_blank_preserves_duration_position(tmp_path):
    path = tmp_path / 'gap.met'
    path.write_text(FIXTURE.read_text().replace('Depth: 2.5800', 'Depth: '))
    assert HmsMet.get_frequency_storm_params(path, subbasin='DBALO')['depths'] == [
        1.3, None, 5.02, 7.17, 8.74, 11.4, 13.9, 16.4]


def test_global_curve_preserved_with_subbasin_metadata(tmp_path):
    path = tmp_path / 'global.met'
    text = FIXTURE.read_text().replace('     Depth: \n', '     Depth: 9.25\n', 1)
    path.write_text(text)
    params = HmsMet.get_frequency_storm_params(path)
    assert params['depths'] == [9.25]
    assert params['subbasin_depths']['DBALO'] == DEPTHS


def test_explicit_selector_without_parameters_raises(tmp_path):
    path = tmp_path / 'no_parameters.met'
    path.write_text('Meteorology: Empty\n     Unit System: English\nEnd:\n')
    assert HmsMet.get_frequency_storm_params(path)['depths'] == []
    with pytest.raises(ValueError, match='no Precip Method Parameters'):
        HmsMet.get_frequency_storm_params(path, subbasin='DBALO')
