"""Custom application exceptions for AMS.

Raise these instead of generic Python/Django exceptions so callers
can distinguish application-level errors from unexpected failures.
"""


class AMSNotFoundError(Exception):
    """Raised when a requested resource does not exist."""


class AMSValidationError(Exception):
    """Raised when business-rule validation fails."""


class AMSPermissionError(Exception):
    """Raised when the caller is not allowed to perform an operation."""
