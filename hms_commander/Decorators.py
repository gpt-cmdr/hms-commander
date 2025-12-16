"""
Decorators for hms-commander library.

Provides decorators for logging and input standardization for HMS file operations.
"""

from functools import wraps
from pathlib import Path
from typing import Union
import logging
import inspect

# Import log_call from LoggingConfig (single source of truth)
from .LoggingConfig import log_call

# Re-export for backwards compatibility
__all__ = ['log_call', 'standardize_path']


def standardize_path(file_type: str = 'hms'):
    """
    Decorator to standardize input paths for HMS file operations.

    This decorator processes various input types and converts them to a Path object
    pointing to the correct HMS file. It handles the following input types:
    - pathlib.Path objects
    - Strings (file paths)

    The decorator also manages HMS object references.

    Args:
        file_type (str): Specifies the type of HMS file to look for:
            - 'hms': Project file (.hms)
            - 'basin': Basin model file (.basin)
            - 'met': Meteorologic model file (.met)
            - 'control': Control specification file (.control)
            - 'gage': Time-series gage file (.gage)
            - 'grid': Grid file (.grid)
            - 'pdata': Paired data file (.pdata)
            - 'run': Run file (.run)

    Returns:
        A decorator that wraps the function to standardize its input to a Path object.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)

            # Check if the function expects a path parameter
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())

            # Handle both static method calls and regular function calls
            if args and isinstance(args[0], type):
                # Static method call, remove the class argument
                args = args[1:]

            # Get file_input from kwargs if provided with file_path key, or take first positional arg
            file_input = kwargs.pop('file_path', None) if 'file_path' in kwargs else (args[0] if args else None)

            # hms_object is always keyword-only, never in args
            hms_object = kwargs.pop('hms_object', None)

            # Get global hms object only if hms_object not provided
            # Use lazy import to avoid circular dependency during HmsPrj initialization
            hms_obj = hms_object
            if hms_obj is None:
                try:
                    from .HmsPrj import hms
                    hms_obj = hms
                except ImportError:
                    hms_obj = None

            # If no file_input provided, return the function unmodified
            if file_input is None:
                return func(*args, **kwargs)

            file_path = None

            # Clean and normalize string inputs
            if isinstance(file_input, str):
                # Clean the string (remove extra whitespace, normalize path separators)
                file_input = file_input.strip()

                # Check if it's a raw file path that exists
                try:
                    test_path = Path(file_input)
                    if test_path.is_file():
                        file_path = test_path
                        logger.info(f"Using file from direct string path: {file_path}")
                except Exception as e:
                    logger.debug(f"Error converting string to path: {str(e)}")

            # If a valid path wasn't created from string processing, continue with normal flow
            if file_path is None:
                # If file_input is already a Path and exists, use it directly
                if isinstance(file_input, Path) and file_input.is_file():
                    file_path = file_input
                    logger.info(f"Using existing Path object file: {file_path}")

                # Handle string inputs that are file names (not full paths) from HMS project
                elif isinstance(file_input, str) and hms_obj is not None:
                    try:
                        hms_obj.check_initialized()

                        # Look up file in appropriate DataFrame based on file_type
                        if file_type == 'basin':
                            matching = hms_obj.basin_df[hms_obj.basin_df['name'] == file_input]
                            if not matching.empty:
                                file_path = Path(matching.iloc[0]['full_path'])

                        elif file_type == 'met':
                            matching = hms_obj.met_df[hms_obj.met_df['name'] == file_input]
                            if not matching.empty:
                                file_path = Path(matching.iloc[0]['full_path'])

                        elif file_type == 'control':
                            matching = hms_obj.control_df[hms_obj.control_df['name'] == file_input]
                            if not matching.empty:
                                file_path = Path(matching.iloc[0]['full_path'])

                        elif file_type == 'run':
                            matching = hms_obj.run_df[hms_obj.run_df['name'] == file_input]
                            if not matching.empty:
                                file_path = Path(matching.iloc[0]['full_path'])

                    except Exception as e:
                        logger.debug(f"Error looking up file in HMS project: {str(e)}")

            # Final verification that the path exists
            if file_path is None or not file_path.exists():
                error_msg = f"HMS {file_type} file not found: {file_input}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)

            logger.info(f"Final validated file path: {file_path}")

            # Pass all original arguments and keywords, replacing file_input with standardized file_path
            # If the original input was positional, replace the first argument
            if args and 'file_path' not in kwargs:
                new_args = (file_path,) + args[1:]
            else:
                new_args = args
                kwargs['file_path'] = file_path

            return func(*new_args, **kwargs)

        return wrapper
    return decorator
