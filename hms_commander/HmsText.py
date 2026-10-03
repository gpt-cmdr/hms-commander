"""Read-only information from already-loaded HEC-HMS text sections."""
from typing import Dict, List
from ._project_registry import iter_project_blocks
from .LoggingConfig import log_call


class HmsText:
    """Parse supported text sections without project initialization or file access.

    Values retain their source spelling. This API does not interpret coordinates,
    read references, load results, infer units, or certify parameter suitability.
    Repeated parameter keys follow the existing parser's last-value behavior;
    use the dedicated APIs for series or repeated storm depth records.
    """

    SECTION_TYPES = {
        "hms": ("Project", "Basin", "Precipitation", "Meteorology", "Met", "Control", "Run", "Gage", "Paired Data"),
        "basin": ("Basin", "Subbasin", "Reach", "Junction", "Reservoir", "Source", "Sink", "Diversion"),
        "met": ("Meteorology", "Subbasin", "Precip Method Parameters"),
        "control": ("Control",),
        "run": ("Run",),
        "gage": ("Gage", "Precipitation Gage", "Discharge Gage", "Temperature Gage"),
    }

    @staticmethod
    @log_call
    def parse_sections(content: str, file_type: str) -> List[Dict[str, object]]:
        """Parse known named sections from text supplied by the caller.

        Args:
            content: Decoded HMS text; the caller owns I/O and size limits.
            file_type: Extension without a dot: hms, basin, met, control, run, gage.

        Returns:
            Ordered dictionaries with section_type, name, and parameters.
            Unknown section types are omitted. Parameters may include spatial
            attributes: consumers must select fields appropriate to their scope.

        Raises:
            ValueError: If file_type is unsupported or text contains NUL bytes.

        Example:
            >>> rows = HmsText.parse_sections(text, "control")
        """
        kind = file_type.lower().lstrip(".")
        if kind not in HmsText.SECTION_TYPES:
            raise ValueError(f"Unsupported HMS text type: {file_type}")
        if "\x00" in content:
            raise ValueError("HMS text must not contain NUL bytes")
        allowed = {name.casefold() for name in HmsText.SECTION_TYPES[kind]}
        return [
            {"section_type": section_type, "name": name, "parameters": attrs}
            for _, section_type, name, attrs in iter_project_blocks(content)
            if section_type.casefold() in allowed
        ]
