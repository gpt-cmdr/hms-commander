"""Exceptions raised by HEC-HMS GUI helper utilities."""


class HmsGuiError(RuntimeError):
    """Base exception for GUI helper failures."""


class HmsGuiUnavailableError(HmsGuiError):
    """Raised when GUI helpers are unavailable in the current environment."""


class HmsGuiAttachError(HmsGuiError):
    """Raised when a GUI window cannot be attached or found."""


class HmsGuiActionError(HmsGuiError):
    """Raised when a GUI helper action cannot be completed."""
