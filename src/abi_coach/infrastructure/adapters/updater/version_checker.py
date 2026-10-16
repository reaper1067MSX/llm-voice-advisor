"""GitHub Release version checker and terminal bulletin presenter."""

from dataclasses import dataclass
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.request

from abi_coach import __version__

DEFAULT_REPO = "reaper1067MSX/llm-voice-advisor"
DEFAULT_TIMEOUT_SEC = 1.5


@dataclass
class UpdateBulletin:
    """Structured release update information."""

    current_version: str
    latest_version: str
    release_title: str
    release_url: str
    published_at: str
    notes_summary: List[str]
    is_update_available: bool = True


def parse_semver(ver_str: str) -> Tuple[int, int, int]:
    """Parse a version string (e.g. 'v0.2.0', '1.3.4-rc1') into a 3-integer tuple.

    Returns (0, 0, 0) if the string cannot be parsed.
    """
    if not ver_str:
        return (0, 0, 0)

    clean = ver_str.strip().lstrip("vV")
    match = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?", clean)
    if not match:
        return (0, 0, 0)

    parts = [int(p) if p is not None else 0 for p in match.groups()]
    return (parts[0], parts[1], parts[2])


def is_newer_version(remote_version: str, current_version: str) -> bool:
    """Return True if remote_version is strictly newer than current_version."""
    remote_tuple = parse_semver(remote_version)
    current_tuple = parse_semver(current_version)
    return remote_tuple > current_tuple


def fetch_latest_release(
    repo: str = DEFAULT_REPO,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
) -> Optional[Dict[str, Any]]:
    """Fetch the latest release payload from GitHub Releases API without blocking the app.

    Returns None silently if there is no internet connection or GitHub times out.
    """
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "LLM-Voice-Advisor-Companion/1.0",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            if resp.status == 200:
                payload = json.loads(resp.read().decode("utf-8"))
                return payload
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
        # Fail silently: offline gaming, rate limits, or slow network must never impact gameplay
        return None
    return None


def extract_release_notes_summary(body_text: str, max_lines: int = 5) -> List[str]:
    """Extract clean bullet points or key lines from the release markdown body."""
    if not body_text:
        return ["Mejoras de rendimiento, estabilidad y nuevas funciones."]

    clean_lines: List[str] = []
    for line in body_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # If it's a bullet point
        if stripped.startswith(("- ", "* ", "• ")):
            clean_lines.append(stripped[2:].strip())
        elif len(stripped) > 5 and not stripped.startswith("```"):
            clean_lines.append(stripped)

        if len(clean_lines) >= max_lines:
            break

    return clean_lines or ["Actualizaciones de estabilidad y corrección de errores."]


def check_for_updates(
    current_version: str = __version__,
    repo: str = DEFAULT_REPO,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
) -> Optional[UpdateBulletin]:
    """Check GitHub for newer versions.

    Returns an UpdateBulletin ONLY if remote version > current version.
    Returns None if current version is up-to-date or if the network is unreachable.
    """
    payload = fetch_latest_release(repo=repo, timeout_sec=timeout_sec)
    if not payload:
        return None

    remote_tag = payload.get("tag_name", "")
    if not is_newer_version(remote_tag, current_version):
        return None

    title = payload.get("name") or remote_tag
    url = payload.get("html_url") or f"https://github.com/{repo}/releases/tag/{remote_tag}"
    published = payload.get("published_at", "")[:10]
    body = payload.get("body", "")
    notes = extract_release_notes_summary(body)

    return UpdateBulletin(
        current_version=current_version,
        latest_version=remote_tag,
        release_title=title,
        release_url=url,
        published_at=published,
        notes_summary=notes,
        is_update_available=True,
    )


def render_terminal_bulletin(bulletin: UpdateBulletin, width: int = 76) -> str:
    """Render a clean, high-visibility framed bulletin box for the Windows terminal."""
    needed_w = max(width, len(bulletin.release_url) + 8, len(bulletin.latest_version) + 50)
    width = min(needed_w, 90)
    inner_w = width - 4
    lines: List[str] = []

    lines.append("┌" + "─" * (width - 2) + "┐")

    # Header line
    hdr = f"🚀 BOLETÍN DE ACTUALIZACIÓN: NUEVA VERSIÓN {bulletin.latest_version} DISPONIBLE"
    if len(hdr) > inner_w:
        hdr = hdr[: inner_w - 3] + "..."
    lines.append(f"│  {hdr:<{inner_w}}  │")

    sub_hdr = f"(Tienes instalada la v{bulletin.current_version})"
    lines.append(f"│  {sub_hdr:<{inner_w}}  │")

    lines.append("├" + "─" * (width - 2) + "┤")

    # Notes section
    lines.append(f"│  {'Novedades del Release en GitHub:':<{inner_w}}  │")
    for note in bulletin.notes_summary:
        bullet_line = f" • {note}"
        if len(bullet_line) > inner_w:
            bullet_line = bullet_line[: inner_w - 3] + "..."
        lines.append(f"│  {bullet_line:<{inner_w}}  │")

    lines.append(f"│  {' ' * inner_w}  │")
    update_call = "👉 Para actualizar: Descarga el nuevo instalador desde:"
    lines.append(f"│  {update_call:<{inner_w}}  │")
    url_line = f"   {bulletin.release_url}"
    if len(url_line) > inner_w:
        url_line = url_line[: inner_w - 3] + "..."
    lines.append(f"│  {url_line:<{inner_w}}  │")

    lines.append("└" + "─" * (width - 2) + "┘")

    return "\n" + "\n".join(lines) + "\n"


def print_bulletin_if_available(
    current_version: str = __version__,
    repo: str = DEFAULT_REPO,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
) -> bool:
    """Check for updates and print the bulletin directly to stdout if available.

    Returns True if a bulletin was printed, False otherwise.
    """
    try:
        bulletin = check_for_updates(current_version=current_version, repo=repo, timeout_sec=timeout_sec)
        if bulletin:
            print(render_terminal_bulletin(bulletin), flush=True)
            return True
    except Exception:
        pass
    return False
