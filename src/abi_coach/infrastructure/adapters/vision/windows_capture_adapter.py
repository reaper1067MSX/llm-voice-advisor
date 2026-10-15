"""Screen Capture Adapter implementing ScreenCapturePort (Infrastructure Vision)."""

from typing import Optional
from abi_coach.core.vision.capture import CaptureConfig, capture_screen
from abi_coach.domain.common.errors import DomainError
from abi_coach.domain.common.result import Result, fail, ok
from abi_coach.domain.ports.vision_port import ScreenCapturePort, ScreenCaptureResultDTO


class WindowsScreenCaptureAdapter(ScreenCapturePort):
    """Hexagonal Adapter wrapping dxcam / mss with Lanczos downscaling."""

    def __init__(self, config: CaptureConfig):
        self.config = config

    def capture(self) -> Result[ScreenCaptureResultDTO, DomainError]:
        try:
            res = capture_screen(self.config)
            dto = ScreenCaptureResultDTO(
                full_image_bytes=res.full_image_bytes,
                crop_bytes=res.crop_bytes,
                original_size=res.original_size,
                processed_size=res.processed_size,
                capture_time_ms=res.capture_time_ms,
                total_time_ms=res.total_time_ms,
            )
            return ok(dto)
        except Exception as e:
            return fail(
                DomainError(
                    code="SCREEN_CAPTURE_ERROR",
                    message=f"Fallo al capturar pantalla: {e}",
                    spoken_fallback="No pude capturar la pantalla del juego.",
                )
            )
