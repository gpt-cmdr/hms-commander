"""
Tests for HmsSqlite - HMS SQLite Grid Database Operations

Uses the river_bend example project bundled with HEC-HMS 4.x installations.
Tests are skipped if the project has not been extracted.

Test data:
    hms_example_projects/river_bend/
    - Minimum_Facility.sqlite: 2 subbasins in subbasin2d, EPSG:26916
    - All three .sqlite files are structurally identical
"""

import pytest
from pathlib import Path

# ---------------------------------------------------------------------------
# Fixture: extract river_bend example project (once per session)
# ---------------------------------------------------------------------------

RIVER_BEND_DIR = Path("hms_example_projects/river_bend")


@pytest.fixture(scope="session")
def river_bend_dir():
    """Extract river_bend if needed, return project directory."""
    if not RIVER_BEND_DIR.exists():
        try:
            from hms_commander import HmsExamples
            HmsExamples.extract_project("river_bend")
        except Exception:
            pass

    if not RIVER_BEND_DIR.exists():
        pytest.skip("river_bend example project not available (no HMS installation found)")

    return RIVER_BEND_DIR


@pytest.fixture(scope="session")
def sqlite_path(river_bend_dir):
    """Return path to the primary SQLite file."""
    path = river_bend_dir / "Minimum_Facility.sqlite"
    if not path.exists():
        pytest.skip(f"SQLite file not found: {path}")
    return path


# ===========================================================================
# list_layers
# ===========================================================================


class TestListLayers:
    """Tests for HmsSqlite.list_layers() - uses stdlib sqlite3 only."""

    def test_returns_dataframe(self, sqlite_path):
        from hms_commander import HmsSqlite

        layers = HmsSqlite.list_layers(sqlite_path)
        assert hasattr(layers, "columns"), "Should return a DataFrame"
        assert "table_name" in layers.columns
        assert "row_count" in layers.columns
        assert "geometry_type" in layers.columns

    def test_expected_layers_present(self, sqlite_path):
        from hms_commander import HmsSqlite

        layers = HmsSqlite.list_layers(sqlite_path)
        table_names = set(layers["table_name"])
        # river_bend registers 10 spatial tables in geometry_columns
        assert "subbasin2d" in table_names
        assert "reach2d" in table_names
        assert "junction" in table_names

    def test_subbasin2d_row_count(self, sqlite_path):
        from hms_commander import HmsSqlite

        layers = HmsSqlite.list_layers(sqlite_path)
        layers_dict = dict(zip(layers["table_name"], layers["row_count"]))
        assert layers_dict["subbasin2d"] == 2, "river_bend has 2 subbasins"

    def test_empty_tables_have_zero_rows(self, sqlite_path):
        from hms_commander import HmsSqlite

        layers = HmsSqlite.list_layers(sqlite_path)
        layers_dict = dict(zip(layers["table_name"], layers["row_count"]))
        # All tables except subbasin2d are empty in river_bend
        assert layers_dict.get("reach2d", 0) == 0
        assert layers_dict.get("junction", 0) == 0

    def test_file_not_found(self):
        from hms_commander import HmsSqlite

        with pytest.raises(FileNotFoundError):
            HmsSqlite.list_layers("nonexistent.sqlite")


# ===========================================================================
# get_crs
# ===========================================================================


class TestGetCrs:
    """Tests for HmsSqlite.get_crs() - uses stdlib sqlite3 only."""

    def test_returns_wkt_string(self, sqlite_path):
        from hms_commander import HmsSqlite

        wkt = HmsSqlite.get_crs(sqlite_path)
        assert wkt is not None, "Should return a WKT string"
        assert isinstance(wkt, str)
        assert "PROJCS" in wkt, "WKT should define a projected CRS"

    def test_contains_utm_zone(self, sqlite_path):
        from hms_commander import HmsSqlite

        wkt = HmsSqlite.get_crs(sqlite_path)
        assert "UTM zone 16N" in wkt, "river_bend uses NAD83 / UTM zone 16N"

    def test_epsg_26916(self, sqlite_path):
        from hms_commander import HmsSqlite

        wkt = HmsSqlite.get_crs(sqlite_path)
        assert "26916" in wkt, "EPSG:26916 should appear in WKT"

    def test_file_not_found(self):
        from hms_commander import HmsSqlite

        with pytest.raises(FileNotFoundError):
            HmsSqlite.get_crs("nonexistent.sqlite")


# ===========================================================================
# get_subbasins
# ===========================================================================


class TestGetSubbasins:
    """Tests for HmsSqlite.get_subbasins()."""

    def test_returns_geodataframe(self, sqlite_path):
        from hms_commander import HmsSqlite
        import geopandas as gpd

        subs = HmsSqlite.get_subbasins(sqlite_path)
        assert isinstance(subs, gpd.GeoDataFrame)

    def test_row_count(self, sqlite_path):
        from hms_commander import HmsSqlite

        subs = HmsSqlite.get_subbasins(sqlite_path)
        assert len(subs) == 2, f"Expected 2 subbasins, got {len(subs)}"

    def test_has_geometry(self, sqlite_path):
        from hms_commander import HmsSqlite

        subs = HmsSqlite.get_subbasins(sqlite_path)
        assert "geometry" in subs.columns
        # geometry_columns registers MULTIPOLYGON but actual WKB is Polygon
        assert subs.geom_type.iloc[0] in ("Polygon", "MultiPolygon")

    def test_has_name_column(self, sqlite_path):
        from hms_commander import HmsSqlite

        subs = HmsSqlite.get_subbasins(sqlite_path)
        assert "name" in subs.columns
        assert subs["name"].notna().all()
        names = set(subs["name"])
        assert "Upper" in names
        assert "Local" in names

    def test_has_crs(self, sqlite_path):
        from hms_commander import HmsSqlite

        subs = HmsSqlite.get_subbasins(sqlite_path)
        assert subs.crs is not None, "GeoDataFrame should have a CRS"

    def test_geometry_is_valid(self, sqlite_path):
        from hms_commander import HmsSqlite

        subs = HmsSqlite.get_subbasins(sqlite_path)
        assert subs.geometry.is_valid.all(), "All geometries should be valid"
        assert (subs.geometry.area > 0).all(), "All polygons should have area"


# ===========================================================================
# get_reaches (empty in river_bend)
# ===========================================================================


class TestGetReaches:
    """Tests for HmsSqlite.get_reaches() - empty in river_bend."""

    def test_empty_result(self, sqlite_path):
        from hms_commander import HmsSqlite
        import geopandas as gpd

        reaches = HmsSqlite.get_reaches(sqlite_path)
        assert isinstance(reaches, gpd.GeoDataFrame)
        assert len(reaches) == 0, "river_bend reach2d table is empty"


# ===========================================================================
# get_outlets (table does not exist in river_bend)
# ===========================================================================


class TestGetOutlets:
    """Tests for HmsSqlite.get_outlets() - table absent in river_bend."""

    def test_missing_table_raises(self, sqlite_path):
        from hms_commander import HmsSqlite

        with pytest.raises(ValueError, match="not found"):
            HmsSqlite.get_outlets(sqlite_path)


# ===========================================================================
# get_junctions (empty in river_bend)
# ===========================================================================


class TestGetJunctions:
    """Tests for HmsSqlite.get_junctions() - handles empty table gracefully."""

    def test_empty_result(self, sqlite_path):
        from hms_commander import HmsSqlite
        import geopandas as gpd

        junctions = HmsSqlite.get_junctions(sqlite_path)
        assert isinstance(junctions, gpd.GeoDataFrame)
        assert len(junctions) == 0, "river_bend junction table is empty"


# ===========================================================================
# read_grid_database
# ===========================================================================


class TestReadGridDatabase:
    """Tests for HmsSqlite.read_grid_database()."""

    def test_returns_dict(self, sqlite_path):
        from hms_commander import HmsSqlite

        layers = HmsSqlite.read_grid_database(sqlite_path)
        assert isinstance(layers, dict)

    def test_skip_empty_only_subbasin2d(self, sqlite_path):
        from hms_commander import HmsSqlite

        layers = HmsSqlite.read_grid_database(sqlite_path, skip_empty=True)
        # Only subbasin2d has data in river_bend
        assert "subbasin2d" in layers
        assert len(layers) == 1, f"Expected only subbasin2d, got {list(layers.keys())}"

    def test_include_empty(self, sqlite_path):
        from hms_commander import HmsSqlite

        layers = HmsSqlite.read_grid_database(sqlite_path, skip_empty=False)
        # Should include empty tables too
        assert "subbasin2d" in layers
        assert len(layers) > 1

    def test_subbasin2d_count(self, sqlite_path):
        from hms_commander import HmsSqlite

        layers = HmsSqlite.read_grid_database(sqlite_path)
        assert len(layers["subbasin2d"]) == 2


# ===========================================================================
# discover_sqlite_files
# ===========================================================================


class TestDiscoverSqliteFiles:
    """Tests for HmsSqlite.discover_sqlite_files()."""

    def test_finds_files(self, river_bend_dir):
        from hms_commander import HmsSqlite

        files = HmsSqlite.discover_sqlite_files(river_bend_dir)
        assert len(files) == 3, f"Expected 3 .sqlite files, got {len(files)}"
        assert all(f.suffix == ".sqlite" for f in files)

    def test_sorted(self, river_bend_dir):
        from hms_commander import HmsSqlite

        files = HmsSqlite.discover_sqlite_files(river_bend_dir)
        names = [f.name for f in files]
        assert names == sorted(names), "Files should be sorted"

    def test_includes_known_files(self, river_bend_dir):
        from hms_commander import HmsSqlite

        files = HmsSqlite.discover_sqlite_files(river_bend_dir)
        names = {f.name for f in files}
        assert "Minimum_Facility.sqlite" in names

    def test_nonexistent_dir(self):
        from hms_commander import HmsSqlite

        files = HmsSqlite.discover_sqlite_files("Z:/nonexistent")
        assert files == []


# ===========================================================================
# join_with_parameters
# ===========================================================================


class TestJoinWithParameters:
    """Tests for HmsSqlite.join_with_parameters()."""

    def test_basic_join(self, sqlite_path):
        import pandas as pd
        from hms_commander import HmsSqlite

        subs_geo = HmsSqlite.get_subbasins(sqlite_path)

        params = pd.DataFrame({
            "name": ["Upper", "Local"],
            "curve_number": [75.0, 82.0],
        })

        merged = HmsSqlite.join_with_parameters(subs_geo, params)
        import geopandas as gpd
        assert isinstance(merged, gpd.GeoDataFrame)
        assert "curve_number" in merged.columns
        assert "geometry" in merged.columns
        assert len(merged) == 2

    def test_preserves_geometry(self, sqlite_path):
        import pandas as pd
        from hms_commander import HmsSqlite

        subs_geo = HmsSqlite.get_subbasins(sqlite_path)
        params = pd.DataFrame({
            "name": ["Upper"],
            "value": [10],
        })

        merged = HmsSqlite.join_with_parameters(subs_geo, params)
        assert merged.crs is not None
        assert len(merged) == len(subs_geo)  # Left join preserves all geometry rows

    def test_partial_join(self, sqlite_path):
        """Parameters for only one subbasin - other gets NaN."""
        import pandas as pd
        from hms_commander import HmsSqlite

        subs_geo = HmsSqlite.get_subbasins(sqlite_path)
        params = pd.DataFrame({
            "name": ["Upper"],
            "lag_time": [30.0],
        })

        merged = HmsSqlite.join_with_parameters(subs_geo, params)
        assert len(merged) == 2  # Both rows preserved
        # One row has value, other has NaN
        assert merged["lag_time"].notna().sum() == 1

    def test_missing_join_column(self, sqlite_path):
        import pandas as pd
        from hms_commander import HmsSqlite

        subs_geo = HmsSqlite.get_subbasins(sqlite_path)
        params = pd.DataFrame({"wrong_col": ["a"], "value": [1]})

        with pytest.raises(ValueError, match="not found"):
            HmsSqlite.join_with_parameters(subs_geo, params)


# ===========================================================================
# HmsPrj integration
# ===========================================================================


class TestHmsPrjIntegration:
    """Tests for HmsPrj SQLite discovery and CRS integration."""

    def test_sqlite_files_discovered(self, river_bend_dir):
        from hms_commander import HmsPrj

        prj = HmsPrj()
        prj.initialize(str(river_bend_dir))
        assert len(prj.sqlite_files) == 3, "Should discover 3 .sqlite files"
        assert all(f.suffix == ".sqlite" for f in prj.sqlite_files)

    def test_is_gridded_flag(self, river_bend_dir):
        from hms_commander import HmsPrj

        prj = HmsPrj()
        prj.initialize(str(river_bend_dir))
        assert prj.is_gridded is True, "river_bend should be detected as gridded"

    def test_crs_from_sqlite(self, river_bend_dir):
        from hms_commander import HmsPrj

        prj = HmsPrj()
        prj.initialize(str(river_bend_dir))
        assert prj.crs is not None, "CRS should be detected from SQLite"
        # river_bend uses EPSG:26916 (NAD83 / UTM zone 16N)
        # crs_epsg may be int (26916), string ("EPSG:26916"), or None
        assert prj.crs_epsg is not None, "EPSG should be detected for river_bend"
        assert "26916" in str(prj.crs_epsg)
        assert prj.projection_file is not None
        assert prj.projection_file.suffix == ".sqlite"


# ===========================================================================
# HmsGeo.detect_model_type
# ===========================================================================


class TestHmsGeoDetectModelType:
    """Tests for HmsGeo.detect_model_type()."""

    def test_gridded_detection(self, river_bend_dir):
        from hms_commander import HmsGeo

        model_type = HmsGeo.detect_model_type(river_bend_dir)
        assert model_type == "gridded"

    def test_lumped_detection(self, tmp_path):
        from hms_commander import HmsGeo

        model_type = HmsGeo.detect_model_type(tmp_path)
        assert model_type == "lumped"

    def test_nonexistent_dir_raises(self):
        from hms_commander import HmsGeo

        with pytest.raises(FileNotFoundError):
            HmsGeo.detect_model_type("Z:/nonexistent_dir")
