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


import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
from typing import Any, Callable, List, Optional, Tuple
import webbrowser


def _find_browser(preferred: str = "firefox") -> Tuple[str, Optional[str]]:
    """Locate browser executable on Windows based on user preference with smart fallback.
    
    Order for "firefox": Firefox -> Edge -> Chrome
    Order for "edge": Edge -> Firefox -> Chrome
    Order for "chrome": Chrome -> Firefox -> Edge
    """
    def check_firefox() -> Optional[str]:
        ff_cmd = shutil.which("firefox") or shutil.which("firefox.exe")
        if ff_cmd and os.path.isfile(ff_cmd):
            return ff_cmd
        candidates = [
            os.path.expandvars(r"%LocalAppData%\Microsoft\WindowsApps\firefox.exe"),
            os.path.expandvars(r"%ProgramFiles%\Mozilla Firefox\firefox.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return None

    def check_edge() -> Optional[str]:
        edge_cmd = shutil.which("msedge") or shutil.which("msedge.exe")
        if edge_cmd and os.path.isfile(edge_cmd):
            return edge_cmd
        candidates = [
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return None

    def check_chrome() -> Optional[str]:
        chrome_cmd = shutil.which("chrome") or shutil.which("chrome.exe")
        if chrome_cmd and os.path.isfile(chrome_cmd):
            return chrome_cmd
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return None

    pref = preferred.lower().strip()
    if pref == "edge":
        order = [("edge", check_edge), ("firefox", check_firefox), ("chrome", check_chrome)]
    elif pref == "chrome":
        order = [("chrome", check_chrome), ("firefox", check_firefox), ("edge", check_edge)]
    else:  # default "firefox"
        order = [("firefox", check_firefox), ("edge", check_edge), ("chrome", check_chrome)]

    for b_type, check_fn in order:
        path = check_fn()
        if path:
            return (b_type, path)

    return ("default", None)



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


def _get_process_name_for_hwnd(hwnd: int) -> str:
    """Safely get executable filename for a window handle."""
    if os.name != "nt":
        return ""
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        hproc = kernel32.OpenProcess(0x1000, False, pid.value)
        if hproc:
            buf = ctypes.create_unicode_buffer(1024)
            pname = ""
            if psapi.GetProcessImageFileNameW(hproc, buf, 1024):
                pname = buf.value.split("\\")[-1].lower()
            kernel32.CloseHandle(hproc)
            return pname
    except Exception:
        pass
    return ""


def _bring_browser_to_front_worker(browser_type: str, title_query: str = "") -> None:
    """Attach to desktop, unminimize, move to secondary monitor, and maximize without yellow taskbar flash."""
    if os.name != "nt":
        return
    try:
        user32 = ctypes.windll.user32
        desk = user32.OpenInputDesktop(0, False, 0x01FF)
        if desk:
            user32.SetThreadDesktop(desk)

        sec_bounds = _get_secondary_monitor_bounds()
        target_hwnd = None
        lower_query = title_query.lower().strip() if title_query else ""

        # Poll for up to 3.0s (15 iterations of 0.2s) to allow browser window creation
        for _ in range(15):
            time.sleep(0.2)
            matching_hwnds = []

            def enum_cb(hwnd, lparam):
                if not user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd):
                    return True

                cls_buf = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, cls_buf, 256)
                cls_val = cls_buf.value

                title_buf = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, title_buf, 512)
                w_title = title_buf.value.lower()

                if browser_type == "firefox":
                    if cls_val == "MozillaWindowClass" or (
                        "firefox" in w_title or (lower_query and lower_query in w_title)
                    ):
                        matching_hwnds.append(hwnd)
                elif browser_type in ("edge", "chrome"):
                    if cls_val == "Chrome_WidgetWin_1":
                        # Exclude IDEs, Discord, NVIDIA Broadcast
                        pname = _get_process_name_for_hwnd(hwnd)
                        expected = "msedge.exe" if browser_type == "edge" else "chrome.exe"
                        if pname == expected or expected.split(".")[0] in w_title or (lower_query and lower_query in w_title):
                            matching_hwnds.append(hwnd)
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

            if matching_hwnds:
                target_hwnd = matching_hwnds[0]
                break

        if not target_hwnd:
            return

        # 1. Un-minimize if iconic
        if user32.IsIconic(target_hwnd):
            user32.ShowWindow(target_hwnd, 9)  # SW_RESTORE

        # 2. Position on secondary monitor if detected
        if sec_bounds:
            sx, sy, sw, sh = sec_bounds
            user32.ShowWindow(target_hwnd, 9)  # SW_RESTORE
            user32.SetWindowPos(target_hwnd, 0, sx, sy, sw - 10, sh - 10, 0x0040)

        # 3. Ensure maximized
        user32.ShowWindow(target_hwnd, 3)  # SW_MAXIMIZE

        # 4. Bring to foreground without Windows taskbar yellow flashing:
        # Topmost flip forces window to top of the screen Z-order
        HWND_TOPMOST = -1
        HWND_NOTOPMOST = -2
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_SHOWWINDOW = 0x0040

        user32.SetWindowPos(target_hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        time.sleep(0.04)
        user32.SetWindowPos(target_hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        user32.BringWindowToTop(target_hwnd)

        # Bypass Windows 11 ForegroundLockTimeout via harmless Alt key
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shell.SendKeys("%")
        except Exception:
            user32.keybd_event(0x12, 0, 0, 0)
            user32.keybd_event(0x12, 0, 2, 0)

        user32.SetForegroundWindow(target_hwnd)
        user32.SwitchToThisWindow(target_hwnd, True)

        mon_label = "DISPLAY2 (Secundaria)" if sec_bounds else "Pantalla principal"
        browser_names = {
            "firefox": "Mozilla Firefox",
            "edge": "Microsoft Edge",
            "chrome": "Google Chrome",
        }
        b_label = browser_names.get(browser_type, browser_type.title())
        print(f"🌐 [{b_label}] Reporte visual abierto y maximizado en {mon_label}.", flush=True)

    except Exception:
        pass


def open_and_maximize_in_browser(file_path: str, title: str = "", preferred: str = "firefox") -> None:
    """Open file in preferred browser (Firefox > Edge > Chrome), position and maximize on secondary monitor."""
    browser_type, browser_path = _find_browser(preferred=preferred)

    if browser_path:
        try:
            si = subprocess.STARTUPINFO()
            if os.name == "nt":
                si.lpDesktop = r"WinSta0\Default"

            if browser_type == "firefox":
                args = [browser_path, "-new-window", file_path]
            else:
                args = [browser_path, "--new-window", file_path]

            subprocess.Popen(args, startupinfo=si, shell=False)

            # Fire and forget background worker for window raising
            t = threading.Thread(
                target=_bring_browser_to_front_worker,
                args=(browser_type, title),
                daemon=True,
            )
            t.start()
            return
        except Exception:
            pass

    # Fallback to default browser
    try:
        webbrowser.open(file_path)
    except Exception:
        pass


# Backwards compatibility alias
open_and_maximize_in_chrome = open_and_maximize_in_browser


def create_html_report(
    title: str,
    html_body: str,
    output_dir: str = "reports",
    auto_open: bool = True,
    opener: Optional[Callable[[str], Any]] = None,
    preferred_browser: str = "firefox",
) -> Path:
    """Generate a styled HTML report and open it maximized in the preferred browser."""
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
            open_and_maximize_in_browser(resolved_str, title=title, preferred=preferred_browser)

    return file_path

