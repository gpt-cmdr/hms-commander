"""
HmsOutput - HEC-HMS Compute Output Parsing and Analysis

This module provides static methods for parsing HEC-HMS compute output,
log files, and execution results to identify errors, warnings, and
execution status.

All methods are static and designed to be used without instantiation.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from .LoggingConfig import get_logger
from .Decorators import log_call

logger = get_logger(__name__)


@dataclass
class HmsMessage:
    """Represents a single HMS log/output message."""
    type: str  # NOTE, WARNING, ERROR
    code: int  # Message code (e.g., 10008, 42720)
    message: str  # Message text
    timestamp: Optional[datetime] = None
    raw_line: Optional[str] = None


@dataclass
class ComputeResult:
    """Results from an HMS compute operation."""
    success: bool
    run_name: Optional[str]
    project_name: Optional[str]
    hms_version: Optional[str]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    exit_code: int
    notes: List[HmsMessage]
    warnings: List[HmsMessage]
    errors: List[HmsMessage]
    stdout: str
    stderr: str


class HmsOutput:
    """
    Parse and analyze HEC-HMS compute output and log files.

    Provides methods for extracting messages, identifying errors,
    and assessing computation success/failure.

    All methods are static - no instantiation required.

    Example:
        >>> from hms_commander import HmsOutput
        >>> result = HmsOutput.parse_compute_output(stdout, stderr)
        >>> if not result.success:
        ...     for err in result.errors:
        ...         print(f"ERROR {err.code}: {err.message}")
    """

    # Regex patterns for parsing HMS output
    NOTE_PATTERN = re.compile(r'^NOTE\s+(\d+):\s+(.+)$', re.MULTILINE)
    WARNING_PATTERN = re.compile(r'^WARNING\s+(\d+):\s+(.+)$', re.MULTILINE)
    ERROR_PATTERN = re.compile(r'^ERROR\s+(\d+):\s+(.+)$', re.MULTILINE)

    # Banner patterns
    HMS_START_PATTERN = re.compile(r'^Begin HEC-HMS\s+([\d.]+)\s+(.+)$', re.MULTILINE)
    HMS_END_PATTERN = re.compile(r'^End HEC-HMS\s+([\d.]+)\s+.+;\s+Exit status\s*=\s*(\d+)$', re.MULTILINE)

    # Script patterns
    SCRIPT_START_PATTERN = re.compile(r'NOTE 14650:\s+Run Script:\s+"([^"]+)"')
    SCRIPT_END_PATTERN = re.compile(r'NOTE 12573:\s+End script\s+"[^"]+";\s+Exit code\s+(\d+)')

    # Project patterns
    PROJECT_OPENED_PATTERN = re.compile(
        r'NOTE 10008:\s+Finished opening project "([^"]+)" in directory "([^"]+)" at time (.+)\.'
    )

    # Compute patterns
    COMPUTE_BEGIN_PATTERN = re.compile(
        r'NOTE 10184:\s+Began computing simulation run "([^"]+)" at time (.+)\.'
    )
    COMPUTE_END_PATTERN = re.compile(
        r'NOTE 10185:\s+Finished computing simulation run "([^"]+)" at time (.+)\.'
    )

    # Common message codes
    MESSAGE_CODES = {
        # Informational - Project Operations
        10008: "Project opened (HMS 3.x)",
        10019: "Project opened (HMS 4.x)",
        10179: "Basin model opened",
        10180: "Meteorologic model opened",
        10181: "Control specifications opened",

        # Informational - Compute Operations (HMS 3.x)
        10184: "Compute begin (HMS 3.x)",
        10185: "Compute finished (HMS 3.x)",

        # Informational - Compute Operations (HMS 4.x)
        15301: "Compute begin (HMS 4.x)",
        15302: "Compute finished (HMS 4.x)",
        15312: "Compute runtime summary",

        # Informational - Script Operations
        12573: "Script ended",
        14400: "Background map file not found",
        14650: "Script started",

        # Informational - Model Validation
        20364: "No meteorologic model parameter problems",
        40049: "No basin model parameter problems",
        42413: "Unit hydrograph volume computed",

        # Warnings - Version Upgrade
        10020: "Begin updating project to new version",
        10021: "Project updated to new version",

        # Warnings - Missing Files
        42720: "Basin map file missing",

        # Errors
        10000: "Unknown exception or error",
        10018: "Project file write permission denied",
    }

    # HMS 4.x specific patterns
    PROJECT_OPENED_4X_PATTERN = re.compile(
        r'NOTE 10019:\s+Finished opening project "([^"]+)" in directory "([^"]+)" at time (.+)\.'
    )

    # HMS 4.x compute patterns
    COMPUTE_BEGIN_4X_PATTERN = re.compile(
        r'NOTE 15301:\s+Began computing simulation run "([^"]+)" at time (.+)\.'
    )
    COMPUTE_END_4X_PATTERN = re.compile(
        r'NOTE 15302:\s+Finished computing simulation run "([^"]+)" at time (.+)\.'
    )

    # Version upgrade patterns
    VERSION_UPGRADE_PATTERN = re.compile(
        r'WARNING 10021:\s+Project "([^"]+)" was updated from Version ([\d.]+) to Version ([\d.]+)'
    )

    @staticmethod
    @log_call
    def parse_compute_output(
        stdout: str,
        stderr: str = ""
    ) -> ComputeResult:
        """
        Parse HEC-HMS compute output into structured result.

        Args:
            stdout: Standard output from HMS execution
            stderr: Standard error from HMS execution

        Returns:
            ComputeResult with parsed messages and status

        Example:
            >>> result = HmsOutput.parse_compute_output(stdout, stderr)
            >>> print(f"Success: {result.success}")
            >>> print(f"Warnings: {len(result.warnings)}")
        """
        notes = []
        warnings = []
        errors = []

        # Parse NOTEs
        for match in HmsOutput.NOTE_PATTERN.finditer(stdout):
            code = int(match.group(1))
            message = match.group(2).strip()
            notes.append(HmsMessage(
                type="NOTE",
                code=code,
                message=message,
                raw_line=match.group(0)
            ))

        # Parse WARNINGs
        for match in HmsOutput.WARNING_PATTERN.finditer(stdout):
            code = int(match.group(1))
            message = match.group(2).strip()
            warnings.append(HmsMessage(
                type="WARNING",
                code=code,
                message=message,
                raw_line=match.group(0)
            ))

        # Parse ERRORs
        for match in HmsOutput.ERROR_PATTERN.finditer(stdout):
            code = int(match.group(1))
            message = match.group(2).strip()
            errors.append(HmsMessage(
                type="ERROR",
                code=code,
                message=message,
                raw_line=match.group(0)
            ))

        # Also check stderr for errors
        for match in HmsOutput.ERROR_PATTERN.finditer(stderr):
            code = int(match.group(1))
            message = match.group(2).strip()
            errors.append(HmsMessage(
                type="ERROR",
                code=code,
                message=message,
                raw_line=match.group(0)
            ))

        # Extract HMS version
        hms_version = None
        start_match = HmsOutput.HMS_START_PATTERN.search(stdout)
        if start_match:
            hms_version = start_match.group(1)

        # Extract exit code
        exit_code = -1
        end_match = HmsOutput.HMS_END_PATTERN.search(stdout)
        if end_match:
            exit_code = int(end_match.group(2))

        # Also check for script exit code
        script_end_match = HmsOutput.SCRIPT_END_PATTERN.search(stdout)
        if script_end_match and exit_code == -1:
            exit_code = int(script_end_match.group(1))

        # Extract project name (try HMS 4.x pattern first, then 3.x)
        project_name = None
        project_match = HmsOutput.PROJECT_OPENED_4X_PATTERN.search(stdout)
        if project_match:
            project_name = project_match.group(1)
        else:
            project_match = HmsOutput.PROJECT_OPENED_PATTERN.search(stdout)
            if project_match:
                project_name = project_match.group(1)

        # Extract run name (try HMS 4.x pattern first, then 3.x)
        run_name = None
        compute_match = HmsOutput.COMPUTE_BEGIN_4X_PATTERN.search(stdout)
        if compute_match:
            run_name = compute_match.group(1)
        else:
            compute_match = HmsOutput.COMPUTE_BEGIN_PATTERN.search(stdout)
            if compute_match:
                run_name = compute_match.group(1)

        # Determine success
        # Check for HMS 3.x (10185) or HMS 4.x (15302) completion notes
        computation_finished = any(
            n.code in (10185, 15302) for n in notes
        )
        # Script success if exit code is 0, or if parsing a log file (exit code unavailable = -1)
        script_success = exit_code == 0 or exit_code == -1
        no_errors = len(errors) == 0

        # Success requires: computation finished AND no errors
        # (script_success is only a factor when exit code is explicitly non-zero)
        success = computation_finished and no_errors and (exit_code != 1)

        return ComputeResult(
            success=success,
            run_name=run_name,
            project_name=project_name,
            hms_version=hms_version,
            start_time=None,  # Could parse from timestamps
            end_time=None,
            exit_code=exit_code,
            notes=notes,
            warnings=warnings,
            errors=errors,
            stdout=stdout,
            stderr=stderr
        )

    @staticmethod
    @log_call
    def parse_log_file(
        log_path: Union[str, Path]
    ) -> ComputeResult:
        """
        Parse an HMS log file (.log) into structured result.

        Args:
            log_path: Path to the log file

        Returns:
            ComputeResult with parsed messages

        Example:
            >>> result = HmsOutput.parse_log_file("Run_1.log")
            >>> for note in result.notes:
            ...     print(f"NOTE {note.code}: {note.message}")
        """
        log_path = Path(log_path)

        if not log_path.exists():
            raise FileNotFoundError(f"Log file not found: {log_path}")

        content = log_path.read_text(encoding='utf-8', errors='replace')

        return HmsOutput.parse_compute_output(content, "")

    @staticmethod
    @log_call
    def get_errors(
        stdout: str,
        stderr: str = ""
    ) -> List[HmsMessage]:
        """
        Extract only ERROR messages from compute output.

        Args:
            stdout: Standard output from HMS execution
            stderr: Standard error from HMS execution

        Returns:
            List of error messages
        """
        result = HmsOutput.parse_compute_output(stdout, stderr)
        return result.errors

    @staticmethod
    @log_call
    def get_warnings(
        stdout: str,
        stderr: str = ""
    ) -> List[HmsMessage]:
        """
        Extract only WARNING messages from compute output.

        Args:
            stdout: Standard output from HMS execution
            stderr: Standard error from HMS execution

        Returns:
            List of warning messages
        """
        result = HmsOutput.parse_compute_output(stdout, stderr)
        return result.warnings

    @staticmethod
    @log_call
    def has_fatal_errors(
        stdout: str,
        stderr: str = ""
    ) -> bool:
        """
        Check if output contains fatal errors that prevented computation.

        Args:
            stdout: Standard output from HMS execution
            stderr: Standard error from HMS execution

        Returns:
            True if fatal errors found
        """
        result = HmsOutput.parse_compute_output(stdout, stderr)

        # Check for explicit errors
        if result.errors:
            return True

        # Check for specific failure indicators
        failure_indicators = [
            "Exit status = 1",
            "Exit code 1",
            "Error opening project",
            "Error during computation",
        ]

        combined = stdout + stderr
        for indicator in failure_indicators:
            if indicator in combined:
                return True

        return False

    @staticmethod
    @log_call
    def format_summary(
        result: ComputeResult,
        include_notes: bool = False
    ) -> str:
        """
        Format compute result as human-readable summary.

        Args:
            result: ComputeResult from parse_compute_output
            include_notes: Whether to include NOTE messages

        Returns:
            Formatted summary string

        Example:
            >>> result = HmsOutput.parse_compute_output(stdout, stderr)
            >>> print(HmsOutput.format_summary(result))
        """
        lines = []
        lines.append("=" * 60)
        lines.append("HMS COMPUTE SUMMARY")
        lines.append("=" * 60)

        # Status
        status = "SUCCESS" if result.success else "FAILED"
        lines.append(f"Status: {status}")

        if result.hms_version:
            lines.append(f"HMS Version: {result.hms_version}")
        if result.project_name:
            lines.append(f"Project: {result.project_name}")
        if result.run_name:
            lines.append(f"Run: {result.run_name}")

        lines.append(f"Exit Code: {result.exit_code}")

        # Errors
        if result.errors:
            lines.append("")
            lines.append(f"ERRORS ({len(result.errors)}):")
            lines.append("-" * 40)
            for err in result.errors:
                lines.append(f"  [{err.code}] {err.message}")

        # Warnings
        if result.warnings:
            lines.append("")
            lines.append(f"WARNINGS ({len(result.warnings)}):")
            lines.append("-" * 40)
            for warn in result.warnings:
                lines.append(f"  [{warn.code}] {warn.message}")

        # Notes (optional)
        if include_notes and result.notes:
            lines.append("")
            lines.append(f"NOTES ({len(result.notes)}):")
            lines.append("-" * 40)
            for note in result.notes:
                lines.append(f"  [{note.code}] {note.message}")

        lines.append("=" * 60)

        return "\n".join(lines)

    @staticmethod
    @log_call
    def compare_runs(
        result1: ComputeResult,
        result2: ComputeResult,
        label1: str = "Run 1",
        label2: str = "Run 2"
    ) -> str:
        """
        Compare two compute results and highlight differences.

        Args:
            result1: First ComputeResult
            result2: Second ComputeResult
            label1: Label for first result
            label2: Label for second result

        Returns:
            Formatted comparison string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("HMS COMPUTE COMPARISON")
        lines.append("=" * 60)

        # Status comparison
        lines.append(f"{label1}: {'SUCCESS' if result1.success else 'FAILED'}")
        lines.append(f"{label2}: {'SUCCESS' if result2.success else 'FAILED'}")

        # Error comparison
        lines.append("")
        lines.append(f"Errors: {label1}={len(result1.errors)}, {label2}={len(result2.errors)}")
        lines.append(f"Warnings: {label1}={len(result1.warnings)}, {label2}={len(result2.warnings)}")

        # New errors in result2
        error_codes_1 = {e.code for e in result1.errors}
        error_codes_2 = {e.code for e in result2.errors}

        new_errors = error_codes_2 - error_codes_1
        if new_errors:
            lines.append("")
            lines.append(f"NEW ERRORS in {label2}:")
            for err in result2.errors:
                if err.code in new_errors:
                    lines.append(f"  [{err.code}] {err.message}")

        resolved_errors = error_codes_1 - error_codes_2
        if resolved_errors:
            lines.append("")
            lines.append(f"RESOLVED ERRORS in {label2}:")
            for err in result1.errors:
                if err.code in resolved_errors:
                    lines.append(f"  [{err.code}] {err.message}")

        # New warnings
        warn_codes_1 = {w.code for w in result1.warnings}
        warn_codes_2 = {w.code for w in result2.warnings}

        new_warnings = warn_codes_2 - warn_codes_1
        if new_warnings:
            lines.append("")
            lines.append(f"NEW WARNINGS in {label2}:")
            for warn in result2.warnings:
                if warn.code in new_warnings:
                    lines.append(f"  [{warn.code}] {warn.message}")

        lines.append("=" * 60)

        return "\n".join(lines)

    @staticmethod
    def get_message_description(code: int) -> str:
        """
        Get human-readable description for an HMS message code.

        Args:
            code: HMS message code

        Returns:
            Description string or "Unknown message code"
        """
        return HmsOutput.MESSAGE_CODES.get(code, "Unknown message code")

    @staticmethod
    @log_call
    def is_version_upgrade_error(
        result: ComputeResult
    ) -> Tuple[bool, List[str]]:
        """
        Check if errors are likely due to version upgrade issues.

        Args:
            result: ComputeResult from parse_compute_output

        Returns:
            Tuple of (is_upgrade_error, list of potential issues)

        Example:
            >>> is_upgrade, issues = HmsOutput.is_version_upgrade_error(result)
            >>> if is_upgrade:
            ...     for issue in issues:
            ...         print(f"Upgrade issue: {issue}")
        """
        issues = []

        # Common upgrade-related error patterns
        upgrade_patterns = [
            (r'DSS file.*version', "DSS file version incompatibility"),
            (r'Unknown.*method', "Unknown method - may need parameter update"),
            (r'deprecated', "Deprecated feature"),
            (r'not.*supported', "Feature not supported in this version"),
            (r'cannot.*open.*project', "Project file format incompatibility"),
            (r'unable.*load', "Unable to load component - format change"),
        ]

        combined_text = result.stdout.lower() + result.stderr.lower()
        for error in result.errors:
            combined_text += error.message.lower()

        for pattern, description in upgrade_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                issues.append(description)

        is_upgrade = len(issues) > 0

        return is_upgrade, issues

    @staticmethod
    @log_call
    def parse_project_log(
        project_path: Union[str, Path],
        project_name: Optional[str] = None
    ) -> ComputeResult:
        """
        Parse the project log file from a project directory.

        Args:
            project_path: Path to the project directory
            project_name: Project name (auto-detected if not provided)

        Returns:
            ComputeResult from the project log file

        Example:
            >>> result = HmsOutput.parse_project_log("C:/Projects/MyProject")
            >>> print(HmsOutput.format_summary(result))
        """
        project_path = Path(project_path)

        # Auto-detect project name from .hms file if not provided
        if project_name is None:
            hms_files = list(project_path.glob("*.hms"))
            if hms_files:
                project_name = hms_files[0].stem
            else:
                raise FileNotFoundError(f"No .hms file found in {project_path}")

        log_file = project_path / f"{project_name}.log"
        if not log_file.exists():
            raise FileNotFoundError(f"Project log file not found: {log_file}")

        return HmsOutput.parse_log_file(log_file)

    @staticmethod
    @log_call
    def parse_run_log(
        project_path: Union[str, Path],
        run_name: str
    ) -> ComputeResult:
        """
        Parse a specific run log file.

        Args:
            project_path: Path to the project directory
            run_name: Name of the run

        Returns:
            ComputeResult from the run log file

        Example:
            >>> result = HmsOutput.parse_run_log("C:/Projects/MyProject", "Run 1")
            >>> if result.success:
            ...     print("Run completed successfully")
        """
        project_path = Path(project_path)

        # Try common log file naming patterns
        log_patterns = [
            f"{run_name.replace(' ', '_')}.log",
            f"{run_name}.log",
            f"Run_{run_name.split()[-1]}.log" if run_name.startswith("Run ") else None,
        ]

        for pattern in log_patterns:
            if pattern:
                log_file = project_path / pattern
                if log_file.exists():
                    return HmsOutput.parse_log_file(log_file)

        raise FileNotFoundError(f"Run log file not found for '{run_name}' in {project_path}")

    @staticmethod
    @log_call
    def check_version_upgrade(
        log_content: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if a version upgrade occurred during project open.

        Args:
            log_content: Content of the project log file

        Returns:
            Tuple of (upgrade_occurred, from_version, to_version)

        Example:
            >>> upgraded, from_ver, to_ver = HmsOutput.check_version_upgrade(log)
            >>> if upgraded:
            ...     print(f"Project upgraded from {from_ver} to {to_ver}")
        """
        match = HmsOutput.VERSION_UPGRADE_PATTERN.search(log_content)
        if match:
            return True, match.group(2), match.group(3)
        return False, None, None

    @staticmethod
    def get_project_name_from_hms(
        hms_file_path: Union[str, Path]
    ) -> str:
        """
        Extract the project name from an .hms file.

        The project name is on the first line: "Project: <name>"

        Args:
            hms_file_path: Path to the .hms file

        Returns:
            Project name string

        Example:
            >>> name = HmsOutput.get_project_name_from_hms("C:/Projects/tifton/tifton.hms")
            >>> print(name)  # "tifton"
        """
        hms_file_path = Path(hms_file_path)

        if not hms_file_path.exists():
            raise FileNotFoundError(f".hms file not found: {hms_file_path}")

        content = hms_file_path.read_text(encoding='utf-8', errors='replace')

        # Look for "Project: <name>" pattern
        match = re.search(r'^Project:\s*(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()

        raise ValueError(f"Could not find project name in {hms_file_path}")
