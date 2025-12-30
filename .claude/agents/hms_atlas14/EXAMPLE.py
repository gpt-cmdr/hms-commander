"""
HMS Atlas 14 Agent - Complete Workflow Example

This script demonstrates the complete workflow for updating an HEC-HMS
project from TP-40 to Atlas 14 precipitation frequency estimates.

Following the CLB Engineering LLM Forward Approach for GUI-verifiable,
non-destructive model modifications.

Usage:
    python EXAMPLE.py --project "C:/HMS_Projects/Tifton" --lat 31.4504 --lon -83.5285

Requirements:
    - HEC-HMS 4.4.1+ installed
    - hms-commander v0.4.1+
    - Python 3.10+
    - Active internet connection (for Atlas 14 API)
"""

import argparse
import logging
from pathlib import Path
from typing import Dict, List

# Import hms-commander
from hms_commander import (
    init_hms_project, hms,
    HmsBasin, HmsMet, HmsRun, HmsCmdr, HmsUtils
)

# Import Atlas 14 agent
from hms_agents.HmsAtlas14 import Atlas14Downloader, Atlas14Converter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main(
    project_path: str,
    lat: float,
    lon: float,
    template_met: str = "Design_Storms_TP40",
    storms: List[Dict] = None,
    run_models: bool = True,
    backup: bool = True
):
    """
    Execute complete Atlas 14 update workflow.

    Args:
        project_path: Path to HMS project folder
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        template_met: Name of template met model (TP-40 baseline)
        storms: List of storms to update (default: 100-year only)
        run_models: Whether to execute model runs (default True)
        backup: Whether to backup project first (default True)
    """
    project_path = Path(project_path)

    # Default storms if not specified
    if storms is None:
        storms = [
            {
                'name': '100yr Storm',
                'aep': '1%',
                'duration': 1440,   # 24 hours in minutes
                'interval': 60,     # 1-hour intervals
                'peak_pos': 50      # Peak at 50% (centered)
            }
        ]

    logger.info("=" * 80)
    logger.info("HMS Atlas 14 Update Workflow")
    logger.info("=" * 80)
    logger.info(f"Project: {project_path}")
    logger.info(f"Location: ({lat}, {lon})")
    logger.info(f"Storms to update: {len(storms)}")
    logger.info("=" * 80)

    # =========================================================================
    # STEP 1: Backup Original Project
    # =========================================================================
    if backup:
        logger.info("\n[STEP 1] Backing up original project...")
        backup_path = project_path.parent / f"{project_path.name}_Backup_TP40"

        if backup_path.exists():
            logger.warning(f"Backup already exists: {backup_path}")
        else:
            HmsUtils.copy_project(project_path, backup_path)
            logger.info(f"✓ Backup created: {backup_path}")
    else:
        logger.info("\n[STEP 1] Skipping backup (as requested)")

    # =========================================================================
    # STEP 2: Initialize Project
    # =========================================================================
    logger.info("\n[STEP 2] Initializing HMS project...")
    init_hms_project(project_path)

    # Validate project
    validation = HmsUtils.validate_project(project_path)
    if not validation['valid']:
        logger.error(f"Project validation failed: {validation['errors']}")
        return False

    logger.info(f"✓ Project initialized: {hms.project_name}")
    logger.info(f"  - Basins: {len(hms.basin_df)}")
    logger.info(f"  - Met models: {len(hms.met_df)}")
    logger.info(f"  - Runs: {len(hms.run_df)}")

    # =========================================================================
    # STEP 3: Download Atlas 14 Data
    # =========================================================================
    logger.info("\n[STEP 3] Downloading Atlas 14 data from NOAA...")
    logger.info(f"Location: {lat}°N, {lon}°W")

    downloader = Atlas14Downloader()

    try:
        atlas14_data = downloader.download_from_coordinates(
            lat=lat,
            lon=lon,
            data='depth',      # Point estimate
            units='english',   # Inches
            series='pds'       # Partial duration series
        )

        logger.info(f"✓ Downloaded Atlas 14 data")
        logger.info(f"  - Return periods: {len(atlas14_data['return_periods'])}")
        logger.info(f"  - Durations: {len(atlas14_data['durations'])}")
        logger.info(f"  - Units: {atlas14_data['units']}")

        # Display sample depths
        sample_aep = '1%'
        if sample_aep in atlas14_data['depths']:
            sample_24hr = atlas14_data['depths'][sample_aep].get('24-hr', 'N/A')
            logger.info(f"  - Sample: {sample_aep} AEP, 24-hr = {sample_24hr} inches")

    except Exception as e:
        logger.error(f"Failed to download Atlas 14 data: {e}")
        return False

    # =========================================================================
    # STEP 4: Clone Meteorologic Model
    # =========================================================================
    logger.info(f"\n[STEP 4] Cloning meteorologic model '{template_met}'...")

    new_met_name = f"{template_met.replace('TP40', 'Atlas14')}"

    # Check if already exists
    if new_met_name in hms.met_df['name'].values:
        logger.warning(f"Met model '{new_met_name}' already exists, using existing")
    else:
        try:
            HmsMet.clone_met(
                template_met=template_met,
                new_name=new_met_name,
                description=f"Atlas 14 precipitation data (NOAA, {lat}°N, {lon}°W)",
                hms_object=hms
            )
            logger.info(f"✓ Cloned met model: {template_met} → {new_met_name}")
        except Exception as e:
            logger.error(f"Failed to clone met model: {e}")
            return False

    # =========================================================================
    # STEP 5: Update Each Storm
    # =========================================================================
    logger.info(f"\n[STEP 5] Updating {len(storms)} storm(s) with Atlas 14 data...")

    converter = Atlas14Converter()
    updated_runs = []

    for i, storm in enumerate(storms, 1):
        logger.info(f"\n  [{i}/{len(storms)}] Processing: {storm['name']} ({storm['aep']} AEP)")

        # Generate Atlas 14 depths
        try:
            depths = converter.generate_depth_values(
                atlas14_data=atlas14_data,
                aep=storm['aep'],
                total_duration=storm['duration'],
                time_interval=storm['interval'],
                peak_position=storm['peak_pos']
            )

            logger.info(f"    ✓ Generated {len(depths)} cumulative depth values")
            logger.info(f"      Total depth: {depths[-1]:.2f} inches")

        except Exception as e:
            logger.error(f"    ✗ Failed to generate depths: {e}")
            continue

        # Update met model (each storm may need separate met model)
        # For simplicity, we'll update the cloned met model
        # In production, you might clone separate met models per storm
        met_path = hms.project_folder / f"{new_met_name}.met"

        try:
            result = HmsMet.update_tp40_to_atlas14(
                met_path=met_path,
                atlas14_depths=depths,
                hms_object=hms
            )

            logger.info(f"    ✓ Updated precipitation depths")
            logger.info(f"      Average change: {result['avg_change_percent']:.1f}%")

        except Exception as e:
            logger.error(f"    ✗ Failed to update depths: {e}")
            continue

        # Clone run for comparison
        baseline_run = storm['name']
        updated_run = f"{baseline_run} - Atlas14"

        # Check if run exists
        if updated_run in hms.run_df['name'].values:
            logger.warning(f"    Run '{updated_run}' already exists, skipping clone")
            updated_runs.append(updated_run)
            continue

        try:
            HmsRun.clone_run(
                source_run=baseline_run,
                new_run_name=updated_run,
                new_met=new_met_name,
                output_dss=f"results_{updated_run.replace(' ', '_').lower()}.dss",
                description=f"{storm['aep']} AEP storm with Atlas 14 precipitation",
                hms_object=hms
            )

            logger.info(f"    ✓ Cloned run: {baseline_run} → {updated_run}")
            updated_runs.append(updated_run)

        except Exception as e:
            logger.error(f"    ✗ Failed to clone run: {e}")
            continue

    logger.info(f"\n✓ Updated {len(updated_runs)} run(s)")

    # =========================================================================
    # STEP 6: Execute Baseline and Updated Runs
    # =========================================================================
    if run_models:
        logger.info("\n[STEP 6] Executing model runs...")

        for storm in storms:
            baseline_run = storm['name']
            updated_run = f"{baseline_run} - Atlas14"

            # Run baseline
            logger.info(f"\n  Running baseline: {baseline_run}")
            try:
                HmsCmdr.compute_run(baseline_run)
                logger.info(f"    ✓ Baseline complete")
            except Exception as e:
                logger.error(f"    ✗ Baseline failed: {e}")

            # Run updated
            if updated_run in updated_runs:
                logger.info(f"\n  Running updated: {updated_run}")
                try:
                    HmsCmdr.compute_run(updated_run)
                    logger.info(f"    ✓ Updated complete")
                except Exception as e:
                    logger.error(f"    ✗ Updated failed: {e}")

        # Verify DSS outputs
        logger.info("\n  Verifying DSS outputs...")
        outputs = HmsRun.verify_dss_outputs(hms_object=hms)

        for run, info in outputs.items():
            status = "✓" if info['exists'] else "✗"
            logger.info(f"    {status} {run}: {info['dss_file']}")

    else:
        logger.info("\n[STEP 6] Skipping model execution (as requested)")

    # =========================================================================
    # STEP 7: Summary and Next Steps
    # =========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("WORKFLOW COMPLETE")
    logger.info("=" * 80)

    logger.info("\nSummary:")
    logger.info(f"  - Project: {project_path}")
    logger.info(f"  - Location: ({lat}, {lon})")
    logger.info(f"  - Storms updated: {len(updated_runs)}")
    logger.info(f"  - New met model: {new_met_name}")

    logger.info("\nNext Steps for QAQC:")
    logger.info("  1. Open HEC-HMS GUI")
    logger.info("  2. Navigate to project folder")
    logger.info("  3. Compare baseline and updated runs side-by-side:")

    for storm in storms:
        baseline_run = storm['name']
        updated_run = f"{baseline_run} - Atlas14"
        logger.info(f"     - Baseline: '{baseline_run}'")
        logger.info(f"     - Updated:  '{updated_run}'")

    logger.info("  4. Verify precipitation depths in met models:")
    logger.info(f"     - Baseline: '{template_met}'")
    logger.info(f"     - Updated:  '{new_met_name}'")

    logger.info("  5. Compare DSS results:")
    for storm in storms:
        baseline_run = storm['name']
        updated_run = f"{baseline_run} - Atlas14"
        logger.info(f"     - Baseline: results_{baseline_run.replace(' ', '_').lower()}.dss")
        logger.info(f"     - Updated:  results_{updated_run.replace(' ', '_').lower()}.dss")

    logger.info("\n✓ All changes verifiable in HEC-HMS GUI (CLB Engineering approach)")
    logger.info("=" * 80)

    return True


if __name__ == "__main__":
    # Command-line interface
    parser = argparse.ArgumentParser(
        description="Update HMS project from TP-40 to Atlas 14 precipitation data"
    )

    parser.add_argument(
        '--project',
        type=str,
        required=True,
        help='Path to HMS project folder'
    )

    parser.add_argument(
        '--lat',
        type=float,
        required=True,
        help='Latitude in decimal degrees'
    )

    parser.add_argument(
        '--lon',
        type=float,
        required=True,
        help='Longitude in decimal degrees'
    )

    parser.add_argument(
        '--template-met',
        type=str,
        default='Design_Storms_TP40',
        help='Name of template met model (default: Design_Storms_TP40)'
    )

    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Skip project backup step'
    )

    parser.add_argument(
        '--no-run',
        action='store_true',
        help='Skip model execution step'
    )

    args = parser.parse_args()

    # Execute workflow
    success = main(
        project_path=args.project,
        lat=args.lat,
        lon=args.lon,
        template_met=args.template_met,
        run_models=not args.no_run,
        backup=not args.no_backup
    )

    if success:
        print("\n✓ Workflow completed successfully!")
        exit(0)
    else:
        print("\n✗ Workflow encountered errors")
        exit(1)
