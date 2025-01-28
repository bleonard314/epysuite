# src/epysuite/__init__.py

"""EPYSuite: A Python interface for EPI Suite™."""

from .config import EPySuiteConfig, STPConfig
from .exceptions import (
    ConfigurationError,
    EPYSuiteError,
    ExecutionError,
    FileHandlingError,
    TimeoutError,
)
from .runner import EPySuiteRunner

__version__ = "0.1.0"
__author__ = "Ben Leonard"
__license__ = "MIT"

__all__ = [
    "EPySuiteRunner",
    "EPySuiteConfig",
    "STPConfig",
    "EPYSuiteError",
    "ConfigurationError",
    "ExecutionError",
    "TimeoutError",
    "FileHandlingError",
]