"""
HmsControl - Control Specification File Operations

This module provides static methods for reading and modifying HEC-HMS control
specification files (.control). It handles simulation time windows and intervals.

All methods are static and designed to be used without instantiation.
"""

import re
from pathlib import Path
from typing import Dict, Optional, Union
from datetime import datetime
import pandas as pd

from .LoggingConfig import get_logger
from .Decorators import log_call
from ._parsing import HmsFileParser
from ._constants import TIME_INTERVALS, HMS_DATE_FORMAT, HMS_TIME_FORMAT

logger = get_logger(__name__)


class HmsControl:
    """
    Control specification file operations (.control files).

    Manage simulation time windows and intervals for HEC-HMS simulations.

    All methods are static - no instantiation required.

    Example:
        >>> from hms_commander import HmsControl
        >>> time_window = HmsControl.get_time_window("model.control")
        >>> print(f"Start: {time_window['start_date']}")
        >>> HmsControl.set_time_window("model.control", start_date, end_date)
    """

    # Valid time interval strings (from _constants.TIME_INTERVALS)
    VALID_INTERVALS = list(TIME_INTERVALS.keys())

    @staticmethod
    @log_call
    def get_controls(
        hms_object=None
    ) -> pd.DataFrame:
        """
        Get all control specifications from the HMS project.

        Args:
            hms_object: HmsPrj instance (uses global hms if None)

        Returns:
            DataFrame with control specification information
        """
        from .HmsPrj import hms
        hms_obj = hms_object or hms

        if hms_obj is None or not hms_obj.initialized:
            raise RuntimeError("HMS project not initialized")

        return hms_obj.control_df.copy()

    @staticmethod
    @log_call
    def get_time_window(
        control_path: Union[str, Path],
        hms_object=None
    ) -> Dict[str, datetime]:
        """
        Get the time window from a control specification file.

        Args:
            control_path: Path to the .control file
            hms_object: Optional HmsPrj instance

        Returns:
            Dictionary with 'start_date' and 'end_date' as datetime objects

        Example:
            >>> window = HmsControl.get_time_window("Run1.control")
            >>> print(f"Start: {window['start_date']}")
            >>> print(f"End: {window['end_date']}")
        """
        control_path = Path(control_path)
        logger.info(f"Reading time window from: {control_path}")

        content = HmsControl._read_control_file(control_path)
        params = HmsControl._parse_control_params(content)

        start_date_str = params.get('Start Date', '')
        start_time_str = params.get('Start Time', '00:00')
        end_date_str = params.get('End Date', '')
        end_time_str = params.get('End Time', '00:00')

        try:
            start_datetime = datetime.strptime(
                f"{start_date_str} {start_time_str}",
                f"{HmsControl.HMS_DATE_FORMAT} {HmsControl.HMS_TIME_FORMAT}"
            )
            end_datetime = datetime.strptime(
                f"{end_date_str} {end_time_str}",
                f"{HmsControl.HMS_DATE_FORMAT} {HmsControl.HMS_TIME_FORMAT}"
            )
        except ValueError as e:
            raise ValueError(f"Error parsing date/time: {e}")

        return {
            'start_date': start_datetime,
            'end_date': end_datetime,
            'start_date_str': start_date_str,
            'start_time_str': start_time_str,
            'end_date_str': end_date_str,
            'end_time_str': end_time_str
        }

    @staticmethod
    @log_call
    def set_time_window(
        control_path: Union[str, Path],
        start_date: datetime,
        end_date: datetime,
        hms_object=None
    ) -> bool:
        """
        Set the time window in a control specification file.

        Args:
            control_path: Path to the .control file
            start_date: Simulation start date/time
            end_date: Simulation end date/time
            hms_object: Optional HmsPrj instance

        Returns:
            True if successful

        Example:
            >>> from datetime import datetime
            >>> start = datetime(2020, 1, 1, 0, 0)
            >>> end = datetime(2020, 1, 3, 0, 0)
            >>> HmsControl.set_time_window("Run1.control", start, end)
        """
        control_path = Path(control_path)
        logger.info(f"Setting time window in: {control_path}")

        content = HmsControl._read_control_file(control_path)

        # Format dates for HMS
        start_date_str = start_date.strftime(HmsControl.HMS_DATE_FORMAT)
        start_time_str = start_date.strftime(HmsControl.HMS_TIME_FORMAT)
        end_date_str = end_date.strftime(HmsControl.HMS_DATE_FORMAT)
        end_time_str = end_date.strftime(HmsControl.HMS_TIME_FORMAT)

        # Update parameters
        content = HmsControl._update_param(content, 'Start Date', start_date_str)
        content = HmsControl._update_param(content, 'Start Time', start_time_str)
        content = HmsControl._update_param(content, 'End Date', end_date_str)
        content = HmsControl._update_param(content, 'End Time', end_time_str)

        with open(control_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Time window set: {start_date_str} {start_time_str} to {end_date_str} {end_time_str}")
        return True

    @staticmethod
    @log_call
    def get_time_interval(
        control_path: Union[str, Path],
        hms_object=None
    ) -> str:
        """
        Get the time interval from a control specification file.

        Args:
            control_path: Path to the .control file
            hms_object: Optional HmsPrj instance

        Returns:
            Time interval string (e.g., "15 Minutes", "1 Hour")

        Example:
            >>> interval = HmsControl.get_time_interval("Run1.control")
            >>> print(f"Interval: {interval}")
        """
        control_path = Path(control_path)
        content = HmsControl._read_control_file(control_path)
        params = HmsControl._parse_control_params(content)

        interval = params.get('Time Interval', '')
        return interval

    @staticmethod
    @log_call
    def set_time_interval(
        control_path: Union[str, Path],
        interval: Union[str, int],
        hms_object=None
    ) -> bool:
        """
        Set the time interval in a control specification file.

        Args:
            control_path: Path to the .control file
            interval: Time interval - can be string (e.g., "15 Minutes") or
                     integer minutes (e.g., 15)
            hms_object: Optional HmsPrj instance

        Returns:
            True if successful

        Example:
            >>> HmsControl.set_time_interval("Run1.control", "15 Minutes")
            >>> HmsControl.set_time_interval("Run1.control", 30)  # 30 minutes
        """
        control_path = Path(control_path)

        # Convert integer to HMS interval string
        if isinstance(interval, int):
            interval = HmsControl._minutes_to_interval(interval)

        if interval not in HmsControl.VALID_INTERVALS:
            logger.warning(f"Non-standard interval: {interval}")

        content = HmsControl._read_control_file(control_path)
        content = HmsControl._update_param(content, 'Time Interval', interval)

        with open(control_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Time interval set to: {interval}")
        return True

    @staticmethod
    @log_call
    def get_control_info(
        control_path: Union[str, Path],
        hms_object=None
    ) -> Dict[str, str]:
        """
        Get all information from a control specification file.

        Args:
            control_path: Path to the .control file
            hms_object: Optional HmsPrj instance

        Returns:
            Dictionary with all control parameters
        """
        control_path = Path(control_path)
        content = HmsControl._read_control_file(control_path)
        params = HmsControl._parse_control_params(content)
        return params

    @staticmethod
    @log_call
    def clone_control(
        template_control: str,
        new_name: str,
        hms_object=None
    ) -> str:
        """
        Clone a control specification file with a new name.

        Args:
            template_control: Name or path of the template control file
            new_name: Name for the new control specification
            hms_object: Optional HmsPrj instance

        Returns:
            Path to the new control file

        Example:
            >>> new_path = HmsControl.clone_control("existing.control", "new_control")
        """
        template_path = Path(template_control)

        if not template_path.exists() and hms_object is not None:
            # Try to find it in the project
            matching = hms_object.control_df[
                hms_object.control_df['name'] == template_control
            ]
            if not matching.empty:
                template_path = Path(matching.iloc[0]['full_path'])

        if not template_path.exists():
            raise FileNotFoundError(f"Template control not found: {template_control}")

        content = HmsControl._read_control_file(template_path)

        # Update the control name in the content
        content = re.sub(
            r'^Control:\s*.*$',
            f'Control: {new_name}',
            content,
            flags=re.MULTILINE
        )

        # Create new file path
        new_path = template_path.parent / f"{new_name}.control"

        with open(new_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Cloned control to: {new_path}")
        return str(new_path)

    @staticmethod
    @log_call
    def create_control(
        control_path: Union[str, Path],
        control_name: str,
        start_date: datetime,
        end_date: datetime,
        time_interval: Union[str, int] = "15 Minutes",
        hms_object=None
    ) -> str:
        """
        Create a new control specification file.

        Args:
            control_path: Path for the new .control file
            control_name: Name of the control specification
            start_date: Simulation start date/time
            end_date: Simulation end date/time
            time_interval: Time interval (string or minutes)
            hms_object: Optional HmsPrj instance

        Returns:
            Path to the new control file

        Example:
            >>> from datetime import datetime
            >>> start = datetime(2020, 1, 1)
            >>> end = datetime(2020, 1, 3)
            >>> HmsControl.create_control("Run1.control", "Run 1", start, end, 15)
        """
        control_path = Path(control_path)

        # Convert integer to HMS interval string
        if isinstance(time_interval, int):
            time_interval = HmsControl._minutes_to_interval(time_interval)

        # Format dates
        start_date_str = start_date.strftime(HmsControl.HMS_DATE_FORMAT)
        start_time_str = start_date.strftime(HmsControl.HMS_TIME_FORMAT)
        end_date_str = end_date.strftime(HmsControl.HMS_DATE_FORMAT)
        end_time_str = end_date.strftime(HmsControl.HMS_TIME_FORMAT)

        content = f"""Control: {control_name}
     Description: Created by hms-commander
     Start Date: {start_date_str}
     Start Time: {start_time_str}
     End Date: {end_date_str}
     End Time: {end_time_str}
     Time Interval: {time_interval}
End:
"""

        with open(control_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Created control file: {control_path}")
        return str(control_path)

    # =========================================================================
    # Private helper methods
    # =========================================================================

    @staticmethod
    def _read_control_file(control_path: Path) -> str:
        """Read control file content with encoding fallback."""
        return HmsFileParser.read_file(control_path)

    @staticmethod
    def _parse_control_params(content: str) -> Dict[str, str]:
        """Parse control file into key-value pairs."""
        params = {}
        for line in content.splitlines():
            line = line.strip()
            if ':' in line and not line.startswith('Control:') and not line.startswith('End'):
                key, value = line.split(':', 1)
                params[key.strip()] = value.strip()
        return params

    @staticmethod
    def _update_param(content: str, param_name: str, new_value: str) -> str:
        """Update a parameter value in control file content."""
        updated, _ = HmsFileParser.update_parameter(content, param_name, new_value)
        return updated

    @staticmethod
    def _minutes_to_interval(minutes: int) -> str:
        """Convert minutes to HMS interval string."""
        if minutes < 60:
            if minutes == 1:
                return "1 Minute"
            return f"{minutes} Minutes"
        else:
            hours = minutes // 60
            if hours == 24:
                return "1 Day"
            elif hours == 1:
                return "1 Hour"
            return f"{hours} Hours"
