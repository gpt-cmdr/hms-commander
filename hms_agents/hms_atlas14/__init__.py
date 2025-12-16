"""
HMS Atlas 14 Agent - Automate TP-40 to Atlas 14 precipitation updates

This agent provides tools for updating HEC-HMS models from deprecated TP-40
precipitation frequency estimates to current NOAA Atlas 14 data.

Follows the CLB Engineering LLM Forward Approach for GUI-verifiable,
non-destructive model modifications.

Usage:
    from hms_agents.HmsAtlas14 import Atlas14Downloader, Atlas14Converter

    # Download Atlas 14 data
    downloader = Atlas14Downloader()
    data = downloader.download_from_coordinates(lat=31.45, lon=-83.53)

    # Convert to HMS format
    converter = Atlas14Converter()
    depths = converter.generate_depth_values(
        atlas14_data=data,
        aep='1%',
        total_duration=1440,  # 24 hours
        time_interval=60      # 1-hour intervals
    )

See AGENT.md for complete workflow documentation.
"""

from .atlas14_downloader import Atlas14Downloader
from .atlas14_converter import Atlas14Converter

__all__ = [
    'Atlas14Downloader',
    'Atlas14Converter',
]

__version__ = '1.0.0'
__author__ = 'CLB Engineering'
