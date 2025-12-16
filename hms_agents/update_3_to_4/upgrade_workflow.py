"""
HMS Project Upgrade Workflow: 3.x to 4.x

This script automates the process of upgrading an HMS project from version 3.x
to 4.x, including running both versions and comparing results.

Usage:
    python upgrade_workflow.py <project_path> <run_name> [options]

Example:
    python upgrade_workflow.py "C:/Projects/my_hms_project" "Run 1"
    python upgrade_workflow.py "C:/Projects/my_hms_project" "Run 1" --hms33 "C:/Program Files (x86)/HEC/HEC-HMS/3.3"
"""

from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
import shutil
import sys

# Flexible import for development vs installed package
try:
    from hms_commander import HmsJython, HmsOutput, HmsDss, HmsRun
except ImportError:
    current_file = Path(__file__).resolve()
    parent_directory = current_file.parent.parent.parent
    sys.path.insert(0, str(parent_directory))
    from hms_commander import HmsJython, HmsOutput, HmsDss, HmsRun

from compare_dss_outputs import compare_hms_dss_outputs, ComparisonResult


@dataclass
class UpgradeResult:
    """Results from the upgrade workflow."""

    # Paths
    original_project: Path
    upgraded_project: Path

    # Run results
    run_33_success: bool
    run_411_success: bool
    run_33_log: str
    run_411_log: str

    # Version info
    original_version: str
    upgraded_version: str

    # DSS comparison (if available)
    comparison: Optional[ComparisonResult] = None

    # Issues encountered
    issues: list = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []


def find_hms_file(project_path: Path) -> Optional[Path]:
    """Find the .hms project file in a directory."""
    hms_files = list(project_path.glob("*.hms"))
    if not hms_files:
        return None
    return hms_files[0]


def find_run_file(project_path: Path) -> Optional[Path]:
    """Find the .run file in a directory."""
    run_files = list(project_path.glob("*.run"))
    if not run_files:
        return None
    return run_files[0]


def get_dss_output_path(project_path: Path, run_name: str) -> Optional[Path]:
    """Get the DSS output file path for a run."""
    run_file = find_run_file(project_path)
    if not run_file:
        return None

    dss_file = HmsRun.get_dss_file_direct(run_file, run_name)
    if dss_file:
        return project_path / dss_file
    return None


def run_hms_33(
    project_path: Path,
    run_name: str,
    hms_exe_path: Optional[Path] = None
) -> Tuple[bool, str, str]:
    """
    Run project in HMS 3.x.

    Returns:
        Tuple of (success, stdout, stderr)
    """
    if hms_exe_path is None:
        hms_exe_path = Path("C:/Program Files (x86)/HEC/HEC-HMS/3.3")

    if not hms_exe_path.exists():
        return False, "", f"HMS 3.x not found at {hms_exe_path}"

    # Generate Python 2 compatible script
    script = HmsJython.generate_compute_script(
        project_path=str(project_path),
        run_name=run_name,
        python2_compatible=True
    )

    # Execute
    success, stdout, stderr = HmsJython.execute_script(
        script_content=script,
        hms_exe_path=hms_exe_path,
        working_dir=str(project_path)
    )

    return success, stdout, stderr


def run_hms_411(
    project_path: Path,
    run_name: str,
    hms_exe_path: Optional[Path] = None
) -> Tuple[bool, str, str]:
    """
    Run project in HMS 4.x.

    Returns:
        Tuple of (success, stdout, stderr)
    """
    if hms_exe_path is None:
        hms_exe_path = Path("C:/Program Files/HEC/HEC-HMS/4.11")

    if not hms_exe_path.exists():
        return False, "", f"HMS 4.x not found at {hms_exe_path}"

    # Get project name from .hms file (CRITICAL for 4.x)
    hms_file = find_hms_file(project_path)
    if not hms_file:
        return False, "", f"No .hms file found in {project_path}"

    project_name = HmsOutput.get_project_name_from_hms(hms_file)

    # Generate Python 3 script with correct project name
    script = HmsJython.generate_compute_script(
        project_path=str(project_path),
        run_name=run_name,
        python2_compatible=False,
        project_name=project_name
    )

    # Execute
    success, stdout, stderr = HmsJython.execute_script(
        script_content=script,
        hms_exe_path=hms_exe_path,
        working_dir=str(project_path)
    )

    # HMS 4.x may have empty stdout - check log files
    if not stdout or len(stdout.strip()) < 50:
        try:
            result = HmsOutput.parse_project_log(project_path, project_name)
            stdout = result.stdout
        except Exception:
            pass

    return success, stdout, stderr


def upgrade_project(
    project_path: str,
    run_name: str,
    hms_33_path: Optional[str] = None,
    hms_411_path: Optional[str] = None,
    output_suffix: str = "_upgrade_4x",
    verbose: bool = True
) -> UpgradeResult:
    """
    Complete workflow to upgrade an HMS project from 3.x to 4.x.

    Args:
        project_path: Path to original HMS 3.x project
        run_name: Name of the run to execute
        hms_33_path: Path to HMS 3.x installation
        hms_411_path: Path to HMS 4.x installation
        output_suffix: Suffix for upgraded project folder
        verbose: Print progress messages

    Returns:
        UpgradeResult with all workflow results
    """
    project_path = Path(project_path)
    upgraded_path = project_path.parent / f"{project_path.name}{output_suffix}"

    issues = []

    if verbose:
        print("=" * 80)
        print("HMS PROJECT UPGRADE WORKFLOW: 3.x to 4.x")
        print("=" * 80)
        print(f"\nOriginal project: {project_path}")
        print(f"Upgraded project: {upgraded_path}")
        print(f"Run name: {run_name}")

    # Step 1: Validate original project
    if verbose:
        print("\n[Step 1] Validating original project...")

    hms_file = find_hms_file(project_path)
    if not hms_file:
        raise FileNotFoundError(f"No .hms file found in {project_path}")

    run_file = find_run_file(project_path)
    if not run_file:
        raise FileNotFoundError(f"No .run file found in {project_path}")

    # Check run exists
    runs = HmsRun.list_runs_direct(run_file)
    run_names = [r['name'] for r in runs]
    if run_name not in run_names:
        raise ValueError(f"Run '{run_name}' not found. Available runs: {run_names}")

    project_name = HmsOutput.get_project_name_from_hms(hms_file)
    if verbose:
        print(f"  Project name: {project_name}")
        print(f"  Available runs: {run_names}")

    # Step 2: Run in HMS 3.x
    if verbose:
        print("\n[Step 2] Running in HMS 3.x...")

    hms_33 = Path(hms_33_path) if hms_33_path else None
    success_33, stdout_33, stderr_33 = run_hms_33(project_path, run_name, hms_33)

    if success_33:
        result_33 = HmsOutput.parse_compute_output(stdout_33, stderr_33)
        if verbose:
            print(f"  Status: SUCCESS")
            print(f"  Warnings: {len(result_33.warnings)}")
            print(f"  Errors: {len(result_33.errors)}")
    else:
        if verbose:
            print(f"  Status: FAILED")
            print(f"  Error: {stderr_33[:200] if stderr_33 else 'Unknown'}")
        issues.append(f"HMS 3.x run failed: {stderr_33[:100]}")

    # Step 3: Create upgrade copy
    if verbose:
        print("\n[Step 3] Creating upgrade copy...")

    if upgraded_path.exists():
        shutil.rmtree(upgraded_path)
    shutil.copytree(project_path, upgraded_path)

    if verbose:
        print(f"  Created: {upgraded_path}")

    # Step 4: Run in HMS 4.x (auto-upgrade)
    if verbose:
        print("\n[Step 4] Running in HMS 4.x (auto-upgrade)...")

    hms_411 = Path(hms_411_path) if hms_411_path else None
    success_411, stdout_411, stderr_411 = run_hms_411(upgraded_path, run_name, hms_411)

    upgraded_version = "4.x"
    if success_411:
        result_411 = HmsOutput.parse_compute_output(stdout_411, stderr_411)

        # Check for version upgrade messages
        upgraded, from_ver, to_ver = HmsOutput.check_version_upgrade(stdout_411)
        if upgraded:
            upgraded_version = to_ver
            if verbose:
                print(f"  Upgraded from {from_ver} to {to_ver}")

        if verbose:
            print(f"  Status: SUCCESS")
            print(f"  Warnings: {len(result_411.warnings)}")
            print(f"  Errors: {len(result_411.errors)}")
    else:
        if verbose:
            print(f"  Status: FAILED")
            print(f"  Error: {stderr_411[:200] if stderr_411 else 'Unknown'}")
        issues.append(f"HMS 4.x run failed: {stderr_411[:100]}")

    # Step 5: Compare DSS outputs
    comparison = None
    if success_33 and success_411:
        if verbose:
            print("\n[Step 5] Comparing DSS outputs...")

        dss_33 = get_dss_output_path(project_path, run_name)
        dss_411 = get_dss_output_path(upgraded_path, run_name)

        if dss_33 and dss_33.exists() and dss_411 and dss_411.exists():
            comparison = compare_hms_dss_outputs(
                str(dss_33),
                str(dss_411),
                verbose=verbose
            )

            acceptable, comp_issues = comparison.is_acceptable()
            if not acceptable:
                issues.extend(comp_issues)
        else:
            if verbose:
                print("  Could not find DSS output files for comparison")
            issues.append("DSS output files not found for comparison")

    # Build result
    result = UpgradeResult(
        original_project=project_path,
        upgraded_project=upgraded_path,
        run_33_success=success_33,
        run_411_success=success_411,
        run_33_log=stdout_33,
        run_411_log=stdout_411,
        original_version="3.x",
        upgraded_version=upgraded_version,
        comparison=comparison,
        issues=issues
    )

    # Summary
    if verbose:
        print("\n" + "=" * 80)
        print("UPGRADE SUMMARY")
        print("=" * 80)
        print(f"\nHMS 3.x run: {'SUCCESS' if success_33 else 'FAILED'}")
        print(f"HMS 4.x run: {'SUCCESS' if success_411 else 'FAILED'}")

        if comparison and comparison.flow_compared:
            print(f"\nPeak flow difference: {comparison.peak_diff_pct:.2f}%")
            print(f"Volume difference: {comparison.volume_diff_pct:.2f}%")

        if issues:
            print(f"\nIssues ({len(issues)}):")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\nNo issues found - upgrade successful!")

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Upgrade HMS project from 3.x to 4.x")
    parser.add_argument("project_path", help="Path to HMS 3.x project")
    parser.add_argument("run_name", help="Name of the run to execute")
    parser.add_argument("--hms33", help="Path to HMS 3.x installation")
    parser.add_argument("--hms411", help="Path to HMS 4.x installation")
    parser.add_argument("--suffix", default="_upgrade_4x", help="Suffix for upgraded project folder")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")

    args = parser.parse_args()

    result = upgrade_project(
        project_path=args.project_path,
        run_name=args.run_name,
        hms_33_path=args.hms33,
        hms_411_path=args.hms411,
        output_suffix=args.suffix,
        verbose=not args.quiet
    )

    # Exit with error code if issues found
    sys.exit(1 if result.issues else 0)
