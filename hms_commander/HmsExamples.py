"""
HmsExamples - Manage HEC-HMS example projects from installed versions

This module provides utilities for discovering, listing, and extracting HEC-HMS
example projects from local HMS installations. Unlike RasExamples which downloads
from GitHub, HmsExamples uses the samples.zip bundled with each HMS installation.

Key Features:
- Auto-detect installed HMS versions (4.x and 3.x)
- List available example projects per version
- Extract projects with consistent structure regardless of zip format
- Integrate with hms-commander workflows

Usage:
    from hms_commander import HmsExamples

    # Discover installed versions
    versions = HmsExamples.list_versions()
    # ["4.13", "4.11", "3.5", "3.3"]

    # List projects for a version
    projects = HmsExamples.list_projects("4.13")
    # ["castro", "river_bend", "tenk", "tifton"]

    # Extract a project
    path = HmsExamples.extract_project("castro", version="4.13")

    # Get HMS executable for workflow
    exe = HmsExamples.get_hms_exe("4.13")
"""

import os
import re
import zipfile
import shutil
import logging
import json
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd

from .LoggingConfig import get_logger, log_call

logger = get_logger(__name__)


class HmsExamples:
    """
    Manage HEC-HMS example projects from installed versions.

    This class discovers HMS installations, catalogs available example projects,
    and extracts them for use with hms-commander workflows.

    All methods are class methods - no instantiation required.

    Example:
        # List what's available
        versions = HmsExamples.list_versions()
        projects = HmsExamples.list_projects("4.13")

        # Extract and use
        path = HmsExamples.extract_project("castro")
        hms = init_hms_project(path)
    """

    # Standard HMS installation paths to search
    DEFAULT_INSTALL_PATHS = [
        Path("C:/Program Files/HEC/HEC-HMS"),       # 64-bit HMS 4.x
        Path("C:/Program Files (x86)/HEC/HEC-HMS"), # 32-bit HMS 3.x
        Path.home() / "HEC/HEC-HMS",                # User install
    ]

    # Valid version pattern (e.g., 4.13, 3.5, 4.7.1)
    VALID_VERSION_PATTERN = r'^\d+\.\d+(\.\d+)?$'

    # Output directories
    base_dir = Path.cwd()
    projects_dir = base_dir / 'hms_example_projects'
    ebfe_projects_dir = base_dir / 'example_projects'

    # eBFE deliveries currently validated with HMS project content in
    # ras-commander's delivery matrix.
    EBFE_HMS_PROJECTS = {
        "lake-maurepas",
        "north-galveston-bay",
    }

    # Cache
    _installed_versions: Optional[Dict[str, Path]] = None
    _project_catalog: Optional[pd.DataFrame] = None

    @classmethod
    @log_call
    def detect_installed_versions(
        cls,
        additional_paths: Optional[List[Path]] = None
    ) -> Dict[str, Path]:
        """
        Scan system for installed HEC-HMS versions.

        Searches standard installation paths and any additional paths provided.
        Only includes versions that have a samples.zip file.

        Args:
            additional_paths: Extra paths to search beyond defaults

        Returns:
            Dict mapping version strings to installation paths
            Example: {"4.13": Path("C:/Program Files/HEC/HEC-HMS/4.13"), ...}

        Example:
            versions = HmsExamples.detect_installed_versions()
            for version, path in versions.items():
                print(f"HMS {version} at {path}")
        """
        if cls._installed_versions is not None:
            return cls._installed_versions

        versions = {}
        search_paths = list(cls.DEFAULT_INSTALL_PATHS)

        if additional_paths:
            search_paths.extend([Path(p) for p in additional_paths])

        for base_path in search_paths:
            if not base_path.exists():
                logger.debug(f"Path does not exist: {base_path}")
                continue

            logger.debug(f"Scanning {base_path} for HMS installations")

            for item in base_path.iterdir():
                if not item.is_dir():
                    continue

                # Check if folder name matches version pattern
                if not re.match(cls.VALID_VERSION_PATTERN, item.name):
                    continue

                # Check for samples.zip
                samples_zip = item / "samples.zip"
                if samples_zip.exists():
                    versions[item.name] = item
                    logger.info(f"Found HMS {item.name} at {item}")
                else:
                    logger.debug(f"HMS {item.name} found but no samples.zip")

        cls._installed_versions = versions

        if not versions:
            logger.warning("No HEC-HMS installations with examples found")
        else:
            logger.info(f"Found {len(versions)} HMS installation(s) with examples")

        return versions

    @classmethod
    @log_call
    def list_versions(cls) -> List[str]:
        """
        List all detected HMS versions with available examples.

        Returns:
            List of version strings, sorted descending (newest first)
            Example: ["4.13", "4.11", "3.5", "3.3"]

        Raises:
            RuntimeError: If no HMS installations found

        Example:
            versions = HmsExamples.list_versions()
            print(f"Latest version: {versions[0]}")
        """
        versions = cls.detect_installed_versions()

        if not versions:
            raise RuntimeError(
                "No HEC-HMS installations found. "
                "Please install HEC-HMS or specify additional search paths "
                "using detect_installed_versions(additional_paths=[...])"
            )

        # Sort versions descending (newest first)
        def version_key(v):
            parts = v.split('.')
            return tuple(int(p) for p in parts)

        sorted_versions = sorted(versions.keys(), key=version_key, reverse=True)
        return sorted_versions

    @classmethod
    @log_call
    def list_projects(
        cls,
        version: Optional[str] = None
    ) -> Union[List[str], Dict[str, List[str]]]:
        """
        List available example projects.

        Args:
            version: Specific HMS version. If None, returns dict of all versions.

        Returns:
            If version specified: List of project names
            If version is None: Dict mapping versions to project lists

        Raises:
            ValueError: If specified version is not installed

        Example:
            # All versions
            all_projects = HmsExamples.list_projects()
            # {"4.13": ["castro", ...], "4.11": [...]}

            # Specific version
            projects = HmsExamples.list_projects("4.13")
            # ["castro", "river_bend", "tenk", "tifton"]
        """
        cls._ensure_catalog_loaded()

        if version is not None:
            # Check version exists
            if version not in cls._installed_versions:
                available = cls.list_versions()
                raise ValueError(
                    f"HMS version '{version}' not installed. "
                    f"Available versions: {', '.join(available)}"
                )

            # Return projects for specific version
            mask = cls._project_catalog['version'] == version
            projects = cls._project_catalog[mask]['project'].tolist()
            return sorted(projects)
        else:
            # Return dict of all versions
            result = {}
            for ver in cls._installed_versions.keys():
                mask = cls._project_catalog['version'] == ver
                projects = cls._project_catalog[mask]['project'].tolist()
                result[ver] = sorted(projects)
            return result

    @classmethod
    @log_call
    def list_ebfe_projects(cls, hms_only: bool = True) -> pd.DataFrame:
        """
        List eBFE model sources available through ras-commander.

        This is a lightweight catalog call. It does not download or organize
        any model data. By default it returns only eBFE deliveries currently
        known to include validated HMS project content.

        Args:
            hms_only: If True, return only HMS-validated eBFE deliveries.
                If False, return the full ras-commander eBFE catalog.

        Returns:
            DataFrame with eBFE model metadata and HMS validation status.

        Raises:
            ImportError: If ras-commander is not installed or is too old to
                expose RasEbfeModels.

        Example:
            sources = HmsExamples.list_ebfe_projects()
            print(sources[["key", "study_area", "hms_validated"]])
        """
        RasEbfeModels = cls._import_ras_ebfe_models()

        columns = [
            "key",
            "study_area",
            "huc8",
            "ras_version",
            "hms_validated",
            "notes",
        ]
        records = []
        for key, metadata in RasEbfeModels.available_models().items():
            hms_validated = key in cls.EBFE_HMS_PROJECTS
            if hms_only and not hms_validated:
                continue

            records.append({
                "key": key,
                "study_area": metadata.get("study_area"),
                "huc8": metadata.get("huc8"),
                "ras_version": metadata.get("ras_version"),
                "hms_validated": hms_validated,
                "notes": metadata.get("notes"),
            })

        return pd.DataFrame.from_records(records, columns=columns)

    @classmethod
    @log_call
    def available_ebfe_projects(cls, hms_only: bool = True) -> pd.DataFrame:
        """
        Compatibility alias for list_ebfe_projects().

        Args:
            hms_only: If True, return only HMS-validated eBFE deliveries.

        Returns:
            DataFrame with eBFE model metadata.
        """
        return cls.list_ebfe_projects(hms_only=hms_only)

    @classmethod
    @log_call
    def extract_project(
        cls,
        project_name: str,
        version: Optional[str] = None,
        output_path: Optional[Union[str, Path]] = None,
        suffix: Optional[str] = None,
        overwrite: bool = True
    ) -> Path:
        """
        Extract an HMS example project for use.

        Args:
            project_name: Name of the project (e.g., "castro", "tenk")
            version: HMS version to extract from. If None, uses latest installed.
            output_path: Where to extract. Default: ./hms_example_projects/
            suffix: Optional suffix appended to the extracted folder name using
                "{project_name}_{suffix}". Useful for notebook-number isolation.
            overwrite: If True, delete existing project folder first

        Returns:
            Path to extracted project folder

        Raises:
            ValueError: If project not found or version not installed

        Example:
            # Basic extraction
            path = HmsExamples.extract_project("castro")

            # Specific version
            path = HmsExamples.extract_project("castro", version="4.11")

            # Custom output location
            path = HmsExamples.extract_project("castro", output_path="my_tests/")

            # Notebook-specific isolated extraction
            path = HmsExamples.extract_project(
                "castro",
                output_path="example_projects/",
                suffix="015",
            )

            # Use with hms-commander
            from hms_commander import init_hms_project
            hms = init_hms_project(path)
        """
        cls._ensure_catalog_loaded()

        # Determine version to use
        if version is None:
            version = cls.list_versions()[0]  # Latest
            logger.info(f"Using latest installed version: {version}")

        # Validate version
        if version not in cls._installed_versions:
            available = cls.list_versions()
            raise ValueError(
                f"HMS version '{version}' not installed. "
                f"Available: {', '.join(available)}"
            )

        # Validate project exists for this version
        available_projects = cls.list_projects(version)
        if project_name not in available_projects:
            raise ValueError(
                f"Project '{project_name}' not found in HMS {version}. "
                f"Available projects: {', '.join(available_projects)}"
            )

        # Determine output directory
        if output_path is None:
            base_output = cls.projects_dir
        else:
            base_output = Path(output_path)
            if not base_output.is_absolute():
                base_output = Path.cwd() / base_output

        # Create output directory
        base_output.mkdir(parents=True, exist_ok=True)

        folder_name = cls._get_folder_name(project_name, suffix)
        project_dest = base_output / folder_name

        # Handle existing directory
        if project_dest.exists():
            if overwrite:
                logger.info(f"Removing existing project folder: {project_dest}")
                shutil.rmtree(project_dest)
            else:
                logger.info(f"Project already exists (overwrite=False): {project_dest}")
                return project_dest

        # Get samples.zip path
        install_path = cls._installed_versions[version]
        samples_zip = install_path / "samples.zip"

        logger.info(
            f"Extracting '{project_name}' from HMS {version}"
            + (f" as '{folder_name}'" if suffix else "")
        )
        logger.info(f"Source: {samples_zip}")
        logger.info(f"Destination: {project_dest}")

        # Extract project
        cls._extract_project_from_zip(samples_zip, project_name, project_dest)

        logger.info(f"Successfully extracted '{project_name}' to {project_dest}")
        return project_dest

    @classmethod
    @log_call
    def extract_ebfe_project(
        cls,
        model_key: str = "lake-maurepas",
        project_name: Optional[str] = None,
        output_path: Optional[Union[str, Path]] = None,
        suffix: Optional[str] = None,
        overwrite: bool = True,
        download_root: Optional[Union[str, Path]] = None,
        organized_root: Optional[Union[str, Path]] = None,
        **organize_kwargs: Any,
    ) -> Path:
        """
        Extract the HMS portion of an eBFE delivery organized by ras-commander.

        ras-commander remains the source of truth for eBFE download and delivery
        normalization. This HMS wrapper calls RasEbfeModels lazily, then copies
        only the selected project from the organized ``HMS Model/`` folder into
        a notebook-safe example workspace.

        Args:
            model_key: eBFE model slug, alias, or HUC8. The default
                ``"lake-maurepas"`` is the preferred lightweight HMS example.
            project_name: Optional HMS project folder name or .hms stem to
                select when a delivery contains more than one HMS project.
            output_path: Base output folder. Default: ``./example_projects/``.
            suffix: Optional suffix appended to the eBFE workspace folder using
                ``"{model_key}_{suffix}"``.
            overwrite: If True, replace the copied HMS-only folder. Download
                and organized-cache folders are preserved.
            download_root: Optional ras-commander download cache root. Default:
                ``<workspace>/downloads``.
            organized_root: Optional ras-commander organized delivery root.
                Default: ``<workspace>/organized``.
            **organize_kwargs: Additional keyword arguments forwarded to
                ``RasEbfeModels.organize_model()``.

        Returns:
            Path to the copied HMS project folder containing the ``.hms`` file.

        Raises:
            ImportError: If ras-commander is unavailable.
            FileNotFoundError: If the organized eBFE delivery has no HMS Model
                folder or no .hms project file.
            ValueError: If multiple HMS projects are present and project_name
                was not specified.

        Example:
            project_dir = HmsExamples.extract_ebfe_project(
                "lake-maurepas",
                output_path=Path.cwd() / "example_projects",
                suffix="015",
                overwrite=False,
            )
        """
        RasEbfeModels = cls._import_ras_ebfe_models()
        canonical_key = RasEbfeModels.normalize_model_key(model_key)

        if output_path is None:
            base_output = Path.cwd() / "example_projects"
        else:
            base_output = cls._resolve_path(output_path)

        workspace = base_output / cls._get_folder_name(canonical_key, suffix)
        workspace.mkdir(parents=True, exist_ok=True)

        if download_root is None:
            download_root_path = workspace / "downloads"
        else:
            download_root_path = cls._resolve_path(download_root)

        if organized_root is None:
            organized_root_path = workspace / "organized"
        else:
            organized_root_path = cls._resolve_path(organized_root)

        hms_output_root = workspace / "hms"
        if hms_output_root.exists() and not overwrite:
            existing_projects = cls._discover_hms_project_roots(hms_output_root)
            if existing_projects:
                selected_root, _ = cls._select_hms_project(
                    existing_projects,
                    project_name=project_name,
                )
                logger.info(f"Using existing eBFE HMS project: {selected_root}")
                return selected_root

        logger.info(f"Organizing eBFE model '{canonical_key}' through ras-commander")
        organized_delivery = Path(RasEbfeModels.organize_model(
            canonical_key,
            download_root=download_root_path,
            output_root=organized_root_path,
            **organize_kwargs,
        ))

        hms_source_root = organized_delivery / "HMS Model"
        if not hms_source_root.exists():
            raise FileNotFoundError(
                f"No HMS Model folder found in organized eBFE delivery: "
                f"{organized_delivery}"
            )

        source_projects = cls._discover_hms_project_roots(hms_source_root)
        if not source_projects:
            raise FileNotFoundError(
                f"No .hms project files found in eBFE HMS Model folder: "
                f"{hms_source_root}"
            )

        selected_source_root, selected_hms_file = cls._select_hms_project(
            source_projects,
            project_name=project_name,
        )

        if hms_output_root.exists():
            if overwrite:
                logger.info(f"Removing existing HMS-only eBFE folder: {hms_output_root}")
                shutil.rmtree(hms_output_root)
            else:
                raise FileExistsError(
                    f"HMS output folder already exists: {hms_output_root}"
                )

        destination_name = (
            selected_source_root.name
            if selected_source_root != hms_source_root
            else selected_hms_file.stem
        )
        destination = hms_output_root / destination_name
        destination.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Copying HMS project from {selected_source_root} to {destination}")
        shutil.copytree(selected_source_root, destination)

        metadata = RasEbfeModels.available_models().get(canonical_key, {})
        provenance = {
            "source": "eBFE",
            "model_key": canonical_key,
            "requested_model_key": model_key,
            "study_area": metadata.get("study_area"),
            "huc8": metadata.get("huc8"),
            "ras_version": metadata.get("ras_version"),
            "hms_project": destination.name,
            "hms_file": selected_hms_file.name,
            "organized_delivery": str(organized_delivery),
            "source_hms_project": str(selected_source_root),
            "ras_commander_version": cls._get_package_version("ras-commander"),
            "extracted_utc": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
        }
        cls._write_ebfe_provenance(destination, provenance)

        logger.info(f"Successfully extracted eBFE HMS project to {destination}")
        return destination

    @classmethod
    @log_call
    def extract_all(
        cls,
        version: Optional[str] = None,
        output_path: Optional[Union[str, Path]] = None,
        suffix: Optional[str] = None
    ) -> Dict[str, Path]:
        """
        Extract all example projects for a given version.

        Args:
            version: HMS version. If None, uses latest installed.
            output_path: Base output directory
            suffix: Optional suffix appended to each extracted project folder.

        Returns:
            Dict mapping project names to extracted paths

        Example:
            paths = HmsExamples.extract_all("4.13")
            for name, path in paths.items():
                print(f"{name}: {path}")
        """
        if version is None:
            version = cls.list_versions()[0]

        projects = cls.list_projects(version)
        extracted = {}

        for project_name in projects:
            try:
                path = cls.extract_project(
                    project_name,
                    version=version,
                    output_path=output_path,
                    suffix=suffix,
                )
                extracted[project_name] = path
            except Exception as e:
                logger.error(f"Failed to extract '{project_name}': {e}")

        return extracted

    @classmethod
    @log_call
    def get_project_info(
        cls,
        project_name: str,
        version: Optional[str] = None
    ) -> Dict:
        """
        Get information about an example project without extracting.

        Args:
            project_name: Name of the project
            version: HMS version. If None, uses latest.

        Returns:
            Dict with project information:
            - name: Project name
            - version: HMS version
            - files: List of files in project
            - has_dss: Whether project includes DSS files
            - basin_models: List of .basin files
            - met_models: List of .met files
            - control_specs: List of .control files
            - run_configs: List of .run files

        Example:
            info = HmsExamples.get_project_info("castro")
            print(f"Basin models: {info['basin_models']}")
        """
        cls._ensure_catalog_loaded()

        if version is None:
            version = cls.list_versions()[0]

        # Validate
        if version not in cls._installed_versions:
            raise ValueError(f"HMS version '{version}' not installed")

        available_projects = cls.list_projects(version)
        if project_name not in available_projects:
            raise ValueError(f"Project '{project_name}' not found in HMS {version}")

        # Get file list from zip
        install_path = cls._installed_versions[version]
        samples_zip = install_path / "samples.zip"

        files = []
        with zipfile.ZipFile(samples_zip, 'r') as zf:
            for member in zf.namelist():
                # Find files belonging to this project
                parts = Path(member).parts
                try:
                    proj_idx = parts.index(project_name)
                    relative = '/'.join(parts[proj_idx + 1:])
                    if relative:  # Skip directory entries
                        files.append(relative)
                except ValueError:
                    continue

        # Categorize files
        info = {
            'name': project_name,
            'version': version,
            'files': files,
            'has_dss': any(f.endswith('.dss') for f in files),
            'basin_models': [f for f in files if f.endswith('.basin')],
            'met_models': [f for f in files if f.endswith('.met')],
            'control_specs': [f for f in files if f.endswith('.control')],
            'run_configs': [f for f in files if f.endswith('.run')],
            'gage_files': [f for f in files if f.endswith('.gage')],
            'hms_file': next((f for f in files if f.endswith('.hms')), None),
        }

        return info

    @classmethod
    @log_call
    def is_project_extracted(
        cls,
        project_name: str,
        output_path: Optional[Union[str, Path]] = None,
        suffix: Optional[str] = None
    ) -> bool:
        """
        Check if a project has already been extracted.

        Args:
            project_name: Name of the project
            output_path: Base output directory (default: ./hms_example_projects/)
            suffix: Optional suffix used when extracting the project.

        Returns:
            True if project directory exists

        Example:
            if not HmsExamples.is_project_extracted("castro"):
                HmsExamples.extract_project("castro")
        """
        if output_path is None:
            base_output = cls.projects_dir
        else:
            base_output = Path(output_path)

        project_path = base_output / cls._get_folder_name(project_name, suffix)
        exists = project_path.exists() and project_path.is_dir()

        logger.debug(f"Project '{project_name}' extracted: {exists}")
        return exists

    @classmethod
    @log_call
    def clean_projects_directory(
        cls,
        output_path: Optional[Union[str, Path]] = None
    ) -> None:
        """
        Remove all extracted example projects.

        Args:
            output_path: Directory to clean (default: ./hms_example_projects/)

        Example:
            HmsExamples.clean_projects_directory()
        """
        if output_path is None:
            target = cls.projects_dir
        else:
            target = Path(output_path)

        if target.exists():
            logger.info(f"Removing all projects from: {target}")
            shutil.rmtree(target)
            logger.info("Projects directory cleaned")
        else:
            logger.info(f"Directory does not exist: {target}")

        # Recreate empty directory
        target.mkdir(parents=True, exist_ok=True)

    @classmethod
    @log_call
    def get_hms_exe(cls, version: Optional[str] = None) -> Path:
        """
        Get path to HEC-HMS executable for a version.

        Useful for workflow integration - extract project, get exe, run simulation.

        Args:
            version: HMS version. If None, uses latest installed.

        Returns:
            Path to HEC-HMS.cmd (preferred for Jython) or HEC-HMS.exe

        Raises:
            ValueError: If version not installed
            FileNotFoundError: If executable not found

        Example:
            exe = HmsExamples.get_hms_exe("4.13")
            hms = init_hms_project(project_path, hms_exe_path=exe)
        """
        versions = cls.detect_installed_versions()

        if version is None:
            version = cls.list_versions()[0]

        if version not in versions:
            available = cls.list_versions()
            raise ValueError(
                f"HMS version '{version}' not installed. "
                f"Available: {', '.join(available)}"
            )

        install_path = versions[version]

        # Prefer .cmd for Jython script support
        cmd_path = install_path / "HEC-HMS.cmd"
        if cmd_path.exists():
            return cmd_path

        exe_path = install_path / "HEC-HMS.exe"
        if exe_path.exists():
            return exe_path

        raise FileNotFoundError(
            f"HEC-HMS executable not found in {install_path}"
        )

    @classmethod
    def get_install_path(cls, version: Optional[str] = None) -> Path:
        """
        Get the installation path for an HMS version.

        Args:
            version: HMS version. If None, uses latest.

        Returns:
            Path to HMS installation directory

        Example:
            install = HmsExamples.get_install_path("4.13")
            # Path("C:/Program Files/HEC/HEC-HMS/4.13")
        """
        versions = cls.detect_installed_versions()

        if version is None:
            version = cls.list_versions()[0]

        if version not in versions:
            raise ValueError(f"HMS version '{version}' not installed")

        return versions[version]

    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------

    @classmethod
    def _import_ras_ebfe_models(cls):
        """Import ras-commander's eBFE catalog lazily."""
        try:
            from ras_commander.sources.federal import RasEbfeModels
            return RasEbfeModels
        except ImportError as primary_error:
            try:
                from ras_commander.ebfe_models import RasEbfeModels
                return RasEbfeModels
            except ImportError:
                raise ImportError(
                    "eBFE example extraction requires ras-commander with "
                    "RasEbfeModels. Install hms-commander[dss] or install a "
                    "recent ras-commander build."
                ) from primary_error

    @classmethod
    def _make_safe_folder_name(cls, name: str) -> str:
        """Convert a string to a filesystem-safe folder name."""
        return re.sub(r'[^a-zA-Z0-9_\-]', '_', str(name))

    @classmethod
    def _get_folder_name(cls, project_name: str, suffix: Optional[str] = None) -> str:
        """Compute an extraction folder name with an optional safe suffix."""
        if suffix is None or str(suffix) == "":
            return project_name

        safe_suffix = cls._make_safe_folder_name(str(suffix))
        return f"{project_name}_{safe_suffix}"

    @classmethod
    def _resolve_path(cls, path: Union[str, Path]) -> Path:
        """Resolve relative user paths against the current working directory."""
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = Path.cwd() / resolved
        return resolved

    @classmethod
    def _discover_hms_project_roots(cls, hms_root: Path) -> List[Tuple[Path, Path]]:
        """Find HMS project roots under a folder."""
        hms_root = Path(hms_root)
        if not hms_root.exists():
            return []

        projects = []
        seen_roots = set()
        for hms_file in sorted(hms_root.rglob("*.hms")):
            if not hms_file.is_file():
                continue
            project_root = hms_file.parent
            if project_root in seen_roots:
                continue
            projects.append((project_root, hms_file))
            seen_roots.add(project_root)

        return projects

    @classmethod
    def _select_hms_project(
        cls,
        projects: List[Tuple[Path, Path]],
        project_name: Optional[str] = None,
    ) -> Tuple[Path, Path]:
        """Select one HMS project from discovered project roots."""
        if not projects:
            raise FileNotFoundError("No HMS projects were discovered")

        if project_name is None:
            if len(projects) == 1:
                return projects[0]

            available = ", ".join(
                f"{root.name} ({hms_file.name})" for root, hms_file in projects
            )
            raise ValueError(
                "Multiple HMS projects found; specify project_name. "
                f"Available projects: {available}"
            )

        requested = str(project_name).lower()
        matches = [
            (root, hms_file)
            for root, hms_file in projects
            if root.name.lower() == requested or hms_file.stem.lower() == requested
        ]

        if not matches:
            available = ", ".join(
                f"{root.name} ({hms_file.stem})" for root, hms_file in projects
            )
            raise ValueError(
                f"HMS project '{project_name}' not found. "
                f"Available projects: {available}"
            )

        if len(matches) > 1:
            available = ", ".join(
                f"{root.name} ({hms_file.name})" for root, hms_file in matches
            )
            raise ValueError(
                f"HMS project name '{project_name}' is ambiguous: {available}"
            )

        return matches[0]

    @classmethod
    def _write_ebfe_provenance(cls, project_dir: Path, provenance: Dict[str, Any]) -> None:
        """Write eBFE source metadata into the copied HMS project folder."""
        project_dir = Path(project_dir)
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "SOURCE_EBFE.json").write_text(
            json.dumps(provenance, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    @classmethod
    def _get_package_version(cls, package_name: str) -> Optional[str]:
        """Return an installed package version when available."""
        try:
            return importlib_metadata.version(package_name)
        except importlib_metadata.PackageNotFoundError:
            return None

    @classmethod
    def _ensure_catalog_loaded(cls) -> None:
        """Ensure project catalog is loaded."""
        if cls._installed_versions is None:
            cls.detect_installed_versions()

        if cls._project_catalog is None:
            cls._build_project_catalog()

    @classmethod
    def _build_project_catalog(cls) -> None:
        """Build complete catalog of all versions and projects."""
        logger.debug("Building project catalog")

        records = []

        for version, install_path in cls._installed_versions.items():
            samples_zip = install_path / "samples.zip"

            if not samples_zip.exists():
                logger.warning(f"samples.zip not found for HMS {version}")
                continue

            projects = cls._scan_zip_projects(samples_zip)

            for project in projects:
                records.append({
                    'version': version,
                    'project': project,
                    'install_path': str(install_path),
                    'samples_zip': str(samples_zip),
                })

        cls._project_catalog = pd.DataFrame(records)
        logger.info(f"Catalog built: {len(records)} project entries")

    @classmethod
    def _scan_zip_projects(cls, zip_path: Path) -> List[str]:
        """
        Extract list of project names from samples.zip.

        Projects are identified by presence of .hms file.
        """
        projects = set()

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.hms'):
                        # Get folder containing .hms file
                        parts = Path(name).parts
                        if len(parts) >= 2:
                            # Could be samples/project/file.hms or
                            # samples/samples/project/file.hms
                            # Find the folder right before the .hms file
                            project_folder = parts[-2]
                            if project_folder != 'samples':
                                projects.add(project_folder)
        except zipfile.BadZipFile:
            logger.error(f"Invalid zip file: {zip_path}")
        except Exception as e:
            logger.error(f"Error scanning {zip_path}: {e}")

        return list(projects)

    @classmethod
    def _extract_project_from_zip(
        cls,
        zip_path: Path,
        project_name: str,
        dest: Path
    ) -> None:
        """
        Extract a project from samples.zip to destination.

        Handles varying internal structures:
        - HMS 4.13: samples/samples/project_name/...
        - HMS 4.11: samples/project_name/...
        """
        dest.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zf:
            for member in zf.namelist():
                parts = Path(member).parts

                # Find the project folder in the path
                try:
                    proj_idx = parts.index(project_name)
                except ValueError:
                    continue  # Not part of this project

                # Get relative path from project folder
                relative_parts = parts[proj_idx + 1:]

                if not relative_parts:
                    continue  # Skip the project folder itself

                relative_path = Path(*relative_parts)
                extract_to = dest / relative_path

                if member.endswith('/'):
                    # Directory entry
                    extract_to.mkdir(parents=True, exist_ok=True)
                else:
                    # File entry
                    extract_to.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as source:
                        with open(extract_to, 'wb') as target:
                            shutil.copyfileobj(source, target)

    @classmethod
    def reset_cache(cls) -> None:
        """
        Clear cached data to force re-detection.

        Useful if HMS installations have changed.

        Example:
            HmsExamples.reset_cache()
            versions = HmsExamples.list_versions()  # Re-scans system
        """
        cls._installed_versions = None
        cls._project_catalog = None
        logger.info("HmsExamples cache cleared")
