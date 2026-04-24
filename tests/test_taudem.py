"""Tests for the direct TauDEM CLI wrapper."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from hms_commander import HmsTauDEM


def _create_fake_taudem_tools(tmp_path: Path) -> Path:
    """Create fake TauDEM command wrappers for deterministic CLI tests."""
    tools_dir = tmp_path / "fake_taudem"
    tools_dir.mkdir(parents=True, exist_ok=True)

    runner = tools_dir / "fake_taudem_tool.py"
    runner.write_text(
        "\n".join(
            [
                "import os",
                "import sys",
                "from pathlib import Path",
                "",
                "tool = sys.argv[1].lower()",
                "args = sys.argv[2:]",
                "if os.environ.get('FAKE_TAUDEM_FAIL_TOOL', '').lower() == tool:",
                "    sys.stderr.write(f'{tool} forced failure\\n')",
                "    raise SystemExit(7)",
                "",
                "output_flags = {",
                "    '-fel', '-p', '-sd8', '-ad8', '-src', '-om',",
                "    '-ord', '-tree', '-coord', '-net', '-w', '-plen', '-tlen', '-gord'",
                "}",
                "for index, arg in enumerate(args[:-1]):",
                "    if arg.lower() in output_flags:",
                "        output_path = Path(args[index + 1])",
                "        output_path.parent.mkdir(parents=True, exist_ok=True)",
                "        output_path.write_text(f'{tool}:{arg}\\n', encoding='utf-8')",
                "",
                "sys.stdout.write(f'{tool} completed\\n')",
                "",
            ]
        ),
        encoding="utf-8",
    )

    mpiexec_runner = tools_dir / "fake_mpiexec.py"
    mpiexec_runner.write_text(
        "\n".join(
            [
                "import subprocess",
                "import sys",
                "",
                "args = sys.argv[1:]",
                "if len(args) >= 2 and args[0] == '-n':",
                "    args = args[2:]",
                "result = subprocess.run(args, capture_output=True, text=True, check=False)",
                "sys.stdout.write(result.stdout)",
                "sys.stderr.write(result.stderr)",
                "raise SystemExit(result.returncode)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    wrapper_template = "\r\n".join(
        [
            "@echo off",
            f"\"{sys.executable}\" \"%~dp0fake_taudem_tool.py\" %~n0 %*",
            "",
        ]
    )

    for tool in (
        "pitremove",
        "d8flowdir",
        "aread8",
        "threshold",
        "moveoutletstostrm",
        "streamnet",
        "gridnet",
    ):
        (tools_dir / f"{tool}.cmd").write_text(wrapper_template, encoding="utf-8")

    (tools_dir / "mpiexec.cmd").write_text(
        "\r\n".join(
            [
                "@echo off",
                f"\"{sys.executable}\" \"%~dp0fake_mpiexec.py\" %*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return tools_dir


def test_find_executable_and_validate_environment(tmp_path):
    tools_dir = _create_fake_taudem_tools(tmp_path)

    pitremove = HmsTauDEM.find_executable("pitremove", search_paths=[tools_dir])
    validation = HmsTauDEM.validate_environment(
        required_tools=["pitremove", "d8flowdir", "streamnet"],
        search_paths=[tools_dir],
    )

    assert pitremove is not None
    assert pitremove.name == "pitremove.cmd"
    assert validation["available"] is True
    assert validation["missing_tools"] == []
    assert validation["tools"]["streamnet"].endswith("streamnet.cmd")


def test_run_standard_delineation_creates_manifest_and_outputs(tmp_path):
    tools_dir = _create_fake_taudem_tools(tmp_path)
    workspace_root = tmp_path / "study"
    dem_path = tmp_path / "dem.tif"
    outlet_path = tmp_path / "outlet.geojson"
    dem_path.write_text("fake dem\n", encoding="utf-8")
    outlet_path.write_text('{"type":"FeatureCollection","features":[]}\n', encoding="utf-8")

    result = HmsTauDEM.run_standard_delineation(
        workspace_root=workspace_root,
        dem_path=dem_path,
        outlet_path=outlet_path,
        threshold_value=5000,
        run_name="spring_creek",
        include_gridnet=True,
        search_paths=[tools_dir],
    )

    run_root = workspace_root / "raw" / "taudem_runs" / "spring_creek"
    manifest_path = run_root / "taudem_command_manifest.json"
    report_path = run_root / "taudem_run_report.json"

    expected_outputs = [
        run_root / "fel.tif",
        run_root / "p.tif",
        run_root / "sd8.tif",
        run_root / "ad8.tif",
        run_root / "src.tif",
        run_root / "outlet_snapped.geojson",
        run_root / "ord.tif",
        run_root / "tree.dat",
        run_root / "coord.dat",
        run_root / "net.shp",
        run_root / "w.tif",
        run_root / "plen.tif",
        run_root / "tlen.tif",
        run_root / "gord.tif",
        manifest_path,
        report_path,
    ]

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert result["status"] == "completed"
    assert all(path.exists() for path in expected_outputs)
    assert [step["step"] for step in manifest["steps"]] == [
        "pitremove",
        "d8flowdir",
        "aread8",
        "threshold",
        "moveoutletstostrm",
        "streamnet",
        "gridnet",
    ]
    assert report["status"] == "completed"
    assert report["failed_step_count"] == 0
    assert (run_root / "logs" / "streamnet.stdout.log").exists()


def test_run_standard_delineation_records_failures_machine_readably(tmp_path):
    tools_dir = _create_fake_taudem_tools(tmp_path)
    workspace_root = tmp_path / "study"
    dem_path = tmp_path / "dem.tif"
    outlet_path = tmp_path / "outlet.geojson"
    dem_path.write_text("fake dem\n", encoding="utf-8")
    outlet_path.write_text('{"type":"FeatureCollection","features":[]}\n', encoding="utf-8")

    result = HmsTauDEM.run_standard_delineation(
        workspace_root=workspace_root,
        dem_path=dem_path,
        outlet_path=outlet_path,
        threshold_value=5000,
        run_name="failing_run",
        search_paths=[tools_dir],
        env={"FAKE_TAUDEM_FAIL_TOOL": "threshold"},
    )

    run_root = workspace_root / "raw" / "taudem_runs" / "failing_run"
    manifest = json.loads((run_root / "taudem_command_manifest.json").read_text(encoding="utf-8"))
    report = json.loads((run_root / "taudem_run_report.json").read_text(encoding="utf-8"))

    assert result["status"] == "failed"
    assert [step["step"] for step in manifest["steps"]] == [
        "pitremove",
        "d8flowdir",
        "aread8",
        "threshold",
    ]
    assert manifest["steps"][-1]["status"] == "failed"
    assert "threshold" in report["failed_steps"]
    assert report["status"] == "failed"
    assert not (run_root / "outlet_snapped.geojson").exists()


def test_run_standard_delineation_uses_mpiexec_when_processes_are_explicit(tmp_path):
    tools_dir = _create_fake_taudem_tools(tmp_path)
    workspace_root = tmp_path / "study"
    dem_path = tmp_path / "dem.tif"
    outlet_path = tmp_path / "outlet.geojson"
    dem_path.write_text("fake dem\n", encoding="utf-8")
    outlet_path.write_text('{"type":"FeatureCollection","features":[]}\n', encoding="utf-8")

    result = HmsTauDEM.run_standard_delineation(
        workspace_root=workspace_root,
        dem_path=dem_path,
        outlet_path=outlet_path,
        threshold_value=5000,
        run_name="spring_creek_mpi",
        search_paths=[tools_dir],
        mpi_processes=1,
    )

    manifest = json.loads(
        (workspace_root / "raw" / "taudem_runs" / "spring_creek_mpi" / "taudem_command_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert result["status"] == "completed"
    assert manifest["environment"]["tools"]["mpiexec"].endswith("mpiexec.cmd")
    assert manifest["steps"][0]["command"][0].endswith("mpiexec.cmd")
    assert manifest["steps"][0]["command"][1:3] == ["-n", "1"]
