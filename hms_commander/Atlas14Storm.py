"""
Atlas14Storm - Atlas 14 precipitation helpers for HEC-HMS.

This module supports two NOAA Atlas 14 workflows:

1. Temporal distribution download/parsing for HMS "Specified Pattern" storms
2. Point depth-duration-frequency lookup for HMS "Frequency Based Hypothetical"
   design storms

The temporal-distribution workflow matches the algorithm used by HEC-HMS
internally for specified-pattern design storms.

Time Axis:
    Output DataFrames include a t=0 zero-sentinel row. Row 0 has hour=0.0
    and incremental_depth=0.0; subsequent rows are interval end times, so a
    24-hour storm at 30-minute intervals ends at hour=24.0.
"""

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import pandas as pd
import numpy as np
import requests

from .LoggingConfig import get_logger
from .Decorators import log_call
from ._hyetograph import (
    build_hyetograph_frame,
    incremental_depths_from_cumulative_pattern,
)

logger = get_logger(__name__)


@dataclass
class Atlas14Config:
    """Configuration for Atlas 14 temporal distribution."""

    state: str  # Two-letter state code (lowercase)
    region: Union[int, str]  # Atlas 14 region number or named regional token
    duration: int  # Duration in hours

    @property
    def url(self) -> str:
        """Generate the NOAA temporal distribution URL."""
        state = str(self.state).strip().lower()
        region = str(self.region).strip().lower()
        return (
            "https://hdsc.nws.noaa.gov/pub/hdsc/data/"
            f"{state}/{state}_{region}_{self.duration}h_temporal.csv"
        )

    @property
    def region_code(self) -> str:
        """Generate region identifier (e.g., TX_R3)."""
        if isinstance(self.region, int):
            return f"{self.state.upper()}_R{self.region}"
        return f"{self.state.upper()}_{str(self.region).upper()}"


class Atlas14Storm:
    """
    Static class for generating Atlas 14 hyetographs.

    Implements the same algorithm as HEC-HMS "Hypothetical Storm" with
    "Specified Pattern" storm type.

    All methods are static - no instantiation required.

    Supported Durations:
        - 6 hours
        - 12 hours
        - 24 hours (most common, default)
        - 96 hours (4 days)

        Note: 48-hour duration is NOT supported (NOAA does not publish 48h
        temporal distributions). Use FrequencyStorm for 48-hour storms.

    Regional Availability:
        Multi-duration support (6h, 12h, 96h) is available for newer Atlas 14
        volumes (Texas, Midwest, Southeast). Older volumes (California, Ohio,
        Southwest) may only have 24-hour data.

    Example:
        >>> from hms_commander import Atlas14Storm
        >>>
        >>> # Generate hyetograph for 100-year, 24-hour storm in Houston, TX
        >>> hyetograph = Atlas14Storm.generate_hyetograph(
        ...     total_depth_inches=17.9,
        ...     state="tx",
        ...     region=3,
        ...     duration_hours=24,
        ...     aep_percent=1.0,
        ...     quartile="All Cases",
        ...     probability_column="50%"
        ... )
        >>> print(f"Generated {len(hyetograph)} time steps")
        >>> print(f"Total depth: {hyetograph['cumulative_depth'].iloc[-1]:.3f} inches")
        >>>
        >>> # Generate 6-hour storm
        >>> hyeto_6h = Atlas14Storm.generate_hyetograph(
        ...     total_depth_inches=10.0,
        ...     state="tx",
        ...     region=3,
        ...     duration_hours=6,
        ...     aep_percent=1.0,
        ...     probability_column="50%"
        ... )
    """

    # Supported durations (hours) - NOAA publishes temporal CSVs for these
    SUPPORTED_DURATIONS = [6, 12, 24, 96]

    # Standard quartile names
    QUARTILE_NAMES = [
        "First Quartile",
        "Second Quartile",
        "Third Quartile",
        "Fourth Quartile",
        "All Cases"
    ]

    # Standard probability columns (as percentages)
    PROBABILITY_COLUMNS = ["90%", "80%", "70%", "60%", "50%", "40%", "30%", "20%", "10%"]

    # Cache for temporal distributions (avoid re-downloading)
    _temporal_cache: Dict[str, Dict[str, pd.DataFrame]] = {}

    # NOAA point-frequency endpoint (returns JS-style assignments)
    PFDS_POINT_ENDPOINT = "https://hdsc.nws.noaa.gov/cgi-bin/hdsc/new/cgi_readH5.py"

    # Standard Atlas 14 PFDS duration table ordering
    PFDS_DURATION_LABELS = [
        "5-min",
        "10-min",
        "15-min",
        "30-min",
        "60-min",
        "2-hr",
        "3-hr",
        "6-hr",
        "12-hr",
        "24-hr",
        "2-day",
        "3-day",
        "4-day",
        "7-day",
        "10-day",
        "20-day",
        "30-day",
        "45-day",
        "60-day",
    ]
    PFDS_DURATION_MINUTES = [
        5,
        10,
        15,
        30,
        60,
        120,
        180,
        360,
        720,
        1440,
        2880,
        4320,
        5760,
        10080,
        14400,
        28800,
        43200,
        64800,
        86400,
    ]
    PFDS_RETURN_PERIOD_YEARS = [1, 2, 5, 10, 25, 50, 100, 200, 500, 1000]
    FREQUENCY_STORM_DURATIONS_MIN = [5, 15, 30, 60, 120, 180, 360, 1440]
    FREQUENCY_DURATION_LABEL_BY_MINUTES = {
        5: "5-min",
        15: "15-min",
        30: "30-min",
        60: "60-min",
        120: "2-hr",
        180: "3-hr",
        360: "6-hr",
        1440: "24-hr",
    }

    @staticmethod
    def _validate_duration(duration_hours: int) -> None:
        """
        Validate that duration is supported.

        Args:
            duration_hours: Storm duration in hours

        Raises:
            ValueError: If duration is not supported, with helpful message
        """
        if duration_hours == 48:
            raise ValueError(
                "48-hour duration is not available in NOAA Atlas 14 temporal distributions.\n"
                "NOAA publishes temporal data for: 6h, 12h, 24h, 96h only.\n\n"
                "For 48-hour storms, use FrequencyStorm instead:\n"
                "  from hms_commander import FrequencyStorm\n"
                "  hyeto = FrequencyStorm.generate_hyetograph(\n"
                "      total_depth_inches=your_depth,\n"
                "      total_duration_min=2880  # 48 hours\n"
                "  )"
            )

        if duration_hours not in Atlas14Storm.SUPPORTED_DURATIONS:
            raise ValueError(
                f"Duration {duration_hours}h is not supported.\n"
                f"Supported durations: {Atlas14Storm.SUPPORTED_DURATIONS}\n"
                f"For other durations, consider FrequencyStorm or StormGenerator."
            )

    @staticmethod
    def _normalize_cache_dir(cache_dir: Optional[Union[str, Path]]) -> Path:
        """Normalize an optional cache directory to a pathlib Path."""
        if cache_dir is None:
            return Atlas14Storm._default_cache_dir()
        return Path(cache_dir)

    @staticmethod
    def normalize_depth_units(units: str) -> str:
        """Normalize Atlas 14 depth units to the supported API labels."""
        normalized_units = str(units).strip().lower()
        if normalized_units in {"english", "in", "inch", "inches"}:
            return "english"
        if normalized_units in {"metric", "mm", "millimeter", "millimeters"}:
            return "metric"
        raise ValueError(f"Unsupported Atlas 14 units: {units!r}")

    @staticmethod
    def _normalize_depth_units(units: str) -> str:
        """Backward-compatible internal alias for depth-unit normalization."""
        return Atlas14Storm.normalize_depth_units(units)

    @staticmethod
    def convert_depths_to_inches(depths: Sequence[float], units: str = "english") -> List[float]:
        """Convert Atlas 14 depth values from their native units to inches."""
        native_depths = [float(depth) for depth in depths]
        normalized_units = Atlas14Storm.normalize_depth_units(units)
        if normalized_units == "metric":
            return [depth / 25.4 for depth in native_depths]
        return native_depths

    @staticmethod
    @log_call
    def download_temporal_csv(
        config: Atlas14Config,
        cache_dir: Optional[Union[str, Path]] = None
    ) -> str:
        """
        Download Atlas 14 temporal distribution CSV from NOAA.

        Args:
            config: Atlas14Config with state, region, duration
            cache_dir: Optional directory to cache downloaded files

        Returns:
            CSV content as string
        """
        # Check cache first
        if cache_dir is not None:
            cache_dir = Atlas14Storm._normalize_cache_dir(cache_dir)
            cache_file = cache_dir / f"{config.state}_{config.region}_{config.duration}h_temporal.csv"
            if cache_file.exists():
                logger.info(f"Using cached temporal distribution: {cache_file}")
                return cache_file.read_text()

        # Download from NOAA
        logger.info(f"Downloading temporal distribution from: {config.url}")
        response = requests.get(config.url, timeout=30)
        response.raise_for_status()

        content = response.text
        logger.info(f"Downloaded {len(content)} bytes")

        # Cache if directory provided
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(content)
            logger.info(f"Cached to: {cache_file}")

        return content

    @staticmethod
    @log_call
    def parse_temporal_csv(csv_content: str) -> Dict[str, pd.DataFrame]:
        """
        Parse Atlas 14 temporal distribution CSV into DataFrames.

        Args:
            csv_content: Raw CSV content as string

        Returns:
            Dictionary mapping quartile names to DataFrames
            Each DataFrame has:
            - Index: 'hours' (0 to 24 in 0.5-hour increments)
            - Columns: Probability strings ("90%", "80%", ..., "10%")
            - Values: Cumulative percentages (0 to 100)
        """
        lines = csv_content.strip().split('\n')

        # Quartile markers in CSV
        quartile_markers = {
            "FIRST-QUARTILE": "First Quartile",
            "SECOND-QUARTILE": "Second Quartile",
            "THIRD-QUARTILE": "Third Quartile",
            "FOURTH-QUARTILE": "Fourth Quartile",
            "ALL CASES": "All Cases"
        }

        quartile_data = {}
        current_quartile = None
        current_data = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for quartile header
            for marker, name in quartile_markers.items():
                if marker in line.upper():
                    # Save previous quartile
                    if current_quartile and current_data:
                        quartile_data[current_quartile] = current_data
                    current_quartile = name
                    current_data = []
                    break
            else:
                # Parse data row
                if current_quartile and line[0].isdigit():
                    values = [v.strip() for v in line.split(',')]
                    if len(values) >= 10:
                        try:
                            row = {
                                'hours': float(values[0]),
                                '90%': float(values[1]),
                                '80%': float(values[2]),
                                '70%': float(values[3]),
                                '60%': float(values[4]),
                                '50%': float(values[5]),
                                '40%': float(values[6]),
                                '30%': float(values[7]),
                                '20%': float(values[8]),
                                '10%': float(values[9])
                            }
                            current_data.append(row)
                        except ValueError:
                            pass

        # Save last quartile
        if current_quartile and current_data:
            quartile_data[current_quartile] = current_data

        # Convert to DataFrames
        result = {}
        for name, data in quartile_data.items():
            df = pd.DataFrame(data)
            df.set_index('hours', inplace=True)
            result[name] = df

        if not result:
            raise ValueError("No Atlas 14 quartile tables were parsed from the provided CSV content")

        sample_table = next(iter(result.values()))
        logger.info(f"Parsed {len(result)} quartile tables with {len(sample_table)} time steps each")
        return result

    @staticmethod
    @log_call
    def load_temporal_distribution(
        state: str,
        region: Union[int, str],
        duration_hours: int = 24,
        cache_dir: Optional[Union[str, Path]] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Load Atlas 14 temporal distribution with caching.

        Args:
            state: Two-letter state code (lowercase, e.g., "tx")
            region: Atlas 14 region number
            duration_hours: Storm duration in hours (default: 24)
                Supported: 6, 12, 24, 96 (NOAA published)
                Note: 48h is NOT available - use FrequencyStorm instead
            cache_dir: Optional cache directory (default: ~/.hms-commander/atlas14/)

        Returns:
            Dictionary mapping quartile names to temporal distribution DataFrames

        Raises:
            ValueError: If duration is not supported (48h) or not available for region
            requests.HTTPError: If NOAA server returns error
        """
        # Validate duration first
        Atlas14Storm._validate_duration(duration_hours)

        # Check memory cache
        cache_key = f"{state}_{region}_{duration_hours}h"
        if cache_key in Atlas14Storm._temporal_cache:
            logger.info(f"Using cached temporal distribution: {cache_key}")
            return Atlas14Storm._temporal_cache[cache_key]

        # Default cache directory
        cache_dir = Atlas14Storm._normalize_cache_dir(cache_dir)

        # Download and parse with 404 handling
        config = Atlas14Config(state=state, region=region, duration=duration_hours)
        try:
            csv_content = Atlas14Storm.download_temporal_csv(config, cache_dir)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise ValueError(
                    f"Duration {duration_hours}h is not available for {state.upper()} region {region}.\n"
                    f"This region may only have 24-hour temporal distributions.\n"
                    f"Try duration_hours=24 or use StormGenerator for other durations."
                ) from e
            raise

        temporal_distributions = Atlas14Storm.parse_temporal_csv(csv_content)

        # Cache in memory
        Atlas14Storm._temporal_cache[cache_key] = temporal_distributions

        return temporal_distributions

    @staticmethod
    def _default_cache_dir() -> Path:
        """Return the default Atlas 14 cache directory."""
        return Path.home() / ".hms-commander" / "atlas14"

    @staticmethod
    def _pfds_cache_file(
        latitude: float,
        longitude: float,
        series: str,
        units: str,
        cache_dir: Path,
    ) -> Path:
        """Build a deterministic cache file path for PFDS point responses."""
        lat_token = f"{latitude:.6f}".replace("-", "m").replace(".", "p")
        lon_token = f"{longitude:.6f}".replace("-", "m").replace(".", "p")
        return cache_dir / f"pfds_depth_{series}_{units}_{lat_token}_{lon_token}.txt"

    @staticmethod
    def _parse_pfds_assignment_value(raw_value: str) -> Any:
        """Parse a JS-style PFDS assignment value into a Python object."""
        value = raw_value.strip()
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value.strip("'\"")

    @staticmethod
    @log_call
    def parse_pfds_response(response_text: str) -> Dict[str, Any]:
        """
        Parse a NOAA PFDS point-frequency response.

        The NOAA endpoint returns JavaScript-style assignments such as
        ``quantiles = [['0.398', ...]];`` rather than JSON.
        """
        assignments: Dict[str, Any] = {}
        pattern = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?);\s*$", re.MULTILINE)
        for match in pattern.finditer(response_text):
            key = match.group(1)
            raw_value = match.group(2)
            assignments[key] = Atlas14Storm._parse_pfds_assignment_value(raw_value)

        for table_name in ("quantiles", "upper", "lower"):
            raw_table = assignments.get(table_name)
            if raw_table is None:
                continue
            assignments[table_name] = [
                [float(value) for value in row]
                for row in raw_table
            ]

        latitude = assignments.get("lat")
        longitude = assignments.get("lon")
        assignments["latitude"] = float(latitude) if latitude is not None else None
        assignments["longitude"] = float(longitude) if longitude is not None else None

        quantiles = assignments.get("quantiles")
        if quantiles is not None and len(quantiles) != len(Atlas14Storm.PFDS_DURATION_LABELS):
            raise ValueError(
                "Unexpected NOAA PFDS response shape: "
                f"expected {len(Atlas14Storm.PFDS_DURATION_LABELS)} duration rows, "
                f"received {len(quantiles)}"
            )

        return assignments

    @staticmethod
    def _normalize_return_period_column(
        depth_table: pd.DataFrame,
        ari_years: int,
    ) -> Union[int, str]:
        """Resolve a return-period column from a depth table."""
        candidates: List[Union[int, str]] = [ari_years, str(ari_years)]
        for candidate in candidates:
            if candidate in depth_table.columns:
                return candidate
        raise ValueError(
            f"Return period {ari_years} years not found in depth table columns: "
            f"{list(depth_table.columns)}"
        )

    @staticmethod
    @log_call
    def build_depth_duration_table(parsed_response: Dict[str, Any]) -> pd.DataFrame:
        """Convert parsed PFDS quantiles into a duration-indexed DataFrame."""
        quantiles = parsed_response.get("quantiles")
        if quantiles is None:
            raise ValueError("Parsed PFDS response is missing 'quantiles'")

        table = pd.DataFrame(
            quantiles,
            columns=Atlas14Storm.PFDS_RETURN_PERIOD_YEARS,
        )
        table.insert(0, "duration_label", Atlas14Storm.PFDS_DURATION_LABELS)
        table.insert(1, "duration_minutes", Atlas14Storm.PFDS_DURATION_MINUTES)
        return table

    @staticmethod
    @log_call
    def get_point_frequency_estimates(
        latitude: float,
        longitude: float,
        series: str = "pds",
        units: str = "english",
        cache_dir: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """
        Fetch and parse a NOAA PFDS point frequency depth table.

        Args:
            latitude: Query latitude in decimal degrees
            longitude: Query longitude in decimal degrees
            series: NOAA series key, typically ``pds`` or ``ams``
            units: NOAA units key, typically ``english`` or ``metric``
            cache_dir: Optional raw-response cache directory

        Returns:
            Dictionary containing parsed NOAA metadata and a
            ``depth_duration_table`` DataFrame.
        """
        units = Atlas14Storm.normalize_depth_units(units)
        cache_dir = Atlas14Storm._normalize_cache_dir(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = Atlas14Storm._pfds_cache_file(latitude, longitude, series, units, cache_dir)

        if cache_file.exists():
            response_text = cache_file.read_text(encoding="utf-8")
        else:
            response = requests.get(
                Atlas14Storm.PFDS_POINT_ENDPOINT,
                params={
                    "lat": f"{latitude:.6f}",
                    "lon": f"{longitude:.6f}",
                    "type": "pf",
                    "data": "depth",
                    "units": units,
                    "series": series,
                },
                timeout=60,
            )
            response.raise_for_status()
            response_text = response.text
            cache_file.write_text(response_text, encoding="utf-8")

        parsed = Atlas14Storm.parse_pfds_response(response_text)
        depth_duration_table = Atlas14Storm.build_depth_duration_table(parsed)
        return {
            **parsed,
            "series": series,
            "units": units,
            "query_url": Atlas14Storm.PFDS_POINT_ENDPOINT,
            "depth_duration_table": depth_duration_table,
            "cache_file": cache_file,
        }

    @staticmethod
    @log_call
    def get_depth_duration_table(
        latitude: float,
        longitude: float,
        series: str = "pds",
        units: str = "english",
        cache_dir: Optional[Union[str, Path]] = None,
    ) -> pd.DataFrame:
        """Fetch a duration-indexed NOAA PFDS depth table."""
        result = Atlas14Storm.get_point_frequency_estimates(
            latitude=latitude,
            longitude=longitude,
            series=series,
            units=units,
            cache_dir=cache_dir,
        )
        return result["depth_duration_table"].copy()

    @staticmethod
    @log_call
    def build_frequency_storm_depths(
        depth_table: pd.DataFrame,
        ari_years: int = 100,
        durations_min: Optional[List[int]] = None,
    ) -> List[float]:
        """
        Build the standard HMS frequency-storm depth vector from a PFDS table.

        Returns cumulative depth values in the canonical HMS/TP-40 ordering:
        5, 15, 30, 60, 120, 180, 360, 1440 minutes by default.
        """
        if durations_min is None:
            durations_min = list(Atlas14Storm.FREQUENCY_STORM_DURATIONS_MIN)

        if "duration_minutes" not in depth_table.columns:
            raise ValueError("Depth table must include a 'duration_minutes' column")

        return_period_column = Atlas14Storm._normalize_return_period_column(depth_table, ari_years)
        indexed = depth_table.set_index("duration_minutes")

        missing_durations = [duration for duration in durations_min if duration not in indexed.index]
        if missing_durations:
            raise ValueError(
                "Depth table is missing required durations for HMS frequency storms: "
                f"{missing_durations}"
            )

        return [float(indexed.loc[duration, return_period_column]) for duration in durations_min]

    @staticmethod
    @log_call
    def get_frequency_storm_depths(
        latitude: float,
        longitude: float,
        ari_years: int = 100,
        series: str = "pds",
        units: str = "english",
        durations_min: Optional[List[int]] = None,
        cache_dir: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """Fetch NOAA point depths and return the standard HMS frequency-storm vector."""
        normalized_units = Atlas14Storm.normalize_depth_units(units)
        point_frequency = Atlas14Storm.get_point_frequency_estimates(
            latitude=latitude,
            longitude=longitude,
            series=series,
            units=normalized_units,
            cache_dir=cache_dir,
        )
        depth_table = point_frequency["depth_duration_table"]
        if durations_min is None:
            durations_min = list(Atlas14Storm.FREQUENCY_STORM_DURATIONS_MIN)
        depths = Atlas14Storm.build_frequency_storm_depths(
            depth_table=depth_table,
            ari_years=ari_years,
            durations_min=durations_min,
        )
        depths_inches = Atlas14Storm.convert_depths_to_inches(depths, normalized_units)

        return {
            "ari_years": int(ari_years),
            "durations_min": list(durations_min),
            "duration_labels": [
                Atlas14Storm.FREQUENCY_DURATION_LABEL_BY_MINUTES.get(duration, f"{duration}-min")
                for duration in durations_min
            ],
            "depths_inches": depths_inches,
            "depths_native_units": list(depths),
            "native_units": normalized_units,
            "depth_duration_table": depth_table.copy(),
            "point_frequency": point_frequency,
        }

    @staticmethod
    def _aep_to_probability_column(aep_percent: float) -> str:
        """
        Map AEP percentage to the legacy nearest probability column.

        This helper is kept for callers that intentionally want an AEP-derived
        temporal distribution probability. ``generate_hyetograph()`` does not
        apply this mapping automatically; it defaults to the median "50%"
        temporal distribution probability unless ``probability_column`` is
        provided.

        Args:
            aep_percent: Annual Exceedance Probability (0.2 to 50)

        Returns:
            Probability column name (e.g., "10%", "50%")
        """
        # Standard probabilities available
        standard_probs = [90, 80, 70, 60, 50, 40, 30, 20, 10]

        # Find nearest (Atlas 14 uses exceedance probability)
        # AEP 50% → use 50% column (median)
        # AEP 10% → use 10% column
        # AEP 1% → use 10% column (most extreme available)

        if aep_percent >= 50:
            return "50%"
        elif aep_percent >= 40:
            return "40%"
        elif aep_percent >= 30:
            return "30%"
        elif aep_percent >= 20:
            return "20%"
        else:
            return "10%"  # For rarer events (1%, 0.5%, 0.2%)

    @staticmethod
    @log_call
    def generate_hyetograph(
        total_depth_inches: float,
        state: str = "tx",
        region: int = 3,
        duration_hours: int = 24,
        aep_percent: float = 1.0,
        quartile: str = "All Cases",
        interval_minutes: int = 30,
        cache_dir: Optional[Path] = None,
        probability_column: str = "50%",
    ) -> pd.DataFrame:
        """
        Generate incremental precipitation hyetograph using Atlas 14 temporal distribution.

        This matches HEC-HMS "Hypothetical Storm" with "Specified Pattern" algorithm.

        Args:
            total_depth_inches: Total storm precipitation depth (from DDF table)
            state: Two-letter state code (e.g., "tx")
            region: Atlas 14 region number (e.g., 3 for Houston area)
            duration_hours: Storm duration in hours (default: 24)
                Supported: 6, 12, 24, 96 hours
                Note: 48h NOT available - use FrequencyStorm instead
            aep_percent: Annual Exceedance Probability percentage (default: 1.0
                for 100-yr). Retained for storm-event context and backward
                compatibility; it does not select the temporal distribution
                probability column.
            quartile: Quartile to use (default: "All Cases")
            interval_minutes: Output interval in minutes (default: 30)
            cache_dir: Optional cache directory
            probability_column: NOAA temporal distribution probability column to
                use (default: "50%"). The "50%" column is the median temporal
                pattern and is the standard design choice. Use non-median
                columns such as "10%" or "90%" only for agency guidance,
                project-specific requirements, or sensitivity analysis.

        Returns:
            pd.DataFrame with columns:
                - 'hour': Time in hours from storm start (float)
                    Values: [0.0, 0.5, 1.0, ...] for 30-min intervals
                - 'incremental_depth': Precipitation depth for this interval (inches, float)
                    Description: Rainfall that occurred during this time step
                - 'cumulative_depth': Cumulative precipitation depth (inches, float)
                    Description: Total rainfall from storm start to end of this interval
            Length = duration_hours * 60 / interval_minutes + 1 (includes
            t=0 sentinel); the final row is the storm duration in hours.

        Raises:
            ValueError: If duration_hours is 48 or not supported

        Example:
            >>> # 100-year, 24-hour storm for Houston, TX using the median
            >>> # Atlas 14 temporal distribution (17.9 inches total)
            >>> hyeto = Atlas14Storm.generate_hyetograph(
            ...     total_depth_inches=17.9,
            ...     state="tx",
            ...     region=3,
            ...     aep_percent=1.0,
            ...     probability_column="50%"
            ... )
            >>> print(hyeto.columns.tolist())
            ['hour', 'incremental_depth', 'cumulative_depth']
            >>> print(f"Total depth: {hyeto['cumulative_depth'].iloc[-1]:.3f} inches")
            Total depth: 17.900 inches
            >>>
            >>> # 6-hour storm
            >>> hyeto_6h = Atlas14Storm.generate_hyetograph(
            ...     total_depth_inches=8.0,
            ...     state="tx",
            ...     region=3,
            ...     duration_hours=6
            ... )
        """
        if probability_column not in Atlas14Storm.PROBABILITY_COLUMNS:
            raise ValueError(
                f"Probability column '{probability_column}' is not valid. "
                f"Available: {Atlas14Storm.PROBABILITY_COLUMNS}"
            )

        # Validation is done in load_temporal_distribution()
        # Load temporal distribution
        temporal_distributions = Atlas14Storm.load_temporal_distribution(
            state, region, duration_hours, cache_dir
        )

        # Select quartile
        if quartile not in temporal_distributions:
            raise ValueError(
                f"Quartile '{quartile}' not found. "
                f"Available: {list(temporal_distributions.keys())}"
            )

        temporal_df = temporal_distributions[quartile]

        # Select probability column
        if probability_column not in temporal_df.columns:
            raise ValueError(
                f"Probability column '{probability_column}' not found in temporal distribution. "
                f"Available: {list(temporal_df.columns)}"
            )

        # Get cumulative curve (0-100%)
        cumulative_percent = temporal_df[probability_column].values

        incremental = incremental_depths_from_cumulative_pattern(
            cumulative_percent,
            total_depth_inches=total_depth_inches,
            source_duration_min=duration_hours * 60,
            time_interval_min=interval_minutes,
            value_scale=100.0,
        )

        # Verify total depth matches (within rounding)
        total_check = incremental.sum()
        if abs(total_check - total_depth_inches) > 0.01:
            logger.warning(
                f"Total depth mismatch: {total_check:.3f} vs {total_depth_inches:.3f} inches"
            )

        logger.info(
            f"Generated hyetograph: {len(incremental)} intervals, "
            f"{total_check:.3f} inches total"
        )

        return build_hyetograph_frame(incremental, interval_minutes)

    @staticmethod
    @log_call
    def generate_hyetograph_from_ari(
        ari_years: int,
        total_depth_inches: float,
        state: str = "tx",
        region: int = 3,
        duration_hours: int = 24,
        quartile: str = "All Cases",
        cache_dir: Optional[Path] = None,
        probability_column: str = "50%",
    ) -> pd.DataFrame:
        """
        Generate hyetograph using Average Recurrence Interval.

        Convenience method that converts ARI (years) to AEP (%) while using the
        selected Atlas 14 temporal distribution probability column. The default
        "50%" column is the median temporal pattern.

        Args:
            ari_years: Average Recurrence Interval in years (e.g., 100 for 100-yr storm)
            total_depth_inches: Total storm depth
            state: Two-letter Atlas 14 state code
            region: Atlas 14 region number or named region token
            duration_hours: Storm duration in hours
            quartile: Temporal-distribution quartile to use
            cache_dir: Optional Atlas 14 temporal-distribution cache directory
            probability_column: NOAA temporal distribution probability column to
                use (default: "50%"). Use non-median columns only for agency
                guidance, project-specific requirements, or sensitivity analysis.

        Returns:
            pd.DataFrame with columns: ``hour``, ``incremental_depth``, and
            ``cumulative_depth``.

        Example:
            >>> # 100-year storm
            >>> hyeto = Atlas14Storm.generate_hyetograph_from_ari(
            ...     ari_years=100,
            ...     total_depth_inches=17.9,
            ...     state="tx",
            ...     region=3,
            ...     probability_column="50%"
            ... )
            >>> print(hyeto.columns.tolist())
            ['hour', 'incremental_depth', 'cumulative_depth']
        """
        # Convert ARI to AEP: AEP = 1/ARI * 100
        aep_percent = (1.0 / ari_years) * 100.0

        return Atlas14Storm.generate_hyetograph(
            total_depth_inches=total_depth_inches,
            state=state,
            region=region,
            duration_hours=duration_hours,
            aep_percent=aep_percent,
            quartile=quartile,
            cache_dir=cache_dir,
            probability_column=probability_column,
        )
