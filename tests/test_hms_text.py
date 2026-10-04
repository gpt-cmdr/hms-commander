"""Pure text API contracts against unmodified repository HMS text fixtures."""
from pathlib import Path
import pytest
from hms_commander import HmsText

FIXTURE = Path(__file__).parent / "projects" / "2014.08_HMS" / "A1000000_upgrade_411"

@pytest.mark.parametrize("name,kind", [("A1000000.hms", "hms"), ("A100_1PCT.basin", "basin"),
                                      ("1__24HR.met", "met"), ("Control_5.control", "control"),
                                      ("A1000000.run", "run"), ("A1000000.gage", "gage")])
def test_real_text_sections(name, kind):
    file = FIXTURE / name
    before = file.read_bytes()
    result = HmsText.parse_sections(before.decode("utf-8"), kind)
    assert result
    assert all(set(row) == {"section_type", "name", "parameters"} for row in result)
    assert file.read_bytes() == before


def test_control_exact_spelling_and_no_file_access(monkeypatch):
    text = (FIXTURE / "Control_5.control").read_text()
    def denied(*args, **kwargs):
        raise AssertionError("pure parser must not open a file")
    monkeypatch.setattr("builtins.open", denied)
    result = HmsText.parse_sections(text, "control")
    assert result[0]["name"] == "Control 5"
    assert result[0]["parameters"]["Start Time"] == "24:00"
    assert result[0]["parameters"]["Time Interval"] == "5"


def test_reject_unsupported_or_binary_and_empty():
    with pytest.raises(ValueError):
        HmsText.parse_sections("", "sqlite")
    with pytest.raises(ValueError):
        HmsText.parse_sections("\x00", "control")
    assert HmsText.parse_sections("", "control") == []
    assert HmsText.parse_sections("Unknown: item\nEnd:\n", "control") == []
