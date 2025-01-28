# src/epysuite/exceptions.py

"""Custom exceptions for the EPYSuite package."""

class EPYSuiteError(Exception):
    """Base exception for EPY Suite errors."""
    pass

class ConfigurationError(EPYSuiteError):
    """Raised when there's an error in configuration."""
    pass

class ExecutionError(EPYSuiteError):
    """Raised when EPI Suite execution fails."""
    pass

class TimeoutError(EPYSuiteError):
    """Raised when EPI Suite execution times out."""
    pass

class FileHandlingError(EPYSuiteError):
    """Raised when there's an error handling input/output files."""
    pass