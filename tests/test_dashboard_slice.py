"""Focused unit tests for dashboard reporting slice and facade."""

from pathlib import Path
import pytest

from abi_coach.application.slices.reporting.dashboard import (
    KnowledgeDashboardItem,
    MemoryDashboardItem,
    create_tactical_dashboard,
)


def test_create_tactical_dashboard_execution(tmp_path: Path):
    """Verify create_tactical_dashboard creates file and invokes opener."""
    out_dir = tmp_path / "dashboards"

    typed_mems = [MemoryDashboardItem(title="FAL Setup", content="4x Scope", pinned=True)]
    typed_know = [KnowledgeDashboardItem(title="Bala 7.62x51mm M80", tier=4, penetration=44, damage=76)]

    path1 = create_tactical_dashboard(
        memory_items=typed_mems,
        knowledge_items=typed_know,
        game="abi",
        output_dir=str(out_dir),
        auto_open=False,
    )
    assert path1.exists()
    content1 = path1.read_text(encoding="utf-8")
    assert "Dashboard Táctico - ABI" in content1
    assert "FAL Setup" in content1
    assert "Bala 7.62x51mm M80" in content1

    opened = []
    path2 = create_tactical_dashboard(
        memory_items=[{"title": "Dict Memory", "content": "From Dict"}],
        knowledge_items=[{"title": "Dict Ammo", "tier": 3}],
        game="abi",
        output_dir=str(out_dir / "sub"),
        auto_open=True,
        opener=lambda p: opened.append(p),
    )
    assert path2.exists()
    assert len(opened) == 1


def test_dashboard_facade_cleanliness():
    """Verify dashboard.py is clean facade with zero HTML tags and zero semicolons."""
    dashboard_path = Path("src/abi_coach/application/slices/reporting/dashboard.py")
    assert dashboard_path.exists()
    lines = dashboard_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 100

    code = "\n".join(lines)
    for tag in ["<div", "<table", "<tr", "<th", "<td", "<p", "<h2", "<h3", "<canvas", "<script"]:
        assert tag not in code, f"Found forbidden tag {tag} in dashboard.py"

    semicolons = [l for l in lines if ";" in l and not l.strip().startswith("#")]
    assert not semicolons
