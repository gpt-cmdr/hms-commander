"""Cell lattices in ``HmsGrid``: cell polygons, remapping a cell file to SHG, and the
check of a cell file against a DSS grid record.

The HRAP checks use the tenk sample from an installed HEC-HMS (``HmsExamples``); they
skip without one. The rest use a small cell file written in the test.
"""

from pathlib import Path

import numpy as np
import pytest

gpd = pytest.importorskip("geopandas")
pytest.importorskip("pyproj")

from hms_commander import HmsGrid  # noqa: E402

CELLS = """Parameter Order: xCoord yCoord TravelLength Area
End:
SUBBASIN:  A
GRIDCELL:  10  20  5.00  4.0000
GRIDCELL:  11  20  7.00  2.0000
END:
SUBBASIN:  B
GRIDCELL:  12  21  3.00  1.0000
END:
"""


@pytest.fixture
def cell_file(tmp_path):
    path = tmp_path / "cells"
    path.write_text(CELLS)
    return path


def test_cell_polygons_on_shg(cell_file):
    cells = HmsGrid.get_cell_polygons(cell_file, "SHG")
    assert list(cells["subbasin"]) == ["A", "A", "B"]
    assert cells.crs.to_epsg() == 5070
    assert cells.geometry[0].bounds == (20000.0, 40000.0, 22000.0, 42000.0)
    assert cells.geometry.area.tolist() == [4e6, 4e6, 4e6]
    cells_1k = HmsGrid.get_cell_polygons(cell_file, "SHG", cell_size=1000)
    assert cells_1k.geometry[2].bounds == (12000.0, 21000.0, 13000.0, 22000.0)


def test_lattice_arguments(cell_file):
    with pytest.raises(ValueError, match="4762.5"):
        HmsGrid.get_cell_polygons(cell_file, "HRAP", cell_size=2000)
    with pytest.raises(ValueError, match="cell_size"):
        HmsGrid.get_cell_polygons(cell_file, "EPSG:5070")
    with pytest.raises(ValueError, match="crs"):
        HmsGrid.get_cell_polygons(cell_file, {"cell_size": 2000.0})
    grid = {"crs": "EPSG:5070", "cell_size": 2000.0}
    assert len(HmsGrid.get_cell_polygons(cell_file, grid)) == 3


def test_remap_to_a_finer_lattice_keeps_areas_and_travel(cell_file, tmp_path):
    out = HmsGrid.remap_cell_file(cell_file, tmp_path / "fine", "SHG", "SHG",
                                  target_cell_size=1000, source_cell_size=2000)
    cells = HmsGrid.read_hrapcells(out)
    assert set(cells) == {"A", "B"}
    assert sum(c["area"] for c in cells["A"]) == pytest.approx(6.0, abs=1e-3)
    assert sum(c["area"] for c in cells["B"]) == pytest.approx(1.0, abs=1e-3)
    # Each 2 km cell splits into four 1 km cells with a quarter of its area each.
    assert len(cells["A"]) == 8 and len(cells["B"]) == 4
    first = {(c["x"], c["y"]): c for c in cells["A"]}
    assert first[(20, 40)]["area"] == pytest.approx(1.0, abs=1e-4)
    assert first[(20, 40)]["travel_length"] == pytest.approx(5.0)
    assert first[(22, 40)]["area"] == pytest.approx(0.5, abs=1e-4)
    assert first[(22, 40)]["travel_length"] == pytest.approx(7.0)


def test_check_cells_on_grid(cell_file):
    # Grid with lower-left cell (10, 20), 2 rows and 2 columns: cell (12, 21) is outside.
    data = np.array([[1.0, np.nan], [3.0, 4.0]])  # row 0 is the southern row
    report = HmsGrid.check_cells_on_grid(cell_file, {"data": data,
                                                     "lower_left_cell": (10, 20)})
    a = report.loc["A"]
    assert (a["cells"], a["cells_outside"], a["cells_missing"]) == (2, 0, 1)
    assert a["area_missing_km2"] == 2.0 and a["weighted_value"] == 1.0
    b = report.loc["B"]
    assert (b["cells_outside"], b["area_outside_km2"]) == (1, 1.0)
    assert np.isnan(b["weighted_value"])


def _tenk_cells(tmp_path):
    hms = pytest.importorskip("hms_commander").HmsExamples
    try:
        versions = hms.detect_installed_versions()
    except Exception:  # pragma: no cover - depends on the host
        versions = {}
    if "4.13" not in versions:
        pytest.skip("HEC-HMS 4.13 with samples.zip is not installed")
    project = Path(hms.extract_project("tenk", version="4.13", output_path=tmp_path))
    return project / "regions" / "hrapcells"


def test_tenk_hrap_cells_are_the_sample_areas(tmp_path):
    """A whole HRAP cell at Tenkiller is 16.5 km2; the file's largest areas match it."""
    cells = HmsGrid.get_cell_polygons(_tenk_cells(tmp_path), "HRAP")
    whole = cells.to_crs(5070).geometry.area / 1e6
    largest = cells["area"].max()
    assert 16.3 < largest <= 16.6
    full = cells["area"] >= largest - 1e-9
    np.testing.assert_allclose(whole[full], cells.loc[full, "area"], rtol=0.005)
    centre = cells.to_crs(4326).geometry.union_all().centroid
    assert -95.5 < centre.x < -94.0 and 35.5 < centre.y < 36.8  # Illinois River, OK/AR


def test_tenk_remap_to_shg_keeps_each_subbasin_area(tmp_path):
    source = _tenk_cells(tmp_path)
    out = HmsGrid.remap_cell_file(source, tmp_path / "shgcells")
    before = {k: sum(c["area"] for c in v) for k, v in HmsGrid.read_hrapcells(source).items()}
    after = {k: sum(c["area"] for c in v) for k, v in HmsGrid.read_hrapcells(out).items()}
    assert before.keys() == after.keys()
    for name in before:
        assert after[name] == pytest.approx(before[name], rel=1e-5), name
    shg = HmsGrid.get_cell_polygons(out, "SHG")
    hrap = HmsGrid.get_cell_polygons(source, "HRAP").to_crs(5070)
    assert shg.union_all().buffer(1.0).contains(hrap.union_all())


# ---------------------------------------------------------------------------
# Lattices whose cell (0, 0) is not at the CRS origin (a grid dict's cell_zero)
# ---------------------------------------------------------------------------

OFFSET_GRID = {"crs": "EPSG:5070", "cell_size": 2000.0, "cell_zero": (100000.0, 200000.0),
               "lower_left_cell": (10, 20), "origin": (120000.0, 240000.0)}


def _one_cell(tmp_path, x=10, y=20, area=4.0):
    path = tmp_path / "one"
    path.write_text("Parameter Order: xCoord yCoord TravelLength Area\nEnd:\n"
                    f"SUBBASIN: A\nGRIDCELL: {x} {y} 5.0 {area}\nEND:\n")
    return path


def test_grid_dict_cell_zero_is_respected(tmp_path):
    """The reviewer's case: cell (10, 20) of a 2 km grid whose cell (0, 0) is at
    (100000, 200000) covers (120000, 240000) to (122000, 242000)."""
    cells = HmsGrid.get_cell_polygons(_one_cell(tmp_path), OFFSET_GRID)
    assert cells.geometry.iloc[0].bounds == (120000.0, 240000.0, 122000.0, 242000.0)


def test_cell_zero_from_origin_when_not_stated(tmp_path):
    grid = {k: v for k, v in OFFSET_GRID.items() if k != "cell_zero"}
    cells = HmsGrid.get_cell_polygons(_one_cell(tmp_path), grid)
    assert cells.geometry.iloc[0].bounds == (120000.0, 240000.0, 122000.0, 242000.0)
    no_offset = {"crs": "EPSG:5070", "cell_size": 2000.0}
    assert HmsGrid.get_cell_polygons(_one_cell(tmp_path), no_offset).geometry.iloc[0].bounds \
        == (20000.0, 40000.0, 22000.0, 42000.0)
    with pytest.raises(ValueError, match="cell_zero"):
        HmsGrid.get_cell_polygons(_one_cell(tmp_path), {**OFFSET_GRID,
                                                        "cell_zero": (float("nan"), 0.0)})


def test_remap_from_an_offset_source(tmp_path):
    """Source cell (10, 20) with cell_zero (100000, 200000) is the SHG square
    (120000, 240000)-(122000, 242000): SHG cell (60, 120) at 2 km."""
    out = HmsGrid.remap_cell_file(_one_cell(tmp_path), tmp_path / "shg", OFFSET_GRID, "SHG")
    cells = HmsGrid.read_hrapcells(out)["A"]
    assert [(c["x"], c["y"]) for c in cells] == [(60, 120)]
    assert cells[0]["area"] == pytest.approx(4.0, abs=1e-4)


def test_remap_to_an_offset_target(tmp_path):
    """SHG cell (60, 120) lies in cell (10, 20) of the offset grid; at 1 km the target
    lattice's indexes count from its own cell_zero."""
    source = _one_cell(tmp_path, 60, 120)
    out = HmsGrid.remap_cell_file(source, tmp_path / "t2", "SHG", OFFSET_GRID)
    cells = HmsGrid.read_hrapcells(out)["A"]
    assert [(c["x"], c["y"]) for c in cells] == [(10, 20)]
    fine = {**OFFSET_GRID, "cell_size": 1000.0, "lower_left_cell": (20, 40)}
    out = HmsGrid.remap_cell_file(source, tmp_path / "t1", "SHG", fine)
    cells = HmsGrid.read_hrapcells(out)["A"]
    assert sorted((c["x"], c["y"]) for c in cells) == [(20, 40), (20, 41), (21, 40), (21, 41)]
    assert sum(c["area"] for c in cells) == pytest.approx(4.0, abs=1e-3)
    placed = HmsGrid.get_cell_polygons(out, fine).union_all().bounds
    assert placed == (120000.0, 240000.0, 122000.0, 242000.0)


def test_remap_between_two_offset_lattices(tmp_path):
    """Half-cell offsets: each source cell splits evenly over four target cells."""
    source_grid = {"crs": "EPSG:5070", "cell_size": 2000.0, "cell_zero": (1000.0, 1000.0)}
    target_grid = {"crs": "EPSG:5070", "cell_size": 2000.0, "cell_zero": (0.0, 0.0)}
    out = HmsGrid.remap_cell_file(_one_cell(tmp_path, 5, 7), tmp_path / "half",
                                  source_grid, target_grid)
    cells = HmsGrid.read_hrapcells(out)["A"]
    # Source square (11000, 15000)-(13000, 17000) covers target cells 5-6 and 7-8.
    assert sorted((c["x"], c["y"]) for c in cells) == [(5, 7), (5, 8), (6, 7), (6, 8)]
    for c in cells:
        assert c["area"] == pytest.approx(1.0, abs=1e-4)
