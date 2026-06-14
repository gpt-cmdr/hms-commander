"""Tests for HmsOutput compute output parsing and message extraction."""

from hms_commander.HmsOutput import ComputeResult, HmsMessage, HmsOutput


SUCCESSFUL_COMPUTE_STDOUT = """Begin HEC-HMS 4.11.0 U.S. Army Corps of Engineers
NOTE 10019: Finished opening project "SyntheticProject" in directory "C:\\HMS\\SyntheticProject" at time 01Jan2024, 00:00:00.
NOTE 15301: Began computing simulation run "Run 1" at time 01Jan2024, 00:00:00.
WARNING 42720: The basin map file was not found.
NOTE 15302: Finished computing simulation run "Run 1" at time 01Jan2024, 01:00:00.
NOTE 12573: End script "compute.py"; Exit code 0
End HEC-HMS 4.11.0 U.S. Army Corps of Engineers; Exit status = 0
"""


FAILED_COMPUTE_STDOUT = """Begin HEC-HMS 4.11.0 U.S. Army Corps of Engineers
NOTE 10019: Finished opening project "SyntheticProject" in directory "C:\\HMS\\SyntheticProject" at time 01Jan2024, 00:00:00.
NOTE 15301: Began computing simulation run "Run 1" at time 01Jan2024, 00:00:00.
WARNING 10021: Project "SyntheticProject" was updated from Version 4.10 to Version 4.11
ERROR 10000: Simulation failed because outlet flow could not be computed.
NOTE 12573: End script "compute.py"; Exit code 1
End HEC-HMS 4.11.0 U.S. Army Corps of Engineers; Exit status = 1
"""


FAILED_COMPUTE_STDERR = (
    "ERROR 10018: Project file write permission denied.\n"
)


NONZERO_EXIT_WITHOUT_ERRORS_STDOUT = """Begin HEC-HMS 4.11.0 U.S. Army Corps of Engineers
NOTE 10019: Finished opening project "SyntheticProject" in directory "C:\\HMS\\SyntheticProject" at time 01Jan2024, 00:00:00.
NOTE 15301: Began computing simulation run "Run 1" at time 01Jan2024, 00:00:00.
NOTE 15302: Finished computing simulation run "Run 1" at time 01Jan2024, 01:00:00.
NOTE 12573: End script "compute.py"; Exit code 2
End HEC-HMS 4.11.0 U.S. Army Corps of Engineers; Exit status = 2
"""


class TestParseComputeOutput:
    def test_successful_compute_output_returns_structured_result(self):
        result = HmsOutput.parse_compute_output(SUCCESSFUL_COMPUTE_STDOUT)

        assert isinstance(result, ComputeResult)
        assert result.success is True
        assert result.project_name == "SyntheticProject"
        assert result.run_name == "Run 1"
        assert result.hms_version == "4.11.0"
        assert result.exit_code == 0
        assert result.start_time is None
        assert result.end_time is None
        assert result.stdout == SUCCESSFUL_COMPUTE_STDOUT
        assert result.stderr == ""

        assert [note.code for note in result.notes] == [10019, 15301, 15302, 12573]
        assert len(result.warnings) == 1
        assert result.warnings[0].type == "WARNING"
        assert result.warnings[0].code == 42720
        assert result.warnings[0].message == "The basin map file was not found."
        assert result.warnings[0].raw_line == (
            "WARNING 42720: The basin map file was not found."
        )
        assert result.errors == []

    def test_failed_compute_output_collects_stdout_and_stderr_errors(self):
        result = HmsOutput.parse_compute_output(
            FAILED_COMPUTE_STDOUT,
            FAILED_COMPUTE_STDERR,
        )

        assert result.success is False
        assert result.exit_code == 1
        assert result.project_name == "SyntheticProject"
        assert result.run_name == "Run 1"
        assert [warning.code for warning in result.warnings] == [10021]
        assert [error.code for error in result.errors] == [10000, 10018]
        assert result.errors[0].message == (
            "Simulation failed because outlet flow could not be computed."
        )
        assert result.errors[1].raw_line == (
            "ERROR 10018: Project file write permission denied."
        )

    def test_nonzero_exit_status_without_error_lines_fails_result(self):
        result = HmsOutput.parse_compute_output(NONZERO_EXIT_WITHOUT_ERRORS_STDOUT)

        assert result.success is False
        assert result.exit_code == 2
        assert result.errors == []
        assert [note.code for note in result.notes] == [10019, 15301, 15302, 12573]


class TestMessageExtraction:
    def test_get_errors_returns_known_error_patterns(self):
        errors = HmsOutput.get_errors(
            FAILED_COMPUTE_STDOUT,
            FAILED_COMPUTE_STDERR,
        )

        assert len(errors) == 2
        assert all(isinstance(error, HmsMessage) for error in errors)
        assert [error.type for error in errors] == ["ERROR", "ERROR"]
        assert [error.code for error in errors] == [10000, 10018]

    def test_get_warnings_returns_known_warning_patterns(self):
        warnings = HmsOutput.get_warnings(FAILED_COMPUTE_STDOUT)

        assert len(warnings) == 1
        assert warnings[0].type == "WARNING"
        assert warnings[0].code == 10021
        assert warnings[0].message == (
            'Project "SyntheticProject" was updated from Version 4.10 to Version 4.11'
        )

    def test_has_fatal_errors_detects_nonzero_exit_without_error_lines(self):
        assert HmsOutput.has_fatal_errors(NONZERO_EXIT_WITHOUT_ERRORS_STDOUT) is True


class TestComputeResultDataclass:
    def test_dataclass_fields_are_available(self):
        message = HmsMessage(
            type="ERROR",
            code=10000,
            message="Unknown exception or error.",
            raw_line="ERROR 10000: Unknown exception or error.",
        )
        result = ComputeResult(
            success=False,
            run_name="Run 1",
            project_name="SyntheticProject",
            hms_version="4.11.0",
            start_time=None,
            end_time=None,
            exit_code=1,
            notes=[],
            warnings=[],
            errors=[message],
            stdout="stdout",
            stderr="stderr",
        )

        assert result.success is False
        assert result.run_name == "Run 1"
        assert result.project_name == "SyntheticProject"
        assert result.hms_version == "4.11.0"
        assert result.exit_code == 1
        assert result.notes == []
        assert result.warnings == []
        assert result.errors == [message]
        assert result.stdout == "stdout"
        assert result.stderr == "stderr"
