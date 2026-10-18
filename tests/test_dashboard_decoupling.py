"""Tests for Dashboard Decoupling, Presentation Infrastructure, and Typed Domain DTOs."""

from dataclasses import FrozenInstanceError
from pathlib import Path
import re

import pytest

from abi_coach.application.slices.reporting.dashboard import (
    KnowledgeDashboardItem,
    MemoryDashboardItem,
    create_tactical_dashboard,
)
from abi_coach.domain.common.value_objects import TopicKey
from abi_coach.domain.entities.player_memory import PlayerMemory
from abi_coach.domain.entities.tactical_fact import TacticalFact
from abi_coach.infrastructure.presentation.dashboard_presenter import DashboardPresenter


def test_memory_dashboard_item_from_raw_dict():
    """Verify MemoryDashboardItem.from_raw converts dicts and enforces immutability."""
    raw = {
        "title": "Sniper Loadout",
        "content": "Silenced DVL-10",
        "topic": "weapons",
        "feature": "sniper",
        "pinned": True,
    }
    item = MemoryDashboardItem.from_raw(raw)
    assert item.title == "Sniper Loadout"
    assert item.content == "Silenced DVL-10"
    assert item.topic == "weapons"
    assert item.feature == "sniper"
    assert item.pinned is True

    # Test immutability
    with pytest.raises(FrozenInstanceError):
        item.title = "Modified"  # type: ignore[misc]

    # Test with empty/default dict
    empty_item = MemoryDashboardItem.from_raw({})
    assert empty_item.title == ""
    assert empty_item.content == ""
    assert empty_item.topic == "general"
    assert empty_item.feature == "main"
    assert empty_item.pinned is False

    # Test idempotent conversion
    assert MemoryDashboardItem.from_raw(item) is item

    # Test None input
    none_item = MemoryDashboardItem.from_raw(None)
    assert none_item.title == ""


def test_memory_dashboard_item_from_raw_player_memory_entity():
    """Verify MemoryDashboardItem converts PlayerMemory domain entities."""
    topic_key = TopicKey.create("abi", "armor", "vest")
    entity = PlayerMemory(
        topic_key=topic_key,
        title="Tier 6 6B45 Armor",
        content="Heavy armor for armory raids",
        pinned=True,
    )
    item = MemoryDashboardItem.from_raw(entity)
    assert item.title == "Tier 6 6B45 Armor"
    assert item.content == "Heavy armor for armory raids"
    assert item.topic == "armor"
    assert item.feature == "vest"
    assert item.pinned is True


def test_memory_dashboard_item_from_raw_generic_object():
    """Verify MemoryDashboardItem duck typing with generic objects."""
    class CustomMemory:
        title = "Generic Title"
        content = "Generic Content"
        topic = "custom_topic"
        feature = "custom_feature"
        pinned = False

    item = MemoryDashboardItem.from_raw(CustomMemory())
    assert item.title == "Generic Title"
    assert item.content == "Generic Content"
    assert item.topic == "custom_topic"
    assert item.feature == "custom_feature"
    assert item.pinned is False


def test_knowledge_dashboard_item_from_raw_dict():
    """Verify KnowledgeDashboardItem.from_raw parses data_json and enforces immutability."""
    raw = {
        "title": "Bala 7.62x51mm M80",
        "data_json": '{"tier": 4, "penetration": 44, "damage": 76}',
        "summary": "High efficiency standard round",
    }
    item = KnowledgeDashboardItem.from_raw(raw)
    assert item.title == "Bala 7.62x51mm M80"
    assert item.tier == 4
    assert item.penetration == 44
    assert item.damage == 76
    assert item.summary == "High efficiency standard round"
    assert item.has_ballistic_data is True

    # Test immutability
    with pytest.raises(FrozenInstanceError):
        item.tier = 5  # type: ignore[misc]

    # Test direct keys override
    direct_raw = {
        "title": "Direct Ammo",
        "tier": 5,
        "penetration": 52,
        "damage": 68,
        "summary": "Direct summary",
    }
    direct_item = KnowledgeDashboardItem.from_raw(direct_raw)
    assert direct_item.tier == 5
    assert direct_item.penetration == 52
    assert direct_item.damage == 68

    # Test malformed data_json fallback
    malformed = {
        "title": "Corrupt Ammo",
        "data_json": "{not valid json",
    }
    corrupt_item = KnowledgeDashboardItem.from_raw(malformed)
    assert corrupt_item.tier == "-"
    assert corrupt_item.penetration == "-"
    assert corrupt_item.damage == "-"
    assert corrupt_item.has_ballistic_data is False

    # Test string numeric conversion
    str_numeric = {
        "title": "String Ammo",
        "data_json": '{"tier": "3", "penetration": "35", "damage": "60.5"}',
    }
    str_item = KnowledgeDashboardItem.from_raw(str_numeric)
    assert str_item.tier == 3
    assert str_item.penetration == 35
    assert str_item.damage == 60.5
    assert str_item.has_ballistic_data is True

    # Test idempotent conversion
    assert KnowledgeDashboardItem.from_raw(item) is item

    # Test None input
    none_item = KnowledgeDashboardItem.from_raw(None)
    assert none_item.title == ""


def test_knowledge_dashboard_item_from_raw_tactical_fact_entity():
    """Verify KnowledgeDashboardItem converts TacticalFact domain entities."""
    fact = TacticalFact(
        game="abi",
        category="ammo",
        entity_key="m61",
        title="Bala 7.62x51mm M61",
        data_payload={"tier": 5, "penetration": 54, "damage": 72},
        summary="Armor piercing cartridge",
    )
    item = KnowledgeDashboardItem.from_raw(fact)
    assert item.title == "Bala 7.62x51mm M61"
    assert item.tier == 5
    assert item.penetration == 54
    assert item.damage == 72
    assert item.summary == "Armor piercing cartridge"
    assert item.has_ballistic_data is True


def test_knowledge_dashboard_item_properties():
    """Verify .short_name and .has_ballistic_data properties."""
    item1 = KnowledgeDashboardItem(
        title="Bala 7.62x51mm M80",
        tier=4,
        penetration=44,
        damage=76,
    )
    assert item1.short_name == "M80"
    assert item1.has_ballistic_data is True

    item2 = KnowledgeDashboardItem(
        title="Bala 5.56x45mm A1",
        tier=4,
        penetration=42,
        damage=55,
    )
    assert item2.short_name == "A1"

    item3 = KnowledgeDashboardItem(
        title="Bala 9x19mm AP6.3",
        tier=3,
        penetration=30,
        damage=52,
    )
    assert item3.short_name == "AP6.3"

    item4 = KnowledgeDashboardItem(
        title="Botiquín Militar",
        tier="-",
        penetration="-",
        damage="-",
    )
    assert item4.short_name == "Botiquín Militar"
    assert item4.has_ballistic_data is False


def test_dashboard_presenter_memory_column():
    """Verify DashboardPresenter formats memory cards, escaping, and empty state."""
    # Empty items
    empty_html = DashboardPresenter.render_memory_column([])
    assert "Sin memorias guardadas aún." in empty_html

    # Populated items with HTML escaping
    items = [
        MemoryDashboardItem(
            title="Loadout <Danger>",
            content="Use 4x scope & laser",
            topic="weapons",
            feature="sniper",
            pinned=True,
        ),
        MemoryDashboardItem(
            title="Unpinned Memory",
            content="Regular note",
            topic="general",
            feature="main",
            pinned=False,
        ),
    ]
    html_out = DashboardPresenter.render_memory_column(items)
    assert "⭐ " in html_out
    assert "&lt;Danger&gt;" in html_out
    assert "&amp;" in html_out
    assert "Unpinned Memory" in html_out
    assert "[weapons/sniper]" in html_out
    assert "[general/main]" in html_out


def test_dashboard_presenter_tier_colors_and_table():
    """Verify tier badge colors and knowledge table generation."""
    assert DashboardPresenter.get_tier_badge_color(3) == "var(--tier3)"
    assert DashboardPresenter.get_tier_badge_color("4") == "var(--tier4)"
    assert DashboardPresenter.get_tier_badge_color(5) == "var(--tier5)"
    assert DashboardPresenter.get_tier_badge_color("6") == "var(--tier6)"
    assert DashboardPresenter.get_tier_badge_color("-") == "var(--text-secondary)"
    assert DashboardPresenter.get_tier_badge_color(1) == "var(--text-secondary)"

    items = [
        KnowledgeDashboardItem(
            title="Bala 7.62x51mm M80",
            summary="Standard round <safe>",
            tier=4,
            penetration=44,
            damage=76,
        )
    ]
    table_html = DashboardPresenter.render_knowledge_table(items)
    assert "<table" in table_html
    assert "<strong>Bala 7.62x51mm M80</strong>" in table_html
    assert "Tier 4" in table_html
    assert "var(--tier4)" in table_html
    assert "<td>44</td>" in table_html
    assert "<td>76</td>" in table_html
    assert "&lt;safe&gt;" in table_html


def test_dashboard_presenter_ballistics_chart():
    """Verify Chart.js script block generation and empty fallback."""
    # Empty items
    assert DashboardPresenter.render_ballistics_chart([]) == ""

    # Items without ballistic data
    non_ballistic = [KnowledgeDashboardItem(title="Vest", tier=4, penetration="-", damage="-")]
    assert DashboardPresenter.render_ballistics_chart(non_ballistic) == ""

    # Ballistic items
    ballistic_items = [
        KnowledgeDashboardItem(title="Bala 7.62x51mm M80", tier=4, penetration=44, damage=76),
        KnowledgeDashboardItem(title="Bala 5.56x45mm A1", tier=4, penetration=42, damage=55),
    ]
    chart_html = DashboardPresenter.render_ballistics_chart(ballistic_items)
    assert '<canvas id="dashboardChart"></canvas>' in chart_html
    assert "Comparativa Balística en Tiempo Real" in chart_html
    assert '"M80"' in chart_html
    assert '"A1"' in chart_html
    assert "[44, 42]" in chart_html
    assert "[76, 55]" in chart_html


def test_dashboard_presenter_render_page():
    """Verify full HTML page generation via HTML_TEMPLATE."""
    memories = [MemoryDashboardItem(title="Test Memory", content="Content")]
    knowledge = [KnowledgeDashboardItem(title="Test Ammo", tier=4, penetration=40, damage=70)]

    page_html = DashboardPresenter.render_page(
        memory_items=memories,
        knowledge_items=knowledge,
        game="abi",
        timestamp="2026-10-18 12:00:00",
    )
    assert "Dashboard Táctico - ABI" in page_html
    assert "Content-Security-Policy" in page_html
    assert "2026-10-18 12:00:00" in page_html
    assert "Test Memory" in page_html
    assert "Test Ammo" in page_html


def test_create_tactical_dashboard_with_typed_and_dict_inputs(tmp_path: Path):
    """Verify create_tactical_dashboard handles both dicts and typed DTOs."""
    out_dir = tmp_path / "dashboards"

    # Call with typed domain DTOs
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
    assert "dashboardChart" in content1

    # Call with custom opener callback
    opened_paths = []
    def mock_opener(p: str):
        opened_paths.append(p)

    path2 = create_tactical_dashboard(
        memory_items=[{"title": "Dict Memory", "content": "From Dict"}],
        knowledge_items=[{"title": "Dict Ammo", "tier": 3}],
        game="abi",
        output_dir=str(out_dir / "sub"),
        auto_open=True,
        opener=mock_opener,
    )
    assert path2.exists()
    assert len(opened_paths) == 1
    assert str(path2.resolve()) in opened_paths[0]


def test_dashboard_py_loc_and_zero_html_strings():
    """Verify dashboard.py is a thin facade (<= 100 LOC) and contains zero HTML tags."""
    dashboard_path = Path("src/abi_coach/application/slices/reporting/dashboard.py")
    assert dashboard_path.exists()

    code = dashboard_path.read_text(encoding="utf-8")
    lines = code.splitlines()

    # LOC constraint: strictly <= 100 LOC (architectural ceiling is <= 200 LOC)
    assert len(lines) <= 100, f"dashboard.py has {len(lines)} LOC, expected <= 100"
    assert len(lines) >= 30, f"dashboard.py has {len(lines)} LOC, unexpectedly sparse"

    # Zero embedded HTML tags in dashboard.py
    forbidden_html = ["<div", "<table", "<tr", "<th", "<td", "<p", "<h2", "<h3", "<canvas", "<script"]
    for tag in forbidden_html:
        assert tag not in code, f"Found embedded HTML tag '{tag}' in dashboard.py"

    # Zero semicolons
    semicolon_matches = [line for line in lines if ";" in line and not line.strip().startswith("#")]
    assert not semicolon_matches, f"Found semicolons in dashboard.py: {semicolon_matches}"


def test_module_reexports_and_public_contracts():
    """Verify backward-compatible exports across domain, presentation, and reporting."""
    from abi_coach import KnowledgeDashboardItem as RootKnowledgeItem
    from abi_coach import MemoryDashboardItem as RootMemoryItem
    from abi_coach.domain import KnowledgeDashboardItem as DomainKnowledgeItem
    from abi_coach.domain import MemoryDashboardItem as DomainMemoryItem
    from abi_coach.domain.entities import KnowledgeDashboardItem as EntityKnowledgeItem
    from abi_coach.domain.entities import MemoryDashboardItem as EntityMemoryItem
    from abi_coach.application.slices.reporting import KnowledgeDashboardItem as ReportingKnowledgeItem
    from abi_coach.application.slices.reporting import MemoryDashboardItem as ReportingMemoryItem
    from abi_coach.application.slices.reporting import create_tactical_dashboard as ReportingCreateDashboard
    from abi_coach.infrastructure.presentation import DashboardPresenter as InfraPresenter

    assert RootMemoryItem is EntityMemoryItem
    assert RootKnowledgeItem is EntityKnowledgeItem
    assert DomainMemoryItem is EntityMemoryItem
    assert DomainKnowledgeItem is EntityKnowledgeItem
    assert ReportingMemoryItem is EntityMemoryItem
    assert ReportingKnowledgeItem is EntityKnowledgeItem
    assert callable(ReportingCreateDashboard)
    assert callable(InfraPresenter.render_page)
