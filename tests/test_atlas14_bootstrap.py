"""Integration coverage for TauDEM Atlas 14 bootstrap workflows."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from hms_commander import HmsBasinBuilder, HmsCmdr, HmsJython, HmsPrj


@pytest.mark.requires_gis
@pytest.mark.local_hms
def test_bootstrapped_taudem_atlas14_project_computes_headlessly(
    spring_creek_taudem_fixture_root,
    river_bend_example_dir,
    tmp_path,
):
    hms_exe = HmsJython.find_hms_executable(version="4.13")
    if hms_exe is None:
        pytest.skip("Local HMS 4.13 installation not available")

    spec = HmsBasinBuilder.build_taudem_hms_spec(spring_creek_taudem_fixture_root)
    output_dir = tmp_path / "spring_creek_atlas14_compute"
    depth_table = pd.DataFrame(
        [
            {"duration_label": "5-min", "duration_minutes": 5, 100: 0.861},
            {"duration_label": "15-min", "duration_minutes": 15, 100: 1.61},
            {"duration_label": "30-min", "duration_minutes": 30, 100: 2.32},
            {"duration_label": "60-min", "duration_minutes": 60, 100: 3.11},
            {"duration_label": "2-hr", "duration_minutes": 120, 100: 3.78},
            {"duration_label": "3-hr", "duration_minutes": 180, 100: 4.10},
            {"duration_label": "6-hr", "duration_minutes": 360, 100: 4.81},
            {"duration_label": "24-hr", "duration_minutes": 1440, 100: 6.15},
        ]
    )

    HmsBasinBuilder.bootstrap_taudem_atlas14_project(
        spec=spec,
        template_project_dir=river_bend_example_dir,
        output_dir=output_dir,
        basin_name="Spring Creek TauDEM Sink",
        met_name="Spring Creek Atlas14 100YR",
        control_name="Spring Creek Atlas14 Control",
        run_name="Spring Creek Atlas14 Run",
        atlas14_depth_table=depth_table,
        atlas14_latitude=39.815328,
        atlas14_longitude=-89.698713,
    )

    project = HmsPrj().initialize(output_dir, hms_exe_path=hms_exe)
    success = HmsCmdr.compute_run("Spring Creek Atlas14 Run", hms_object=project)

    assert success is True
    assert (output_dir / "Spring_Creek_Atlas14_Run.dss").exists()
    assert (output_dir / "Spring_Creek_Atlas14_Run.log").exists()
    assert (output_dir / "Spring_Creek_Atlas14_100YR.met").exists()
    assert (output_dir / "Spring_Creek_Atlas14_Control.control").exists()
