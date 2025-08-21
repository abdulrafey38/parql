"""
ParQL exception classes.

This module defines custom exceptions used throughout ParQL.
"""


class ParQLError(Exception):
    """Base exception class for ParQL errors."""
    pass


class ParQLDataError(ParQLError):
    """Exception raised for data-related errors."""
    pass


class ParQLConfigError(ParQLError):
    """Exception raised for configuration errors."""
    pass


class ParQLValidationError(ParQLError):
    """Exception raised for validation errors."""
    pass


class ParQLIOError(ParQLError):
    """Exception raised for I/O related errors."""
    pass


class ParQLQueryError(ParQLError):
    """Exception raised for query execution errors."""
    pass
