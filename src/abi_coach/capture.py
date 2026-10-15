"""Backward compatibility shim for abi_coach.capture."""

from abi_coach.core.vision.capture import CaptureConfig, CaptureRegion, ProcessedCapture, capture_screen

__all__ = ["CaptureConfig", "CaptureRegion", "ProcessedCapture", "capture_screen"]
