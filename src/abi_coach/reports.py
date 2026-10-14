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


def create_html_report(
    title: str,
    html_body: str,
    output_dir: str = "reports",
    auto_open: bool = True,
    opener: Optional[Callable[[str], Any]] = None,
) -> Path:
    """Generate a styled HTML report and optionally open it in the default browser."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
    file_timestamp = int(time.time())
    safe_title = "".join(c if c.isalnum() else "_" for c in title).lower()[:30]
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
        open_func = opener or webbrowser.open
        try:
            open_func(str(file_path.resolve().as_uri()))
        except Exception:
            pass

    return file_path
