"""Focused unit tests for DashboardPresenter HTML rendering and escaping."""

import pytest

from abi_coach.domain.entities.dashboard_records import (
    KnowledgeDashboardItem,
    MemoryDashboardItem,
)
from abi_coach.infrastructure.presentation.dashboard_presenter import DashboardPresenter


def test_dashboard_presenter_memory_column():
    """Verify DashboardPresenter formats memory cards, escaping, and empty state."""
    empty_html = DashboardPresenter.render_memory_column([])
    assert "Sin memorias guardadas aún." in empty_html

    items = [
        MemoryDashboardItem(title="Loadout <Danger>", content="Use 4x & laser", topic="weapons", feature="sniper", pinned=True),
        MemoryDashboardItem(title="Note", content="Regular note", topic="general", feature="main", pinned=False),
    ]
    html_out = DashboardPresenter.render_memory_column(items)
    assert "⭐ " in html_out
    assert "&lt;Danger&gt;" in html_out
    assert "&amp;" in html_out
    assert "[weapons/sniper]" in html_out


def test_dashboard_presenter_knowledge_table_and_badges():
    """Verify tier badge colors and knowledge table generation."""
    assert DashboardPresenter.get_tier_badge_color(3) == "var(--tier3)"
    assert DashboardPresenter.get_tier_badge_color("4") == "var(--tier4)"
    assert DashboardPresenter.get_tier_badge_color(5) == "var(--tier5)"
    assert DashboardPresenter.get_tier_badge_color("6") == "var(--tier6)"
    assert DashboardPresenter.get_tier_badge_color("-") == "var(--text-secondary)"

    items = [
        KnowledgeDashboardItem(title="Bala 7.62x51mm M80", summary="Round <safe>", tier=4, penetration=44, damage=76)
    ]
    table_html = DashboardPresenter.render_knowledge_table(items)
    assert "<table" in table_html
    assert "<strong>Bala 7.62x51mm M80</strong>" in table_html
    assert "Tier 4" in table_html
    assert "var(--tier4)" in table_html
    assert "<td>44</td>" in table_html
    assert "<td>76</td>" in table_html
    assert "&lt;safe&gt;" in table_html


def test_dashboard_presenter_chart_and_page():
    """Verify Chart.js script block generation and full page rendering."""
    assert DashboardPresenter.render_ballistics_chart([]) == ""
    non_ballistic = [KnowledgeDashboardItem(title="Vest", tier=4, penetration="-", damage="-")]
    assert DashboardPresenter.render_ballistics_chart(non_ballistic) == ""

    ballistic = [
        KnowledgeDashboardItem(title="Bala 7.62x51mm M80", tier=4, penetration=44, damage=76),
        KnowledgeDashboardItem(title="Bala 5.56x45mm A1", tier=4, penetration=42, damage=55),
    ]
    chart_html = DashboardPresenter.render_ballistics_chart(ballistic)
    assert '<canvas id="dashboardChart"></canvas>' in chart_html
    assert '"M80"' in chart_html
    assert '"A1"' in chart_html
    assert "[44, 42]" in chart_html
    assert "[76, 55]" in chart_html

    page_html = DashboardPresenter.render_page(
        memory_items=[MemoryDashboardItem(title="Mem", content="Txt")],
        knowledge_items=ballistic,
        game="abi",
        timestamp="2026-10-18 12:00:00",
    )
    assert "Dashboard Táctico - ABI" in page_html
    assert "Content-Security-Policy" in page_html
