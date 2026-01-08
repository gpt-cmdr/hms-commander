"""
Shared parsing utilities for HMS text files.

Consolidates file reading, encoding fallback, and block parsing
used across HmsBasin, HmsMet, HmsControl, and HmsGage.

All methods are static and designed for internal use by HMS file
operation classes.
"""
from pathlib import Path
from typing import Dict, Any, Tuple, Union, Optional
import re

from .LoggingConfig import get_logger

logger = get_logger(__name__)


class HmsFileParser:
    """
    Common parser for HMS ASCII text files (.basin, .met, .control, .gage).

    Provides static methods for file I/O and content parsing with consistent
    encoding handling and block/parameter extraction patterns.

    This class consolidates ~230 lines of duplicated parsing logic from
    HmsBasin, HmsMet, HmsControl, and HmsGage classes.
    """

    @staticmethod
    def read_file(file_path: Union[str, Path]) -> str:
        """
        Read HMS file with UTF-8 → Latin-1 encoding fallback.

        HMS files may use different encodings depending on when they were created
        and what characters they contain. This method tries UTF-8 first, then
        falls back to Latin-1 if decoding fails.

        Args:
            file_path: Path to HMS file (.basin, .met, .control, .gage, etc.)

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If file doesn't exist

        Example:
            >>> content = HmsFileParser.read_file("model.basin")
            >>> print(len(content))
            5432
        """
        file_path = Path(file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            logger.debug(f"UTF-8 decode failed for {file_path}, falling back to Latin-1")
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()

    @staticmethod
    def write_file(file_path: Union[str, Path], content: str, encoding: str = 'utf-8') -> None:
        """
        Write HMS file with specified encoding.

        Args:
            file_path: Output file path
            content: File content string
            encoding: Character encoding (default: utf-8)

        Example:
            >>> HmsFileParser.write_file("model.basin", updated_content)
        """
        file_path = Path(file_path)
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        logger.debug(f"Wrote {len(content)} characters to {file_path}")

    @staticmethod
    def parse_blocks(content: str, block_keyword: str) -> Dict[str, Dict[str, str]]:
        """
        Parse HMS file into named blocks (e.g., "Subbasin:", "Gage:", "Reach:").

        Handles patterns like:
            Subbasin: Sub1
                 Area: 100.0
                 Downstream: Junction-1
            End:

        Args:
            content: HMS file content
            block_keyword: Block type (Subbasin, Junction, Reach, Gage, etc.)

        Returns:
            Dict mapping element names to their attribute dictionaries

        Example:
            >>> blocks = HmsFileParser.parse_blocks(content, "Subbasin")
            >>> print(blocks["Sub1"]["Area"])
            '100.0'
            >>> print(blocks["Sub1"]["Downstream"])
            'Junction-1'
        """
        elements = {}
        pattern = rf'{block_keyword}:\s*(.+?)\n(.*?)End:'
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)

        for match in matches:
            name = match[0].strip()
            block = match[1]
            attrs = HmsFileParser._parse_attribute_block(block)
            elements[name] = attrs

        return elements

    @staticmethod
    def _parse_attribute_block(block: str) -> Dict[str, str]:
        """
        Parse key-value pairs from block content.

        Internal helper method for extracting parameters from the content
        between a block header and "End:" marker.

        Args:
            block: Block content string (between header and "End:")

        Returns:
            Dict of attribute name to value

        Example:
            >>> block = "     Area: 123.45\\n     Loss: SCS Curve Number\\n"
            >>> params = HmsFileParser._parse_attribute_block(block)
            >>> print(params["Area"])
            '123.45'
        """
        attrs = {}
        for line in block.splitlines():
            line = line.strip()
            # Parse key:value pairs, but skip "End:" block terminator
            if ':' in line and line != 'End:':
                key, value = line.split(':', 1)
                attrs[key.strip()] = value.strip()
        return attrs

    @staticmethod
    def parse_named_section(
        content: str,
        section_keyword: str
    ) -> Tuple[str, Dict[str, str]]:
        """
        Parse a single named section (e.g., "Meteorology:", "Control:").

        Different from parse_blocks() because these sections typically appear
        once per file and may not have explicit "End:" markers.

        Args:
            content: HMS file content
            section_keyword: Section type (e.g., "Meteorology", "Control")

        Returns:
            Tuple of (section_name, section_parameters)

        Example:
            >>> name, params = HmsFileParser.parse_named_section(content, "Control")
            >>> print(name)
            'Jan2020'
            >>> print(params["Start Date"])
            '01Jan2020'
        """
        pattern = rf'{re.escape(section_keyword)}:\s*(.+?)\n(.*?)(?=\w+:|End:|$)'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

        if not match:
            return '', {}

        section_name = match.group(1).strip()
        block_content = match.group(2)
        params = HmsFileParser._parse_attribute_block(block_content)

        return section_name, params

    @staticmethod
    def update_parameter(
        content: str,
        param_name: str,
        new_value: Union[str, int, float]
    ) -> Tuple[str, bool]:
        """
        Update a parameter value in HMS file content.

        Searches for the parameter by name and replaces its value while
        preserving the file structure and formatting.

        Args:
            content: HMS file content or block content
            param_name: Parameter name to update (case-sensitive)
            new_value: New value to set

        Returns:
            Tuple of (modified content, whether change was made)

        Example:
            >>> updated, changed = HmsFileParser.update_parameter(
            ...     content, "Initial Deficit", 1.0
            ... )
            >>> if changed:
            ...     print("Parameter updated successfully")
        """
        pattern = rf'^(\s*{re.escape(param_name)}:\s*)(.+)$'
        match = re.search(pattern, content, re.MULTILINE)

        if match:
            old_line = match.group(0)
            new_line = f"{match.group(1)}{new_value}"
            new_content = content.replace(old_line, new_line, 1)
            return new_content, True

        return content, False

    @staticmethod
    def find_block(
        content: str,
        block_keyword: str,
        block_name: str
    ) -> Tuple[Optional[re.Match], str, str, str]:
        """
        Find a specific named block in content.

        Used when you need to locate and potentially replace a specific block
        (e.g., a particular Subbasin or Gage).

        Args:
            content: HMS file content
            block_keyword: Block type (e.g., "Subbasin")
            block_name: Name of the specific block to find

        Returns:
            Tuple of (match_object, header, block_content, footer)
            Returns (None, '', '', '') if block not found

        Example:
            >>> match, header, body, footer = HmsFileParser.find_block(
            ...     content, "Subbasin", "Sub-1"
            ... )
            >>> if match:
            ...     print(f"Found block with {len(body)} characters")
        """
        pattern = rf'({re.escape(block_keyword)}:\s*{re.escape(block_name)}\s*\n)(.*?)(End:)'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

        if not match:
            return None, '', '', ''

        return match, match.group(1), match.group(2), match.group(3)

    @staticmethod
    def replace_block(
        content: str,
        match: re.Match,
        new_block_content: str
    ) -> str:
        """
        Replace a block's content while preserving header and footer.

        Use with find_block() to locate a block, modify its content,
        and replace it in the file.

        Args:
            content: Original file content
            match: Match object from find_block()
            new_block_content: New content for the block body

        Returns:
            Updated file content

        Example:
            >>> match, header, body, footer = HmsFileParser.find_block(
            ...     content, "Subbasin", "Sub-1"
            ... )
            >>> modified_body = body.replace("Area: 100", "Area: 150")
            >>> updated = HmsFileParser.replace_block(content, match, modified_body)
        """
        header = match.group(1)
        footer = match.group(3)
        new_block = header + new_block_content + footer
        return content[:match.start()] + new_block + content[match.end():]

    @staticmethod
    def to_numeric(value: str) -> Union[float, str]:
        """
        Convert string value to float if possible, otherwise return original string.

        Handles scientific notation (e.g., '1.3824636581E7') and regular decimals.
        Returns original string if conversion fails.

        Args:
            value: String value to convert

        Returns:
            Float if conversion succeeds, original string otherwise

        Example:
            >>> HmsFileParser.to_numeric("123.45")
            123.45
            >>> HmsFileParser.to_numeric("1.5E6")
            1500000.0
            >>> HmsFileParser.to_numeric("Junction-1")
            'Junction-1'
        """
        if value is None:
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            return value
