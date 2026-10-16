"""Vision Adapters package."""

from abi_coach.infrastructure.adapters.vision.capture import (
    CaptureConfig,
    CaptureRegion,
    ProcessedCapture,
    capture_screen,
)
from abi_coach.infrastructure.adapters.vision.windows_capture_adapter import WindowsScreenCaptureAdapter

__all__ = [
    "CaptureConfig",
    "CaptureRegion",
    "ProcessedCapture",
    "WindowsScreenCaptureAdapter",
    "capture_screen",
]

