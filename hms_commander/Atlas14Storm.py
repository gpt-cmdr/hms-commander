"""
Atlas14Storm - Atlas 14 Hyetograph Generation for HEC-HMS

Generates precipitation hyetographs using NOAA Atlas 14 temporal distributions,
matching the algorithm used by HEC-HMS internally.

Algorithm:
    1. Download/load Atlas 14 temporal distribution (cumulative % vs time)
    2. Select appropriate quartile and probability
    3. Apply to total storm depth (from DDF table)
    4. Convert cumulative to incremental depths

This matches HEC-HMS "Hypothetical Storm" with "Specified Pattern" storm type.
"""

from pathlib import Path
from typing import Dict, Optional, Union, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
import requests

from .LoggingConfig import get_logger
from .Decorators import log_call

logger = get_logger(__name__)


@dataclass
class Atlas14Config:
    """Configuration for Atlas 14 temporal distribution."""
    state: str  # Two-letter state code (lowercase)
    region: int  # Atlas 14 region number
    duration: int  # Duration in hours

    @property
    def url(self) -> str:
        """Generate the NOAA temporal distribution URL."""
        return f"https://hdsc.nws.noaa.gov/pub/hdsc/data/{self.state}/{self.state}_{self.region}_{self.duration}h_temporal.csv"

    @property
    def region_code(self) -> str:
        """Generate region identifier (e.g., TX_R3)."""
        return f"{self.state.upper()}_R{self.region}"


class Atlas14Storm:
    """
    Static class for generating Atlas 14 hyetographs.

    Implements the same algorithm as HEC-HMS "Hypothetical Storm" with
    "Specified Pattern" storm type.

    All methods are static - no instantiation required.

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
        ...     quartile="All Cases"
        ... )
        >>> print(f"Generated {len(hyetograph)} time steps")
        >>> print(f"Total depth: {hyetograph.sum():.3f} inches")
    """

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

    @staticmethod
    @log_call
    def download_temporal_csv(
        config: Atlas14Config,
        cache_dir: Optional[Path] = None
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
        if cache_dir:
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
        if cache_dir:
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

        logger.info(f"Parsed {len(result)} quartile tables with {len(df)} time steps each")
        return result

    @staticmethod
    @log_call
    def load_temporal_distribution(
        state: str,
        region: int,
        duration_hours: int = 24,
        cache_dir: Optional[Path] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Load Atlas 14 temporal distribution with caching.

        Args:
            state: Two-letter state code (lowercase, e.g., "tx")
            region: Atlas 14 region number
            duration_hours: Storm duration in hours (default: 24)
            cache_dir: Optional cache directory (default: ~/.hms-commander/atlas14/)

        Returns:
            Dictionary mapping quartile names to temporal distribution DataFrames
        """
        # Check memory cache
        cache_key = f"{state}_{region}_{duration_hours}h"
        if cache_key in Atlas14Storm._temporal_cache:
            logger.info(f"Using cached temporal distribution: {cache_key}")
            return Atlas14Storm._temporal_cache[cache_key]

        # Default cache directory
        if cache_dir is None:
            cache_dir = Path.home() / ".hms-commander" / "atlas14"

        # Download and parse
        config = Atlas14Config(state=state, region=region, duration=duration_hours)
        csv_content = Atlas14Storm.download_temporal_csv(config, cache_dir)
        temporal_distributions = Atlas14Storm.parse_temporal_csv(csv_content)

        # Cache in memory
        Atlas14Storm._temporal_cache[cache_key] = temporal_distributions

        return temporal_distributions

    @staticmethod
    def _aep_to_probability_column(aep_percent: float) -> str:
        """
        Map AEP percentage to nearest probability column.

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
        cache_dir: Optional[Path] = None
    ) -> np.ndarray:
        """
        Generate incremental precipitation hyetograph using Atlas 14 temporal distribution.

        This matches HEC-HMS "Hypothetical Storm" with "Specified Pattern" algorithm.

        Args:
            total_depth_inches: Total storm precipitation depth (from DDF table)
            state: Two-letter state code (e.g., "tx")
            region: Atlas 14 region number (e.g., 3 for Houston area)
            duration_hours: Storm duration in hours (default: 24)
            aep_percent: Annual Exceedance Probability percentage (default: 1.0 for 100-yr)
            quartile: Quartile to use (default: "All Cases")
            interval_minutes: Output interval in minutes (default: 30)
            cache_dir: Optional cache directory

        Returns:
            numpy array of incremental precipitation depths (inches)
            Length = duration_hours * 60 / interval_minutes

        Example:
            >>> # 100-year, 24-hour storm for Houston, TX (17.9 inches total)
            >>> hyeto = Atlas14Storm.generate_hyetograph(
            ...     total_depth_inches=17.9,
            ...     state="tx",
            ...     region=3,
            ...     aep_percent=1.0
            ... )
            >>> print(f"Total depth: {hyeto.sum():.3f} inches")
        """
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
        prob_col = Atlas14Storm._aep_to_probability_column(aep_percent)

        if prob_col not in temporal_df.columns:
            raise ValueError(
                f"Probability '{prob_col}' not available. "
                f"Available: {list(temporal_df.columns)}"
            )

        # Get cumulative curve (0-100%)
        cumulative_percent = temporal_df[prob_col].values

        # Convert to cumulative depth
        cumulative_depth = cumulative_percent / 100.0 * total_depth_inches

        # Convert to incremental depth
        incremental = np.diff(cumulative_depth, prepend=0.0)

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

        return incremental

    @staticmethod
    @log_call
    def generate_hyetograph_from_ari(
        ari_years: int,
        total_depth_inches: float,
        state: str = "tx",
        region: int = 3,
        duration_hours: int = 24,
        quartile: str = "All Cases",
        cache_dir: Optional[Path] = None
    ) -> np.ndarray:
        """
        Generate hyetograph using Average Recurrence Interval.

        Convenience method that converts ARI (years) to AEP (%).

        Args:
            ari_years: Average Recurrence Interval in years (e.g., 100 for 100-yr storm)
            total_depth_inches: Total storm depth
            (other args same as generate_hyetograph)

        Returns:
            numpy array of incremental precipitation depths

        Example:
            >>> # 100-year storm
            >>> hyeto = Atlas14Storm.generate_hyetograph_from_ari(
            ...     ari_years=100,
            ...     total_depth_inches=17.9,
            ...     state="tx",
            ...     region=3
            ... )
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
            cache_dir=cache_dir
        )
