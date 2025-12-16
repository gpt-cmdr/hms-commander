"""
Atlas14Downloader - Download NOAA Atlas 14 precipitation data

Adapts the ras-commander Atlas 14 download logic for HMS workflows.
Uses safe parsing with ast.literal_eval (no eval).

Source: ras_commander/precip/StormGenerator.py
"""

import ast
import requests
from typing import Dict, List, Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Atlas14Downloader:
    """
    Download NOAA Atlas 14 precipitation frequency estimates.

    Uses the NOAA HDSC API to retrieve point precipitation frequency
    estimates for a given location.

    Example:
        >>> downloader = Atlas14Downloader()
        >>> data = downloader.download_from_coordinates(
        ...     lat=31.4504,
        ...     lon=-83.5285,
        ...     data='depth',
        ...     units='english'
        ... )
        >>> print(data['depths']['1%']['24-hr'])  # 1% AEP, 24-hr depth
    """

    # NOAA Atlas 14 API endpoint
    NOAA_API_URL = "https://hdsc.nws.noaa.gov/cgi-bin/hdsc/new/cgi_readH5.py"

    # Standard durations (minutes)
    STANDARD_DURATIONS = [
        5, 10, 15, 30,              # Sub-hourly
        60, 120, 180,               # 1-3 hours
        360, 720, 1440,             # 6-24 hours
        2880, 4320, 5760, 7200,     # 2-5 days
        8640, 10080, 20160, 43200   # 6-30 days
    ]

    # Standard return periods (years) → AEP mapping
    RETURN_PERIODS = {
        1: '50%',      # 1-year = 50% AEP
        2: '20%',      # 2-year = 20% AEP
        5: '10%',      # 5-year = 10% AEP
        10: '4%',      # 10-year = 4% AEP (common approximation)
        25: '2%',      # 25-year = 2% AEP
        50: '1%',      # 50-year = 1% AEP
        100: '0.5%',   # 100-year = 0.5% AEP
        200: '0.2%',   # 200-year = 0.2% AEP
        500: '0.1%',   # 500-year = 0.1% AEP
        1000: '0.05%'  # 1000-year = 0.05% AEP
    }

    def __init__(self, timeout: int = 30):
        """
        Initialize Atlas 14 downloader.

        Args:
            timeout: Request timeout in seconds (default 30)
        """
        self.timeout = timeout

    def download_from_coordinates(
        self,
        lat: float,
        lon: float,
        data: str = 'depth',
        units: str = 'english',
        series: str = 'pds'
    ) -> Dict[str, any]:
        """
        Download Atlas 14 data for a specific location.

        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            data: Data type - 'depth', 'upper', or 'lower'
                  - 'depth': Point estimate
                  - 'upper': Upper 90% confidence interval
                  - 'lower': Lower 90% confidence interval
            units: 'english' (inches) or 'metric' (mm)
            series: 'pds' (partial duration series) or 'ams' (annual maximum series)

        Returns:
            Dictionary with structure:
            {
                'location': {'lat': 31.45, 'lon': -83.53},
                'units': 'inches',
                'series': 'pds',
                'data_type': 'depth',
                'return_periods': [1, 2, 5, 10, 25, 50, 100, 200, 500, 1000],
                'aep_labels': ['50%', '20%', '10%', ...],
                'durations': [5, 10, 15, 30, 60, ...],  # minutes
                'depths': {
                    '50%': {5: 0.42, 10: 0.65, ..., '24-hr': 3.2, ...},
                    '20%': {5: 0.58, 10: 0.89, ..., '24-hr': 4.5, ...},
                    '10%': {...},
                    '4%': {...},
                    '2%': {...},
                    '1%': {...},
                    ...
                }
            }

        Raises:
            ValueError: If coordinates are invalid or API returns error
            requests.RequestException: If API request fails

        Example:
            >>> downloader = Atlas14Downloader()
            >>> data = downloader.download_from_coordinates(31.45, -83.53)
            >>> depth_24hr = data['depths']['1%']['24-hr']
            >>> print(f"100-year, 24-hr depth: {depth_24hr} inches")
        """
        # Validate coordinates
        if not (-90 <= lat <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, got {lat}")
        if not (-180 <= lon <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, got {lon}")

        # Build API request parameters
        params = {
            'lat': lat,
            'lon': lon,
            'data': data,
            'units': units,
            'series': series
        }

        logger.info(f"Downloading Atlas 14 data for ({lat}, {lon})...")

        try:
            # Make API request
            response = requests.get(
                self.NOAA_API_URL,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

            # Parse response - NOAA API returns JavaScript, not Python dict
            raw_text = response.text.strip()

            # Parse JavaScript response using regex
            try:
                data_dict = self._parse_javascript_response(raw_text)
            except (ValueError, SyntaxError) as e:
                logger.error(f"Failed to parse API response: {e}")
                logger.debug(f"Response text: {raw_text[:500]}...")
                raise ValueError(f"Could not parse API response: {e}")

            # Process and structure the data
            result = self._process_api_response(
                data_dict,
                lat=lat,
                lon=lon,
                data_type=data,
                units=units,
                series=series
            )

            logger.info(f"Successfully downloaded Atlas 14 data")
            logger.debug(f"Return periods: {result['return_periods']}")
            logger.debug(f"Durations: {len(result['durations'])} values")

            return result

        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise

    def _parse_javascript_response(self, raw_text: str) -> Dict:
        """
        Parse JavaScript response from NOAA API.

        The NOAA API returns JavaScript code like:
            quantiles = [['0.397', '0.458', ...], ...];
            upper = [['0.498', ...], ...];
            lower = [['0.309', ...], ...];

        Args:
            raw_text: Raw JavaScript response from API

        Returns:
            Dictionary with 'quantiles', 'upper', 'lower' arrays

        Raises:
            ValueError: If parsing fails
        """
        import re
        import json

        result = {}

        # Extract quantiles array
        match = re.search(r'quantiles\s*=\s*(\[\[.*?\]\]);', raw_text, re.DOTALL)
        if match:
            js_array = match.group(1)
            # Convert JavaScript array to JSON (single quotes to double quotes)
            json_array = js_array.replace("'", '"')
            result['quantiles'] = json.loads(json_array)

        # Extract upper bounds
        match = re.search(r'upper\s*=\s*(\[\[.*?\]\]);', raw_text, re.DOTALL)
        if match:
            js_array = match.group(1)
            json_array = js_array.replace("'", '"')
            result['upper'] = json.loads(json_array)

        # Extract lower bounds
        match = re.search(r'lower\s*=\s*(\[\[.*?\]\]);', raw_text, re.DOTALL)
        if match:
            js_array = match.group(1)
            json_array = js_array.replace("'", '"')
            result['lower'] = json.loads(json_array)

        if not result:
            raise ValueError("Could not extract data arrays from JavaScript response")

        return result

    def _process_api_response(
        self,
        data_dict: Dict,
        lat: float,
        lon: float,
        data_type: str,
        units: str,
        series: str
    ) -> Dict[str, any]:
        """
        Process raw API response into structured format.

        The NOAA API returns a nested dictionary structure that we
        reorganize for easier HMS workflow usage.

        Args:
            data_dict: Raw dictionary from API
            lat: Original latitude
            lon: Original longitude
            data_type: 'depth', 'upper', or 'lower'
            units: 'english' or 'metric'
            series: 'pds' or 'ams'

        Returns:
            Structured dictionary with organized depth data
        """
        # Determine unit label
        unit_label = 'inches' if units == 'english' else 'mm'

        # Extract return periods and durations from API response
        # data_dict now contains 'quantiles', 'upper', 'lower' arrays
        # Format: [duration_index][return_period_index]
        try:
            # Select which array to use based on data_type
            if data_type == 'upper':
                values_array = data_dict.get('upper', data_dict.get('quantiles', []))
            elif data_type == 'lower':
                values_array = data_dict.get('lower', data_dict.get('quantiles', []))
            else:  # 'depth' or default
                values_array = data_dict.get('quantiles', [])

            depths_by_aep = {}

            # Build AEP labels list
            aep_labels = list(self.RETURN_PERIODS.values())
            return_periods_list = list(self.RETURN_PERIODS.keys())

            # NOAA API structure: values_array[duration_idx][return_period_idx]
            # Return periods: [1, 2, 5, 10, 25, 50, 100, 200, 500, 1000]
            for rp_idx, (return_period, aep_label) in enumerate(self.RETURN_PERIODS.items()):
                depths_for_aep = {}

                # Process each duration
                for dur_idx, duration_min in enumerate(self.STANDARD_DURATIONS):
                    # Convert duration to label
                    if duration_min < 60:
                        duration_label = f"{duration_min}-min"
                    elif duration_min == 60:
                        duration_label = "1-hr"
                    elif duration_min < 1440:
                        hours = duration_min // 60
                        duration_label = f"{hours}-hr"
                    elif duration_min == 1440:
                        duration_label = "24-hr"
                    else:
                        days = duration_min // 1440
                        duration_label = f"{days}-day"

                    # Extract value from array if available
                    if dur_idx < len(values_array) and rp_idx < len(values_array[dur_idx]):
                        depth_value = float(values_array[dur_idx][rp_idx])
                        depths_for_aep[duration_label] = depth_value
                        depths_for_aep[duration_min] = depth_value  # Also store by minutes

                if depths_for_aep:
                    depths_by_aep[aep_label] = depths_for_aep

            # Build structured result
            result = {
                'location': {'lat': lat, 'lon': lon},
                'units': unit_label,
                'series': series,
                'data_type': data_type,
                'return_periods': list(self.RETURN_PERIODS.keys()),
                'aep_labels': aep_labels,
                'durations': self.STANDARD_DURATIONS,
                'depths': depths_by_aep
            }

            return result

        except Exception as e:
            logger.error(f"Error processing API response: {e}")
            logger.debug(f"Data dict keys: {data_dict.keys()}")
            raise ValueError(f"Could not process API response structure: {e}")

    def _extract_depth_from_dict(
        self,
        data_dict: Dict,
        duration_min: int,
        return_period: int
    ) -> Optional[float]:
        """
        Extract depth value from nested API dictionary.

        The NOAA API response format can vary. This method tries
        multiple access patterns to find the depth value.

        Args:
            data_dict: Raw API response dictionary
            duration_min: Duration in minutes
            return_period: Return period in years

        Returns:
            Depth value or None if not found
        """
        # Try different access patterns
        patterns = [
            # Pattern 1: data_dict[duration][return_period]
            lambda: data_dict.get(str(duration_min), {}).get(str(return_period)),
            lambda: data_dict.get(duration_min, {}).get(return_period),

            # Pattern 2: data_dict[return_period][duration]
            lambda: data_dict.get(str(return_period), {}).get(str(duration_min)),
            lambda: data_dict.get(return_period, {}).get(duration_min),

            # Pattern 3: Flattened with compound keys
            lambda: data_dict.get(f"{duration_min}_{return_period}"),
            lambda: data_dict.get(f"{return_period}_{duration_min}"),
        ]

        for pattern in patterns:
            try:
                value = pattern()
                if value is not None:
                    return float(value)
            except (KeyError, TypeError, ValueError):
                continue

        return None

    def get_available_aeps(self) -> List[str]:
        """
        Get list of available AEP labels.

        Returns:
            List of AEP labels (e.g., ['50%', '20%', '10%', ...])
        """
        return list(self.RETURN_PERIODS.values())

    def get_available_durations(self) -> List[int]:
        """
        Get list of available durations in minutes.

        Returns:
            List of durations in minutes
        """
        return self.STANDARD_DURATIONS.copy()

    def aep_to_return_period(self, aep: str) -> Optional[int]:
        """
        Convert AEP label to return period in years.

        Args:
            aep: AEP label (e.g., '1%', '0.5%')

        Returns:
            Return period in years or None if not found

        Example:
            >>> downloader = Atlas14Downloader()
            >>> downloader.aep_to_return_period('1%')
            100
        """
        for rp, aep_label in self.RETURN_PERIODS.items():
            if aep_label == aep:
                return rp
        return None

    def return_period_to_aep(self, return_period: int) -> Optional[str]:
        """
        Convert return period to AEP label.

        Args:
            return_period: Return period in years

        Returns:
            AEP label or None if not found

        Example:
            >>> downloader = Atlas14Downloader()
            >>> downloader.return_period_to_aep(100)
            '1%'
        """
        return self.RETURN_PERIODS.get(return_period)
