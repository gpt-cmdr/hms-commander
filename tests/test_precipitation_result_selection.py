"""Select the physical rainfall quantity from a real HMS example catalog."""
import json
from pathlib import Path
import pandas as pd
import pytest
from hms_commander import HmsResults
from hms_commander.dss import HmsDss

CATALOG=json.loads((Path(__file__).parent/'fixtures/tenk_catalog/precipitation.json').read_text())

@pytest.mark.parametrize('catalog', [CATALOG, list(reversed(CATALOG))])
def test_real_tenk_catalog_selects_interval_depth(monkeypatch, tmp_path, catalog):
    selected=[]
    monkeypatch.setattr(HmsDss,'get_catalog',lambda _:catalog)
    def read(_,path):
        selected.append(path)
        return pd.DataFrame({'value':[1.0]})
    monkeypatch.setattr(HmsDss,'read_timeseries',read)
    result=HmsResults.get_precipitation_timeseries(tmp_path/'results.dss','85','Jan 96 storm')
    assert '/PRECIP-INC/' in selected[0]
    assert result.precipitation.tolist()==[1.0]

def test_no_diagnostic_or_cumulative_fallback(monkeypatch,tmp_path):
    monkeypatch.setattr(HmsDss,'get_catalog',lambda _:[p for p in CATALOG if '/PRECIP-INC/' not in p])
    with pytest.raises(ValueError,match='No interval precipitation'):
        HmsResults.get_precipitation_timeseries(tmp_path/'results.dss','85')

def test_legacy_precip_and_exact_run(monkeypatch,tmp_path):
    paths=['//85/PRECIP-INC//1HOUR/RUN:OTHER/', '//85/PRECIP//1HOUR/RUN:JAN 96 STORM/']
    selected=[]
    monkeypatch.setattr(HmsDss,'get_catalog',lambda _:paths)
    def read(_,path):
        selected.append(path)
        return pd.DataFrame({'value':[2.0]})
    monkeypatch.setattr(HmsDss,'read_timeseries',read)
    HmsResults.get_precipitation_timeseries(tmp_path/'results.dss','85','Jan 96 storm')
    assert selected==[paths[1]]

def test_incremental_preferred_over_legacy(monkeypatch,tmp_path):
    paths=['//85/PRECIP//1HOUR/RUN:JAN 96 STORM/', '//85/PRECIP-INC//1HOUR/RUN:JAN 96 STORM/']
    selected=[]
    monkeypatch.setattr(HmsDss,'get_catalog',lambda _:paths)
    def read(_,path):
        selected.append(path)
        return pd.DataFrame({'value':[2.0]})
    monkeypatch.setattr(HmsDss,'read_timeseries',read)
    HmsResults.get_precipitation_timeseries(tmp_path/'results.dss','85','Jan 96 storm')
    assert selected==[paths[1]]
