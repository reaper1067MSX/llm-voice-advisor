"""Screen capture module for ABI Coach.

Uses OS-level desktop capture (Windows GDI / Desktop Duplication) to avoid
touching the game process or triggering anti-cheat mechanisms.
"""

from dataclasses import dataclass
import ctypes
import io
import os
from pathlib import Path
import time
from typing import Dict, Optional, Tuple
import mss
from PIL import Image, ImageGrab

from abi_coach.config import CaptureConfig, CaptureRegion


@dataclass
class ProcessedCapture:
    full_image_bytes: bytes
    full_image_pil: Image.Image
    crop_bytes: Optional[Dict[str, bytes]]
    original_size: Tuple[int, int]
    processed_size: Tuple[int, int]
    capture_time_ms: float
    total_time_ms: float


_ACTIVE_DESKTOP_HANDLE = None


def _ensure_active_desktop() -> None:
    """Ensure current thread is attached to the active input desktop on Windows."""
    global _ACTIVE_DESKTOP_HANDLE
    try:
        user32 = ctypes.windll.user32
        if _ACTIVE_DESKTOP_HANDLE is None:
            desk = user32.OpenInputDesktop(0, False, 0x01FF)
            if desk:
                user32.SetThreadDesktop(desk)
                _ACTIVE_DESKTOP_HANDLE = desk
    except Exception:
        pass


def capture_screen(config: CaptureConfig) -> ProcessedCapture:
    """Capture one frame from the specified monitor and optimize for vision LLM."""
    start_time = time.perf_counter()
    _ensure_active_desktop()

    pil_img: Optional[Image.Image] = None

    # Try MSS first
    try:
        with mss.MSS() as sct:
            monitors = sct.monitors
            idx = config.monitor_index
            if idx >= len(monitors):
                idx = 1 if len(monitors) > 1 else 0
            target_monitor = monitors[idx]
            sct_img = sct.grab(target_monitor)
            pil_img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
    except Exception as e:
        import traceback
        traceback.print_exc()
        pil_img = None

    # Fallback to ImageGrab
    if pil_img is None:
        try:
            pil_img = ImageGrab.grab(all_screens=False)
        except Exception as e:
            raise RuntimeError(f"No se pudo capturar la pantalla: {e}") from e

    capture_duration_ms = (time.perf_counter() - start_time) * 1000
    orig_w, orig_h = pil_img.size

    # Extract optional high-resolution crops BEFORE downscaling
    crops_dict: Optional[Dict[str, bytes]] = None
    if config.regions:
        crops_dict = {}
        for region_name, reg in config.regions.items():
            # Validate bounds
            box = (
                max(0, reg.x),
                max(0, reg.y),
                min(orig_w, reg.x + reg.width),
                min(orig_h, reg.y + reg.height),
            )
            if box[2] > box[0] and box[3] > box[1]:
                cropped = pil_img.crop(box)
                buf = io.BytesIO()
                cropped.save(buf, format="JPEG", quality=config.jpeg_quality)
                crops_dict[region_name] = buf.getvalue()

    # Downscale full frame if larger than configured limits (e.g. 2560x1440 -> 1920x1080)
    resized_img = pil_img
    if orig_w > config.downscale_width or orig_h > config.downscale_height:
        # Calculate aspect-ratio preserving size
        ratio = min(config.downscale_width / orig_w, config.downscale_height / orig_h)
        new_size = (int(orig_w * ratio), int(orig_h * ratio))
        resized_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)

    # Encode full frame to JPEG
    full_buf = io.BytesIO()
    resized_img.save(full_buf, format="JPEG", quality=config.jpeg_quality)
    full_bytes = full_buf.getvalue()

    # Optional save to disk for debugging
    if config.save_captures:
        try:
            out_dir = Path(config.capture_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            timestamp = int(time.time())
            out_path = out_dir / f"capture_{timestamp}.jpg"
            with open(out_path, "wb") as f:
                f.write(full_bytes)
        except Exception:
            pass

    total_duration_ms = (time.perf_counter() - start_time) * 1000

    return ProcessedCapture(
        full_image_bytes=full_bytes,
        full_image_pil=resized_img,
        crop_bytes=crops_dict,
        original_size=(orig_w, orig_h),
        processed_size=resized_img.size,
        capture_time_ms=capture_duration_ms,
        total_time_ms=total_duration_ms,
    )
