"""Screen Capture and Report Display Outbound Ports (Domain Layer)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Protocol, Tuple
from abi_coach.domain.common.errors import DomainError
from abi_coach.domain.common.result import Result


@dataclass(frozen=True)
class ScreenCaptureResultDTO:
    """Carries captured desktop frame and regional crops."""

    full_image_bytes: bytes
    crop_bytes: Optional[Dict[str, bytes]] = None
    original_size: Tuple[int, int] = (2560, 1440)
    processed_size: Tuple[int, int] = (1920, 1080)
    capture_time_ms: float = 0.0
    total_time_ms: float = 0.0


class ScreenCapturePort(Protocol):
    """Port for non-blocking desktop frame capture and Lanczos downscaling."""

    def capture(self) -> Result[ScreenCaptureResultDTO, DomainError]:
        ...


class ReportDisplayPort(Protocol):
    """Port for compiling and presenting rich HTML dashboards on secondary display."""

    def display_report(
        self,
        title: str,
        html_body: str,
        auto_open: bool = True,
    ) -> Result[Path, DomainError]:
        ...
