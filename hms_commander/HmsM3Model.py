"""
HmsM3Model - Manage HCFCD M3 Model HMS projects

This module provides access to HEC-HMS projects within the Harris County Flood
Control District (HCFCD) M3 Models - Current FEMA effective H&H models.

M3 Models contain both HEC-RAS (hydraulic) and HEC-HMS (hydrologic) models.
This class focuses on extracting and managing the HMS portion.

Key Features:
- List available HMS projects across all 22 M3 model watersheds
- Extract specific HMS projects for use with hms-commander
- Query by model ID, unit ID, or channel name
- Integrates with M3Model from ras-commander (if available)

Usage:
    from hms_commander import HmsM3Model

    # List all HMS projects
    projects = HmsM3Model.list_projects()

    # Extract a specific project
    path = HmsM3Model.extract_project('D', 'D100-00-00')

    # Find project by channel name
    model_id, unit_id = HmsM3Model.get_project_by_channel('BRAYS BAYOU')

Note:
    All M3 HMS projects use HMS 3.x format, which requires:
    - python2_compatible=True for Jython script generation
    - HmsJython compatibility for execution

See Also:
    - M3Model (ras-commander): For HEC-RAS project access
    - HmsExamples: For HMS installation example projects
"""

import os
import requests
import zipfile
import pandas as pd
from pathlib import Path
import shutil
from typing import Union, List, Dict, Optional, Tuple
from datetime import datetime
import logging
from tqdm import tqdm
import csv
import io

from .LoggingConfig import get_logger, log_call

logger = get_logger(__name__)


class HmsM3Model:
    """
    Manage HEC-HMS projects from HCFCD M3 Models.

    M3 Models are Harris County Flood Control District's FEMA effective H&H
    models for major bayous and watersheds in the Houston, Texas region.

    This class provides HMS-specific access to these models, complementing
    the M3Model class in ras-commander which handles the RAS portion.

    All methods are class methods - no instantiation required.

    Example:
        # List available HMS projects
        projects = HmsM3Model.list_projects()

        # Get projects for Brays Bayou (Model D)
        brays = HmsM3Model.list_projects(model_id='D')

        # Extract for use with hms-commander
        path = HmsM3Model.extract_project('D', 'D100-00-00')
        hms = init_hms_project(path)
    """

    # Base URL for M3 Model downloads
    base_url = 'https://files.m3models.org/modellibrary/'

    # Base directory for model storage
    base_dir = Path.cwd()
    models_dir = base_dir / 'm3_hms_projects'

    # Model metadata - mirrors M3Model from ras-commander
    MODELS = {
        'A': {
            'name': 'Clear Creek',
            'short_name': 'Clear',
            'effective_date': '2022-05-05',
            'size_gb': 0.03,
            'primary_channels': ['CLEAR CREEK']
        },
        'B': {
            'name': 'Armand Bayou',
            'short_name': 'Armand',
            'effective_date': '2022-05-05',
            'size_gb': 0.04,
            'primary_channels': ['ARMAND BAYOU']
        },
        'C': {
            'name': 'Sims Bayou',
            'short_name': 'Sims',
            'effective_date': '2022-05-05',
            'size_gb': 0.01,
            'primary_channels': ['SIMS BAYOU']
        },
        'D': {
            'name': 'Brays Bayou',
            'short_name': 'Brays',
            'effective_date': '2022-05-05',
            'size_gb': 0.03,
            'primary_channels': ['BRAYS BAYOU']
        },
        'E': {
            'name': 'White Oak Bayou',
            'short_name': 'WhiteOak',
            'effective_date': '2023-01-30',
            'size_gb': 0.02,
            'primary_channels': ['WHITE OAK BAYOU']
        },
        'F': {
            'name': 'San Jacinto/Galveston Bay',
            'short_name': 'GalvBay',
            'effective_date': '2022-05-05',
            'size_gb': 0.01,
            'primary_channels': ['BAYPORT CHANNEL', 'SHIP CHANNEL']
        },
        'G': {
            'name': 'San Jacinto River',
            'short_name': 'SanJac',
            'effective_date': '2022-05-05',
            'size_gb': 0.09,
            'primary_channels': ['SAN JACINTO RIVER', 'EAST FORK SAN JACINTO RIVER']
        },
        'H': {
            'name': 'Hunting Bayou',
            'short_name': 'Hunting',
            'effective_date': '2022-05-05',
            'size_gb': 0.01,
            'primary_channels': ['HUNTING BAYOU']
        },
        'I': {
            'name': 'Vince Bayou',
            'short_name': 'Vince',
            'effective_date': '2022-05-05',
            'size_gb': 0.01,
            'primary_channels': ['VINCE BAYOU', 'LITTLE VINCE BAYOU']
        },
        'J': {
            'name': 'Spring Creek',
            'short_name': 'Spring',
            'effective_date': '2022-05-05',
            'size_gb': 0.06,
            'primary_channels': ['SPRING CREEK', 'SPRING BRANCH']
        },
        'K': {
            'name': 'Cypress Creek',
            'short_name': 'Cypress',
            'effective_date': '2022-05-05',
            'size_gb': 0.04,
            'primary_channels': ['CYPRESS CREEK']
        },
        'L': {
            'name': 'Little Cypress Creek',
            'short_name': 'LttlCyp',
            'effective_date': '2022-05-05',
            'size_gb': 0.03,
            'primary_channels': ['LITTLE CYPRESS CREEK']
        },
        'M': {
            'name': 'Willow Creek',
            'short_name': 'Willow',
            'effective_date': '2023-01-30',
            'size_gb': 0.05,
            'primary_channels': ['WILLOW CREEK', 'WILLOW WATER HOLE']
        },
        'N': {
            'name': 'Carpenters Bayou',
            'short_name': 'Carpenters',
            'effective_date': '2022-05-05',
            'size_gb': 0.01,
            'primary_channels': ['CARPENTERS BAYOU']
        },
        'O': {
            'name': 'Spring Gully and Goose Creek',
            'short_name': 'SprgGully',
            'effective_date': '2022-05-05',
            'size_gb': 0.01,
            'primary_channels': ['SPRING GULLY', 'GOOSE CREEK', 'E. FORK GOOSE CREEK', 'W. FORK GOOSE CREEK']
        },
        'P': {
            'name': 'Greens Bayou',
            'short_name': 'Greens',
            'effective_date': '2024-03-04',
            'size_gb': 0.02,
            'primary_channels': ['GREENS BAYOU', 'HALLS BAYOU', 'GARNERS BAYOU']
        },
        'Q': {
            'name': 'Cedar Bayou',
            'short_name': 'Cedar',
            'effective_date': '2022-05-05',
            'size_gb': 0.02,
            'primary_channels': ['CEDAR BAYOU', 'LITTLE CEDAR BAYOU']
        },
        'R': {
            'name': 'Jackson Bayou',
            'short_name': 'Jackson',
            'effective_date': '2022-05-05',
            'size_gb': 0.01,
            'primary_channels': ['JACKSON BAYOU']
        },
        'S': {
            'name': 'Luce Bayou',
            'short_name': 'Luce',
            'effective_date': '2022-05-05',
            'size_gb': 0.01,
            'primary_channels': ['LUCE BAYOU']
        },
        'T': {
            'name': 'Barker',
            'short_name': 'Barker',
            'effective_date': '2022-05-05',
            'size_gb': 0.01,
            'primary_channels': ['BARKER DITCH']
        },
        'U': {
            'name': 'Addicks',
            'short_name': 'Addicks',
            'effective_date': '2022-05-05',
            'size_gb': 0.08,
            'primary_channels': []  # Reservoir, not a specific channel
        },
        'W': {
            'name': 'Buffalo Bayou',
            'short_name': 'Buffalo',
            'effective_date': '2022-05-05',
            'size_gb': 0.03,
            'primary_channels': ['BUFFALO BAYOU', 'UPPER BUFFALO BAYOU/CANE']
        }
    }

    # HMS Project catalog - embedded for standalone operation
    # Can also be loaded from CSV file
    HMS_PROJECTS = None  # Loaded on first access
    _catalog_df = None

    @classmethod
    def _load_catalog(cls) -> pd.DataFrame:
        """Load the HMS project catalog from embedded CSV data."""
        if cls._catalog_df is not None:
            return cls._catalog_df

        # Try to load from package data file first
        try:
            import importlib.resources as pkg_resources
            try:
                # Python 3.9+
                files = pkg_resources.files('hms_commander.data')
                csv_path = files.joinpath('m3_hms_catalog.csv')
                with pkg_resources.as_file(csv_path) as path:
                    cls._catalog_df = pd.read_csv(path)
                    logger.debug(f"Loaded catalog from package: {len(cls._catalog_df)} projects")
                    return cls._catalog_df
            except (TypeError, AttributeError):
                # Python 3.8
                with pkg_resources.open_text('hms_commander.data', 'm3_hms_catalog.csv') as f:
                    cls._catalog_df = pd.read_csv(f)
                    logger.debug(f"Loaded catalog from package: {len(cls._catalog_df)} projects")
                    return cls._catalog_df
        except Exception as e:
            logger.debug(f"Could not load from package resources: {e}")

        # Fallback: try relative path
        try:
            catalog_path = Path(__file__).parent / 'data' / 'm3_hms_catalog.csv'
            if catalog_path.exists():
                cls._catalog_df = pd.read_csv(catalog_path)
                logger.debug(f"Loaded catalog from file: {len(cls._catalog_df)} projects")
                return cls._catalog_df
        except Exception as e:
            logger.debug(f"Could not load from file: {e}")

        # Ultimate fallback: embedded data
        logger.warning("Using embedded catalog data (may be outdated)")
        cls._catalog_df = cls._get_embedded_catalog()
        return cls._catalog_df

    @classmethod
    def _get_embedded_catalog(cls) -> pd.DataFrame:
        """Return embedded catalog data as DataFrame."""
        # Minimal embedded catalog for fallback
        data = [
            {'model_id': 'A', 'model_name': 'Clear Creek', 'unit_id': 'A100-00-00',
             'hms_file': 'A1000000.hms', 'hms_version': '3.3', 'relative_path': 'A/HEC-HMS/A_A100-00-00'},
            {'model_id': 'D', 'model_name': 'Brays Bayou', 'unit_id': 'D100-00-00',
             'hms_file': 'D100_00_00.hms', 'hms_version': '3.3', 'relative_path': 'D/HEC-HMS/D_D100-00-00/D_D100-00-00'},
            {'model_id': 'W', 'model_name': 'Buffalo Bayou', 'unit_id': 'W100-00-00',
             'hms_file': 'W100_00_00.hms', 'hms_version': '3.3', 'relative_path': 'W/HEC-HMS/W100_00_00/W100_00_00'},
        ]
        return pd.DataFrame(data)

    @classmethod
    @log_call
    def list_models(cls, as_dataframe: bool = True) -> Union[pd.DataFrame, List[Dict]]:
        """
        List all available M3 Models that contain HMS projects.

        Args:
            as_dataframe: If True, returns DataFrame. If False, returns list of dicts.

        Returns:
            DataFrame or list with model information including:
            - model_id: Single letter identifier (A-W)
            - name: Watershed/bayou name
            - hms_project_count: Number of HMS projects in model
            - primary_channels: Main channels in watershed

        Example:
            >>> models = HmsM3Model.list_models()
            >>> print(models[['model_id', 'name', 'hms_project_count']])
        """
        catalog = cls._load_catalog()

        # Count projects per model
        project_counts = catalog.groupby('model_id').size().to_dict()

        models_list = []
        for model_id, info in cls.MODELS.items():
            count = project_counts.get(model_id, 0)
            if count > 0:  # Only include models with HMS projects
                model_dict = {
                    'model_id': model_id,
                    'name': info['name'],
                    'hms_project_count': count,
                    'effective_date': info['effective_date'],
                    'size_gb': info['size_gb'],
                    'primary_channels': ', '.join(info['primary_channels'])
                }
                models_list.append(model_dict)

        if as_dataframe:
            df = pd.DataFrame(models_list)
            logger.info(f"Listed {len(df)} M3 Models with HMS projects")
            return df
        else:
            logger.info(f"Listed {len(models_list)} M3 Models with HMS projects")
            return models_list

    @classmethod
    @log_call
    def list_projects(
        cls,
        model_id: Optional[str] = None,
        as_dataframe: bool = True
    ) -> Union[pd.DataFrame, List[Dict]]:
        """
        List available HMS projects from M3 Models.

        Args:
            model_id: Filter by model letter (e.g., 'D' for Brays Bayou).
                     If None, returns all projects.
            as_dataframe: If True, returns DataFrame. If False, returns list of dicts.

        Returns:
            DataFrame or list with HMS project information including:
            - model_id: Model letter
            - model_name: Watershed name
            - unit_id: HCFCD unit number
            - hms_file: HMS project filename
            - hms_version: HMS version (3.3 or 3.4)
            - design_storms: Available storm frequencies
            - loss_method: Hydrologic loss method
            - transform_method: Unit hydrograph method

        Example:
            >>> # All projects
            >>> all_projects = HmsM3Model.list_projects()
            >>>
            >>> # Projects for Brays Bayou only
            >>> brays = HmsM3Model.list_projects(model_id='D')
        """
        catalog = cls._load_catalog()

        if model_id is not None:
            model_id = model_id.upper()
            if model_id not in cls.MODELS:
                available = ', '.join(sorted(cls.MODELS.keys()))
                raise ValueError(f"Model '{model_id}' not found. Available: {available}")
            catalog = catalog[catalog['model_id'] == model_id]

        if as_dataframe:
            logger.info(f"Listed {len(catalog)} HMS projects")
            return catalog.copy()
        else:
            result = catalog.to_dict('records')
            logger.info(f"Listed {len(result)} HMS projects")
            return result

    @classmethod
    @log_call
    def get_model_info(cls, model_id: str) -> Dict:
        """
        Get detailed information about an M3 Model.

        Args:
            model_id: Single letter model identifier (e.g., 'D')

        Returns:
            Dictionary containing:
            - name: Watershed name
            - effective_date: FEMA effective date
            - size_gb: Download size
            - primary_channels: List of main channels
            - hms_projects: List of HMS project unit IDs
            - download_url: URL for model download

        Example:
            >>> info = HmsM3Model.get_model_info('D')
            >>> print(f"Model: {info['name']}")
            >>> print(f"HMS Projects: {info['hms_projects']}")
        """
        model_id = model_id.upper()

        if model_id not in cls.MODELS:
            available = ', '.join(sorted(cls.MODELS.keys()))
            raise ValueError(f"Model '{model_id}' not found. Available: {available}")

        info = cls.MODELS[model_id].copy()
        info['model_id'] = model_id
        info['download_url'] = cls._get_download_url(model_id)
        info['filename'] = cls._get_filename(model_id)

        # Add HMS project list
        catalog = cls._load_catalog()
        model_projects = catalog[catalog['model_id'] == model_id]
        info['hms_projects'] = model_projects['unit_id'].tolist()
        info['hms_project_count'] = len(model_projects)

        logger.info(f"Retrieved info for model '{model_id}': {info['name']}")
        return info

    @classmethod
    @log_call
    def get_project_info(cls, model_id: str, unit_id: str) -> Dict:
        """
        Get detailed information about a specific HMS project.

        Args:
            model_id: Model letter (e.g., 'D')
            unit_id: HCFCD unit number (e.g., 'D100-00-00')

        Returns:
            Dictionary with project metadata from catalog

        Example:
            >>> info = HmsM3Model.get_project_info('D', 'D100-00-00')
            >>> print(f"HMS Version: {info['hms_version']}")
            >>> print(f"Loss Method: {info['loss_method']}")
        """
        model_id = model_id.upper()
        catalog = cls._load_catalog()

        # Find matching project
        mask = (catalog['model_id'] == model_id) & (catalog['unit_id'] == unit_id)
        matches = catalog[mask]

        if len(matches) == 0:
            available = catalog[catalog['model_id'] == model_id]['unit_id'].tolist()
            raise ValueError(
                f"HMS project '{unit_id}' not found in model '{model_id}'. "
                f"Available: {', '.join(available)}"
            )

        info = matches.iloc[0].to_dict()
        logger.info(f"Retrieved info for project '{unit_id}'")
        return info

    @classmethod
    @log_call
    def get_project_by_channel(cls, channel_name: str) -> Optional[Tuple[str, str]]:
        """
        Find M3 Model and HMS project for a channel name.

        Args:
            channel_name: Name of channel (e.g., 'BRAYS BAYOU')

        Returns:
            Tuple of (model_id, unit_id) if found, None otherwise

        Example:
            >>> result = HmsM3Model.get_project_by_channel('BRAYS BAYOU')
            >>> if result:
            ...     model_id, unit_id = result
            ...     path = HmsM3Model.extract_project(model_id, unit_id)
        """
        channel_upper = channel_name.upper()

        for model_id, info in cls.MODELS.items():
            for primary_channel in info['primary_channels']:
                if channel_upper == primary_channel.upper():
                    # Found model, get first HMS project
                    catalog = cls._load_catalog()
                    model_projects = catalog[catalog['model_id'] == model_id]
                    if len(model_projects) > 0:
                        unit_id = model_projects.iloc[0]['unit_id']
                        logger.info(f"Channel '{channel_name}' -> Model {model_id}, Unit {unit_id}")
                        return (model_id, unit_id)

        logger.warning(f"No HMS project found for channel '{channel_name}'")
        return None

    @classmethod
    def _get_filename(cls, model_id: str) -> str:
        """Generate the zip filename for a model."""
        info = cls.MODELS[model_id.upper()]
        return f"{model_id.upper()}_{info['short_name']}_FEMA_Effective.zip"

    @classmethod
    def _get_download_url(cls, model_id: str) -> str:
        """Generate the full download URL for a model."""
        info = cls.MODELS[model_id.upper()]
        filename = cls._get_filename(model_id)
        effective_date = info['effective_date'] + ' 05:00'
        return f"{cls.base_url}{filename}?effectivedate={effective_date.replace(' ', '%20')}"

    @classmethod
    @log_call
    def extract_project(
        cls,
        model_id: str,
        unit_id: str,
        output_path: Optional[Union[str, Path]] = None,
        overwrite: bool = False
    ) -> Path:
        """
        Download and extract a specific HMS project from an M3 Model.

        This downloads the full M3 model zip, then extracts only the
        HEC-HMS folder for the specified unit.

        Args:
            model_id: Model letter (e.g., 'D' for Brays Bayou)
            unit_id: HCFCD unit number (e.g., 'D100-00-00')
            output_path: Where to extract. Default: ./m3_hms_projects/
            overwrite: If True, overwrite existing extraction

        Returns:
            Path to extracted HMS project folder

        Example:
            >>> path = HmsM3Model.extract_project('D', 'D100-00-00')
            >>> hms = init_hms_project(path)
            >>> HmsCmdr.compute_run("1PCT")

        Note:
            These are HMS 3.x projects. Use python2_compatible=True
            for Jython script generation.
        """
        model_id = model_id.upper()

        # Validate inputs
        project_info = cls.get_project_info(model_id, unit_id)
        relative_path = project_info['relative_path']

        # Determine output directory
        if output_path is None:
            base_output = cls.models_dir
        else:
            base_output = Path(output_path)
            if not base_output.is_absolute():
                base_output = Path.cwd() / base_output

        base_output.mkdir(parents=True, exist_ok=True)

        # Project destination
        project_dest = base_output / model_id / unit_id

        logger.info("----- HmsM3Model Extracting Project -----")
        logger.info(f"Model: {model_id} - {cls.MODELS[model_id]['name']}")
        logger.info(f"Unit: {unit_id}")

        # Check if already extracted
        if project_dest.exists():
            if not overwrite:
                logger.info(f"Project already exists at {project_dest}")
                logger.info("Use overwrite=True to re-download")
                return project_dest
            else:
                logger.info(f"Removing existing project...")
                shutil.rmtree(project_dest)

        # Download the full model zip
        zip_path = base_output / cls._get_filename(model_id)
        url = cls._get_download_url(model_id)

        logger.info(f"Downloading from: {url}")
        logger.info(f"Size: ~{cls.MODELS[model_id]['size_gb']} GB")

        try:
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))

            with open(zip_path, 'wb') as file:
                if total_size > 0:
                    with tqdm(
                        desc=f"Downloading {model_id}",
                        total=total_size,
                        unit='iB',
                        unit_scale=True,
                        unit_divisor=1024,
                    ) as progress_bar:
                        for chunk in response.iter_content(chunk_size=8192):
                            size = file.write(chunk)
                            progress_bar.update(size)
                else:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)

            logger.info(f"Downloaded to {zip_path}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download model '{model_id}': {e}")
            if zip_path.exists():
                zip_path.unlink()
            raise

        # Extract the HMS project from nested zip structure
        # M3 zips contain: HEC-HMS/{unit_id}.zip which contains the actual HMS files
        logger.info(f"Extracting HMS project to {project_dest}...")

        try:
            project_dest.mkdir(parents=True, exist_ok=True)

            # Find the inner HMS zip file
            # Pattern: HEC-HMS/{model}_{unit_id}.zip or HEC-HMS/{unit_id with underscores}.zip
            unit_patterns = [
                f"HEC-HMS/{model_id}_{unit_id.replace('-', '_')}.zip",
                f"HEC-HMS/{model_id}_{unit_id.replace('-', '-')}.zip",
                f"HEC-HMS/{unit_id.replace('-', '_')}.zip",
                f"HEC-HMS/{unit_id}.zip",
            ]

            with zipfile.ZipFile(zip_path, 'r') as outer_zf:
                # List all HMS zip files in the outer zip
                hms_zips = [n for n in outer_zf.namelist()
                           if n.startswith('HEC-HMS/') and n.endswith('.zip')]

                logger.debug(f"Found {len(hms_zips)} HMS zip files in model")

                # Find matching inner zip
                inner_zip_name = None
                for pattern in unit_patterns:
                    for hms_zip in hms_zips:
                        if hms_zip.lower() == pattern.lower():
                            inner_zip_name = hms_zip
                            break
                    if inner_zip_name:
                        break

                # Fallback: try to match by unit_id prefix
                if not inner_zip_name:
                    unit_base = unit_id.replace('-', '_').replace('-', '')
                    for hms_zip in hms_zips:
                        zip_base = Path(hms_zip).stem.replace('_', '').replace('-', '')
                        if unit_base.lower() in zip_base.lower():
                            inner_zip_name = hms_zip
                            logger.debug(f"Matched by prefix: {hms_zip}")
                            break

                if not inner_zip_name:
                    # List available for debugging
                    available = [Path(z).stem for z in hms_zips]
                    raise FileNotFoundError(
                        f"Could not find HMS zip for unit '{unit_id}' in model {model_id}. "
                        f"Available: {available}"
                    )

                logger.info(f"Found inner HMS zip: {inner_zip_name}")

                # Extract inner zip to memory and then extract its contents
                with outer_zf.open(inner_zip_name) as inner_file:
                    inner_content = inner_file.read()
                    inner_zf = zipfile.ZipFile(io.BytesIO(inner_content))

                    extracted_count = 0
                    for member in inner_zf.namelist():
                        # Skip directory entries
                        if member.endswith('/'):
                            continue

                        # Remove the first folder level (e.g., "D_D100-00-00/file.hms" -> "file.hms")
                        parts = member.split('/')
                        if len(parts) > 1:
                            relative_file = '/'.join(parts[1:])
                        else:
                            relative_file = member

                        if relative_file:
                            dest_file = project_dest / relative_file
                            dest_file.parent.mkdir(parents=True, exist_ok=True)

                            with inner_zf.open(member) as src:
                                with open(dest_file, 'wb') as dst:
                                    shutil.copyfileobj(src, dst)
                            extracted_count += 1

                    inner_zf.close()

                logger.info(f"Extracted {extracted_count} files")

        except Exception as e:
            logger.error(f"Failed to extract HMS project: {e}")
            if project_dest.exists():
                shutil.rmtree(project_dest)
            raise
        finally:
            # Clean up zip file
            if zip_path.exists():
                zip_path.unlink()
                logger.debug(f"Removed temporary zip file: {zip_path}")

        logger.info(f"Successfully extracted to {project_dest}")
        return project_dest

    @classmethod
    @log_call
    def extract_model(
        cls,
        model_id: str,
        output_path: Optional[Union[str, Path]] = None,
        overwrite: bool = False
    ) -> Dict[str, Path]:
        """
        Extract all HMS projects from an M3 Model.

        Args:
            model_id: Model letter (e.g., 'G' for San Jacinto River)
            output_path: Base output directory
            overwrite: If True, overwrite existing extractions

        Returns:
            Dictionary mapping unit_id to extracted path

        Example:
            >>> # Extract all San Jacinto River HMS projects
            >>> paths = HmsM3Model.extract_model('G')
            >>> for unit_id, path in paths.items():
            ...     print(f"{unit_id}: {path}")
        """
        model_id = model_id.upper()

        if model_id not in cls.MODELS:
            available = ', '.join(sorted(cls.MODELS.keys()))
            raise ValueError(f"Model '{model_id}' not found. Available: {available}")

        catalog = cls._load_catalog()
        model_projects = catalog[catalog['model_id'] == model_id]

        if len(model_projects) == 0:
            logger.warning(f"No HMS projects found in model '{model_id}'")
            return {}

        extracted = {}
        for _, row in model_projects.iterrows():
            unit_id = row['unit_id']
            try:
                path = cls.extract_project(
                    model_id,
                    unit_id,
                    output_path=output_path,
                    overwrite=overwrite
                )
                extracted[unit_id] = path
            except Exception as e:
                logger.error(f"Failed to extract '{unit_id}': {e}")

        logger.info(f"Extracted {len(extracted)} of {len(model_projects)} HMS projects from model '{model_id}'")
        return extracted

    @classmethod
    @log_call
    def is_project_extracted(
        cls,
        model_id: str,
        unit_id: str,
        output_path: Optional[Union[str, Path]] = None
    ) -> bool:
        """
        Check if an HMS project has already been extracted.

        Args:
            model_id: Model letter
            unit_id: HCFCD unit number
            output_path: Base output directory (default: ./m3_hms_projects/)

        Returns:
            True if project folder exists

        Example:
            >>> if not HmsM3Model.is_project_extracted('D', 'D100-00-00'):
            ...     HmsM3Model.extract_project('D', 'D100-00-00')
        """
        model_id = model_id.upper()

        if output_path is None:
            base_output = cls.models_dir
        else:
            base_output = Path(output_path)
            if not base_output.is_absolute():
                base_output = Path.cwd() / base_output

        project_path = base_output / model_id / unit_id
        exists = project_path.exists() and project_path.is_dir()

        logger.debug(f"Project '{model_id}/{unit_id}' extracted: {exists}")
        return exists

    @classmethod
    @log_call
    def clean_projects_directory(
        cls,
        output_path: Optional[Union[str, Path]] = None
    ) -> None:
        """
        Remove all extracted M3 HMS projects.

        Args:
            output_path: Directory to clean (default: ./m3_hms_projects/)

        Example:
            >>> HmsM3Model.clean_projects_directory()
        """
        if output_path is None:
            target = cls.models_dir
        else:
            target = Path(output_path)
            if not target.is_absolute():
                target = Path.cwd() / target

        if target.exists():
            logger.info(f"Removing all projects from: {target}")
            shutil.rmtree(target)
            logger.info("Projects directory cleaned")
        else:
            logger.info(f"Directory does not exist: {target}")

        target.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_statistics(cls) -> Dict:
        """
        Get summary statistics about M3 HMS projects.

        Returns:
            Dictionary with catalog statistics

        Example:
            >>> stats = HmsM3Model.get_statistics()
            >>> print(f"Total projects: {stats['total_projects']}")
        """
        catalog = cls._load_catalog()

        stats = {
            'total_projects': len(catalog),
            'total_models': catalog['model_id'].nunique(),
            'models_with_most_projects': catalog['model_id'].value_counts().head(3).to_dict(),
            'hms_versions': catalog['hms_version'].value_counts().to_dict() if 'hms_version' in catalog.columns else {},
            'loss_methods': catalog['loss_method'].value_counts().to_dict() if 'loss_method' in catalog.columns else {},
        }

        return stats
