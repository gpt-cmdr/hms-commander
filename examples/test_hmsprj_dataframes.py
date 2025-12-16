"""
Test script for HmsPrj dataframe enhancements.

Tests the enhanced HmsPrj implementation across multiple HMS example projects.
"""

import sys
from pathlib import Path

# Add parent directory to path for development
current_file = Path(__file__).resolve()
parent_directory = current_file.parent.parent
sys.path.insert(0, str(parent_directory))

from hms_commander import init_hms_project, HmsPrj

# Test projects - all available HMS example projects
TEST_PROJECTS = [
    # HMS 4.13 projects (4 unique projects)
    "hms413_test/castro/castro",
    "hms413_test/river_bend/river_bend",
    "hms413_test/tenk/tenk",
    "hms413_test/tifton/tifton",
    # Multi-version tifton projects (test version compatibility)
    "multi_version_test/hms_4_0/tifton",
    "multi_version_test/hms_4_4_1/tifton",
    "multi_version_test/hms_4_6/tifton",
    "multi_version_test/hms_4_8/tifton",
    "multi_version_test/hms_4_13/tifton",
]

def test_project(project_path: Path) -> dict:
    """Test a single HMS project and return summary."""
    print(f"\n{'='*80}")
    print(f"Testing: {project_path.name}")
    print(f"{'='*80}")

    try:
        prj = HmsPrj()
        prj.initialize(project_path)

        result = {
            'name': prj.project_name,
            'version': prj.hms_version,
            'status': 'OK',
            'error': None,
            'hms_df_rows': len(prj.hms_df),
            'basin_df_rows': len(prj.basin_df),
            'met_df_rows': len(prj.met_df),
            'control_df_rows': len(prj.control_df),
            'run_df_rows': len(prj.run_df),
            'gage_df_rows': len(prj.gage_df),
            'pdata_df_rows': len(prj.pdata_df),
            'total_area': prj.total_area,
            'dss_files_count': len(prj.dss_files),
        }

        # Print dataframe summaries
        print(f"\n{prj}")

        print(f"\n--- hms_df ({len(prj.hms_df)} rows) ---")
        if not prj.hms_df.empty:
            print(prj.hms_df.to_string())

        print(f"\n--- basin_df ({len(prj.basin_df)} rows) ---")
        if not prj.basin_df.empty:
            cols_to_show = ['name', 'num_subbasins', 'num_reaches', 'num_junctions',
                          'total_area', 'loss_methods', 'transform_methods']
            available_cols = [c for c in cols_to_show if c in prj.basin_df.columns]
            print(prj.basin_df[available_cols].to_string())

        print(f"\n--- met_df ({len(prj.met_df)} rows) ---")
        if not prj.met_df.empty:
            cols_to_show = ['name', 'precip_method', 'et_method', 'snowmelt_method']
            available_cols = [c for c in cols_to_show if c in prj.met_df.columns]
            print(prj.met_df[available_cols].to_string())

        print(f"\n--- control_df ({len(prj.control_df)} rows) ---")
        if not prj.control_df.empty:
            cols_to_show = ['name', 'start_date', 'end_date', 'time_interval', 'duration_hours']
            available_cols = [c for c in cols_to_show if c in prj.control_df.columns]
            print(prj.control_df[available_cols].to_string())

        print(f"\n--- run_df ({len(prj.run_df)} rows) ---")
        if not prj.run_df.empty:
            cols_to_show = ['name', 'basin_model', 'met_model', 'control_spec', 'dss_file']
            available_cols = [c for c in cols_to_show if c in prj.run_df.columns]
            print(prj.run_df[available_cols].to_string())

        print(f"\n--- gage_df ({len(prj.gage_df)} rows) ---")
        if not prj.gage_df.empty:
            cols_to_show = ['name', 'gage_type', 'dss_file', 'has_dss_reference']
            available_cols = [c for c in cols_to_show if c in prj.gage_df.columns]
            print(prj.gage_df[available_cols].to_string())

        print(f"\n--- pdata_df ({len(prj.pdata_df)} rows) ---")
        if not prj.pdata_df.empty:
            cols_to_show = ['name', 'table_type', 'x_units', 'y_units']
            available_cols = [c for c in cols_to_show if c in prj.pdata_df.columns]
            print(prj.pdata_df[available_cols].to_string())

        # Print computed properties
        print(f"\n--- Computed Properties ---")
        print(f"Total area: {prj.total_area:.2f}")
        print(f"DSS files: {len(prj.dss_files)}")
        print(f"Available methods: {prj.available_methods}")

        return result

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            'name': project_path.name,
            'version': 'N/A',
            'status': 'FAILED',
            'error': str(e),
            'hms_df_rows': 0,
            'basin_df_rows': 0,
            'met_df_rows': 0,
            'control_df_rows': 0,
            'run_df_rows': 0,
            'gage_df_rows': 0,
            'pdata_df_rows': 0,
            'total_area': 0,
            'dss_files_count': 0,
        }


def main():
    """Test all example projects."""
    print("="*80)
    print("HmsPrj DataFrame Enhancement Test")
    print("="*80)

    examples_dir = Path(__file__).parent

    results = []
    for project_rel in TEST_PROJECTS:
        project_path = examples_dir / project_rel
        if project_path.exists():
            result = test_project(project_path)
            results.append(result)
        else:
            print(f"\nSkipping {project_rel} - not found")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    import pandas as pd
    summary_df = pd.DataFrame(results)
    print(summary_df[['name', 'version', 'status', 'basin_df_rows', 'run_df_rows',
                       'gage_df_rows', 'total_area']].to_string())

    # Check for failures
    failures = [r for r in results if r['status'] == 'FAILED']
    if failures:
        print(f"\n{len(failures)} project(s) failed!")
        for f in failures:
            print(f"  - {f['name']}: {f['error']}")
        return 1
    else:
        print(f"\nAll {len(results)} projects passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
