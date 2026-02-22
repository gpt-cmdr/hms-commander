"""Tests for HmsFileParser — the foundation all other modules depend on."""

from pathlib import Path

import pytest

from hms_commander._parsing import HmsFileParser


# ---------------------------------------------------------------------------
# read_file / write_file
# ---------------------------------------------------------------------------

class TestReadFile:
    def test_reads_basin_file(self, basin_path_33):
        content = HmsFileParser.read_file(basin_path_33)
        assert len(content) > 0
        assert "Subbasin:" in content

    def test_returns_string(self, basin_path_33):
        content = HmsFileParser.read_file(basin_path_33)
        assert isinstance(content, str)

    def test_reads_control_file(self, control_path):
        content = HmsFileParser.read_file(control_path)
        assert "Control:" in content

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            HmsFileParser.read_file(tmp_path / "nonexistent.basin")


class TestWriteFile:
    def test_write_and_read_roundtrip(self, tmp_path):
        path = tmp_path / "test.txt"
        original = "Line1\nLine2\nLine3\n"
        HmsFileParser.write_file(path, original)
        result = HmsFileParser.read_file(path)
        assert result == original

    def test_write_overwrites_existing(self, tmp_path):
        path = tmp_path / "test.txt"
        HmsFileParser.write_file(path, "first")
        HmsFileParser.write_file(path, "second")
        assert HmsFileParser.read_file(path) == "second"


# ---------------------------------------------------------------------------
# parse_blocks
# ---------------------------------------------------------------------------

class TestParseBlocks:
    def test_parses_subbasins(self, basin_content):
        blocks = HmsFileParser.parse_blocks(basin_content, "Subbasin")
        assert len(blocks) == 131

    def test_parses_reaches(self, basin_content):
        blocks = HmsFileParser.parse_blocks(basin_content, "Reach")
        assert len(blocks) == 94

    def test_subbasin_has_attributes(self, basin_content):
        blocks = HmsFileParser.parse_blocks(basin_content, "Subbasin")
        a100a = blocks["A100A"]
        assert "Area" in a100a
        assert "Downstream" in a100a

    def test_attribute_values(self, basin_content):
        blocks = HmsFileParser.parse_blocks(basin_content, "Subbasin")
        a100a = blocks["A100A"]
        assert a100a["Area"] == "3.213"
        assert a100a["Downstream"] == "A1000000_2494_J"

    def test_nonexistent_keyword_returns_empty(self, basin_content):
        blocks = HmsFileParser.parse_blocks(basin_content, "NonExistentKeyword")
        assert len(blocks) == 0


# ---------------------------------------------------------------------------
# find_all_blocks
# ---------------------------------------------------------------------------

class TestFindAllBlocks:
    def test_returns_list_of_tuples(self, basin_content):
        results = HmsFileParser.find_all_blocks(basin_content, "Subbasin")
        assert isinstance(results, list)
        assert len(results) == 131
        # Each tuple: (match, name, attrs)
        assert len(results[0]) == 3

    def test_first_subbasin_is_a100a(self, basin_content):
        results = HmsFileParser.find_all_blocks(basin_content, "Subbasin")
        _, name, _ = results[0]
        assert name == "A100A"

    def test_order_preserved(self, basin_content):
        results = HmsFileParser.find_all_blocks(basin_content, "Subbasin")
        names = [name for _, name, _ in results]
        # First few subbasins from file
        assert names[0] == "A100A"
        assert names[1] == "A100B"
        assert names[2] == "A100C"


# ---------------------------------------------------------------------------
# update_parameter
# ---------------------------------------------------------------------------

class TestUpdateParameter:
    def test_updates_existing_parameter(self):
        content = "     Area: 3.213\n     Downstream: J1\n"
        updated, changed = HmsFileParser.update_parameter(content, "Area", "5.0")
        assert changed is True
        assert "Area: 5.0" in updated

    def test_returns_false_for_nonexistent(self):
        content = "     Area: 3.213\n"
        updated, changed = HmsFileParser.update_parameter(content, "MissingParam", "99")
        assert changed is False
        assert updated == content

    def test_preserves_other_lines(self):
        content = "     Area: 3.213\n     Downstream: J1\n     LossRate: Clark\n"
        updated, _ = HmsFileParser.update_parameter(content, "Area", "5.0")
        assert "Downstream: J1" in updated
        assert "LossRate: Clark" in updated


# ---------------------------------------------------------------------------
# find_block
# ---------------------------------------------------------------------------

class TestFindBlock:
    def test_finds_named_block(self, basin_content):
        match, header, body, footer = HmsFileParser.find_block(
            basin_content, "Subbasin", "A100A"
        )
        assert match is not None
        assert "Area" in body

    def test_returns_none_for_missing(self, basin_content):
        match, _, _, _ = HmsFileParser.find_block(
            basin_content, "Subbasin", "NONEXISTENT"
        )
        assert match is None


# ---------------------------------------------------------------------------
# replace_block
# ---------------------------------------------------------------------------

class TestReplaceBlock:
    def test_replaces_block_content(self, basin_content):
        results = HmsFileParser.find_all_blocks(basin_content, "Subbasin")
        match, name, attrs = results[0]  # A100A
        new_body = "     Area: 99.0\n     Downstream: TestJunction\n"
        updated = HmsFileParser.replace_block(basin_content, match, new_body)
        assert "Area: 99.0" in updated
        # Verify the new content was inserted
        assert updated != basin_content


# ---------------------------------------------------------------------------
# to_numeric
# ---------------------------------------------------------------------------

class TestToNumeric:
    def test_float_string(self):
        assert HmsFileParser.to_numeric("3.213") == 3.213

    def test_integer_string(self):
        assert HmsFileParser.to_numeric("5") == 5.0

    def test_scientific_notation(self):
        result = HmsFileParser.to_numeric("1.37714796E7")
        assert abs(result - 1.37714796e7) < 1.0

    def test_non_numeric_passthrough(self):
        assert HmsFileParser.to_numeric("Green and Ampt") == "Green and Ampt"

    def test_none_returns_none(self):
        assert HmsFileParser.to_numeric(None) is None
