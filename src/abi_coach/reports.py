"""HTML Report generation module for ABI Coach.

Generates dark-themed, game-styled HTML reports with charts (Chart.js) and tables,
opening them in the user's browser (ideally placed on the secondary monitor).
"""

from pathlib import Path
import time
from typing import Any, Callable, Optional
import webbrowser


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - ABI Coach</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-primary: #0f1115;
            --bg-secondary: #181b22;
            --bg-card: #20242e;
            --accent: #f59e0b;
            --accent-glow: rgba(245, 158, 11, 0.2);
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --border: #2e3542;
            --tier1: #9ca3af;
            --tier2: #34d399;
            --tier3: #60a5fa;
            --tier4: #a78bfa;
            --tier5: #f472b6;
            --tier6: #fbbf24;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            background-color: var(--bg-primary);
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            padding: 24px;
            line-height: 1.5;
        }}
        .header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 2px solid var(--border);
            padding-bottom: 16px;
            margin-bottom: 24px;
        }}
        .header h1 {{
            font-size: 1.6rem;
            color: var(--accent);
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .badge {{
            background-color: var(--accent-glow);
            border: 1px solid var(--accent);
            color: var(--accent);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
        }}
        .timestamp {{
            font-size: 0.85rem;
            color: var(--text-secondary);
        }}
        .card {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }}
        .card h2 {{
            font-size: 1.2rem;
            margin-bottom: 14px;
            color: var(--text-primary);
            border-left: 4px solid var(--accent);
            padding-left: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            background-color: var(--bg-card);
            border-radius: 8px;
            overflow: hidden;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{
            background-color: rgba(245, 158, 11, 0.1);
            color: var(--accent);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.5px;
        }}
        tr:hover {{
            background-color: rgba(255, 255, 255, 0.03);
        }}
        .chart-container {{
            position: relative;
            height: 340px;
            width: 100%;
            margin: 16px 0;
        }}
        .footer {{
            margin-top: 40px;
            text-align: center;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1><span>🎯 ABI Coach</span> {title}</h1>
        <div>
            <span class="badge">Arena Breakout: Infinite</span>
            <span class="timestamp">{timestamp}</span>
        </div>
    </div>

    <div class="content">
        {content}
    </div>

    <div class="footer">
        Generado en vivo por <strong>ABI Voice Coach</strong> • Análisis táctico y optimización de Koens
    </div>
</body>
</html>
"""


from concurrent.futures import ThreadPoolExecutor
import ctypes
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Callable, List, Optional, Tuple
import webbrowser


def _find_chrome_path() -> Optional[str]:
    """Locate Google Chrome executable on Windows."""
    candidates = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def _get_secondary_monitor_bounds() -> Optional[Tuple[int, int, int, int]]:
    """Get the working area bounds (x, y, w, h) of the secondary monitor if present."""
    if os.name != "nt":
        return None
    try:
        user32 = ctypes.windll.user32

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("rcMonitor", ctypes.c_long * 4),
                ("rcWork", ctypes.c_long * 4),
                ("dwFlags", ctypes.c_ulong),
            ]

        secondary_bounds = None

        def monitor_cb(hmon, hdc, lprect, lparam):
            nonlocal secondary_bounds
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                is_primary = bool(mi.dwFlags & 1)
                if not is_primary:
                    x = mi.rcWork[0]
                    y = mi.rcWork[1]
                    w = mi.rcWork[2] - mi.rcWork[0]
                    h = mi.rcWork[3] - mi.rcWork[1]
                    secondary_bounds = (x, y, w, h)
            return True

        MONITORENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_long * 4),
            ctypes.c_void_p,
        )
        user32.EnumDisplayMonitors(0, 0, MONITORENUMPROC(monitor_cb), 0)
        return secondary_bounds
    except Exception:
        return None


def _bring_chrome_to_front_worker() -> None:
    """Runs in clean thread to attach to user desktop, unminimize, and maximize Chrome on DISPLAY2 without yellow flashing."""
    if os.name != "nt":
        return
    try:
        user32 = ctypes.windll.user32
        desk = user32.OpenInputDesktop(0, False, 0x01FF)
        if desk:
            user32.SetThreadDesktop(desk)

        # Brief delay to allow Chrome to process the new tab IPC
        time.sleep(0.4)

        chrome_hwnds = []

        def enum_cb(hwnd, lparam):
            cls_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls_buf, 256)
            if cls_buf.value == "Chrome_WidgetWin_1" and user32.IsWindowVisible(hwnd):
                title_buf = ctypes.create_unicode_buffer(256)
                user32.GetWindowTextW(hwnd, title_buf, 256)
                chrome_hwnds.append((hwnd, title_buf.value))
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

        if not chrome_hwnds:
            return

        target_hwnd = chrome_hwnds[0][0]

        # 1. Check if already positioned on secondary monitor (x < 0)
        rect = (ctypes.c_long * 4)()
        user32.GetWindowRect(target_hwnd, rect)
        current_x = rect[0]

        sec_bounds = _get_secondary_monitor_bounds()
        already_on_sec = (sec_bounds is not None and current_x < 0)

        # 2. Un-minimize if iconic
        if user32.IsIconic(target_hwnd):
            user32.ShowWindow(target_hwnd, 9)  # SW_RESTORE

        # 3. Position on secondary monitor ONLY if not already there
        if sec_bounds and not already_on_sec:
            sx, sy, sw, sh = sec_bounds
            user32.ShowWindow(target_hwnd, 9)  # SW_RESTORE
            user32.SetWindowPos(target_hwnd, 0, sx, sy, sw - 10, sh - 10, 0x0040)

        # Ensure maximized
        if not user32.IsZoomed(target_hwnd):
            user32.ShowWindow(target_hwnd, 3)  # SW_MAXIMIZE

        # 4. Bring to foreground without Windows taskbar yellow flashing:
        # Simulate an Alt keypress to grant SetForegroundWindow permission
        user32.keybd_event(0x12, 0, 0, 0)
        user32.keybd_event(0x12, 0, 2, 0)
        user32.SetForegroundWindow(target_hwnd)

        mon_label = "DISPLAY2 (Secundaria)" if sec_bounds else "Pantalla principal"
        print(f"🌐 [Google Chrome] Pestaña abierta y maximizada en {mon_label}.", flush=True)

    except Exception:
        pass


def open_and_maximize_in_chrome(file_path: str) -> None:
    """Open file in Google Chrome, un-minimize, move to secondary monitor, and maximize."""
    chrome_path = _find_chrome_path()
    if chrome_path:
        try:
            # Pass absolute Windows path directly to Chrome
            subprocess.Popen([chrome_path, file_path], shell=False)
            with ThreadPoolExecutor(max_workers=1) as ex:
                ex.submit(_bring_chrome_to_front_worker)
            return
        except Exception:
            pass

    # Fallback to default browser
    try:
        webbrowser.open(file_path)
    except Exception:
        pass


def create_html_report(
    title: str,
    html_body: str,
    output_dir: str = "reports",
    auto_open: bool = True,
    opener: Optional[Callable[[str], Any]] = None,
) -> Path:
    """Generate a styled HTML report and open it maximized in Google Chrome."""
    import unicodedata

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
    file_timestamp = int(time.time())
    ascii_title = unicodedata.normalize("NFKD", title).encode("ASCII", "ignore").decode("utf-8")
    safe_title = "".join(c if c.isalnum() else "_" for c in ascii_title).lower()[:30].strip("_")
    filename = f"report_{file_timestamp}_{safe_title}.html"
    file_path = out_path / filename

    full_html = HTML_TEMPLATE.format(
        title=title,
        content=html_body,
        timestamp=timestamp_str,
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    if auto_open:
        resolved_str = str(file_path.resolve())
        if opener is not None:
            try:
                opener(resolved_str)
            except Exception:
                pass
        else:
            open_and_maximize_in_chrome(resolved_str)

    return file_path
