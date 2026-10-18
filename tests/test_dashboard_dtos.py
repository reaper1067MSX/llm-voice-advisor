"""Focused unit tests for Dashboard typed DTO records."""

from dataclasses import FrozenInstanceError
import pytest

from abi_coach.domain.common.value_objects import TopicKey
from abi_coach.domain.entities.dashboard_records import (
    KnowledgeDashboardItem,
    MemoryDashboardItem,
)
from abi_coach.domain.entities.player_memory import PlayerMemory
from abi_coach.domain.entities.tactical_fact import TacticalFact


def test_memory_dashboard_item_conversions():
    """Verify MemoryDashboardItem conversions from dict, entity, and immutability."""
    raw = {"title": "Sniper Loadout", "content": "Silenced DVL-10", "topic": "weapons", "feature": "sniper", "pinned": True}
    item = MemoryDashboardItem.from_raw(raw)
    assert item.title == "Sniper Loadout"
    assert item.pinned is True

    with pytest.raises(FrozenInstanceError):
        item.title = "Modified"  # type: ignore[misc]

    empty_item = MemoryDashboardItem.from_raw({})
    assert empty_item.title == ""
    assert empty_item.pinned is False
    assert MemoryDashboardItem.from_raw(item) is item
    assert MemoryDashboardItem.from_raw(None).title == ""

    # Entity conversion
    topic_key = TopicKey.create("abi", "armor", "vest")
    entity = PlayerMemory(topic_key=topic_key, title="Tier 6 Armor", content="Heavy armor", pinned=True)
    entity_item = MemoryDashboardItem.from_raw(entity)
    assert entity_item.title == "Tier 6 Armor"
    assert entity_item.topic == "armor"


def test_knowledge_dashboard_item_conversions():
    """Verify KnowledgeDashboardItem parsing, numeric conversions, and properties."""
    raw = {"title": "Bala 7.62x51mm M80", "data_json": '{"tier": 4, "penetration": 44, "damage": 76}', "summary": "Standard round"}
    item = KnowledgeDashboardItem.from_raw(raw)
    assert item.title == "Bala 7.62x51mm M80"
    assert item.tier == 4
    assert item.penetration == 44
    assert item.damage == 76
    assert item.short_name == "M80"
    assert item.has_ballistic_data is True

    with pytest.raises(FrozenInstanceError):
        item.tier = 5  # type: ignore[misc]

    # Malformed data_json fallback
    corrupt = KnowledgeDashboardItem.from_raw({"title": "Corrupt", "data_json": "{bad json"})
    assert corrupt.tier == "-"
    assert corrupt.has_ballistic_data is False

    # String numeric
    str_num = KnowledgeDashboardItem.from_raw({"title": "String Ammo", "data_json": '{"tier": "3", "penetration": "35", "damage": "60.5"}'})
    assert str_num.tier == 3
    assert str_num.damage == 60.5

    # TacticalFact entity conversion
    fact = TacticalFact(game="abi", category="ammo", entity_key="m61", title="Bala 7.62x51mm M61", data_payload={"tier": 5, "penetration": 54, "damage": 72}, summary="AP")
    fact_item = KnowledgeDashboardItem.from_raw(fact)
    assert fact_item.tier == 5
    assert fact_item.penetration == 54
