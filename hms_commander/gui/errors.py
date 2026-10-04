"""Exceptions raised by the HEC-HMS GUI control layer."""


class HmsGuiError(RuntimeError):
    """Base exception for GUI control failures."""


class HmsGuiUnavailableError(HmsGuiError):
    """Raised when GUI control is unavailable in the current environment."""


class HmsGuiAttachError(HmsGuiError):
    """Raised when the Java Access Bridge cannot attach to HMS."""


class HmsGuiActionError(HmsGuiError):
    """Raised when a GUI action cannot be completed."""
