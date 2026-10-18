"""Dashboard items and DTO records (Domain Layer)."""

from __future__ import annotations

from dataclasses import dataclass
import html
import json
from typing import Any, Dict, Optional, Union


def _try_numeric(val: Any) -> Union[int, float, Any]:
    """Attempt converting string or numeric values to int/float if valid."""
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, str):
        s = val.strip()
        try:
            return int(s)
        except ValueError:
            try:
                return float(s)
            except ValueError:
                return val
    return val


@dataclass(frozen=True)
class MemoryDashboardItem:
    """Immutable domain DTO representing a player memory entry in the dashboard."""

    title: str
    content: str
    topic: str = "general"
    feature: str = "main"
    pinned: bool = False

    @classmethod
    def from_raw(cls, item: Any) -> "MemoryDashboardItem":
        """Factory converting dict, PlayerMemory entity, or generic object into MemoryDashboardItem."""
        if isinstance(item, cls):
            return item
        if item is None:
            return cls(title="", content="", topic="general", feature="main", pinned=False)
        if isinstance(item, dict):
            return cls(
                title=str(item.get("title") or ""),
                content=str(item.get("content") or ""),
                topic=str(item.get("topic") or "general"),
                feature=str(item.get("feature") or "main"),
                pinned=bool(item.get("pinned", False)),
            )

        # Duck typing for domain entity PlayerMemory or generic object
        title = getattr(item, "title", "") or ""
        content = getattr(item, "content", "") or ""
        pinned = bool(getattr(item, "pinned", False))
        topic_key = getattr(item, "topic_key", None)
        if topic_key is not None:
            topic = getattr(topic_key, "topic", "general")
            feature = getattr(topic_key, "facet", "main")
        else:
            topic = getattr(item, "topic", "general")
            feature = getattr(item, "feature", "main")

        return cls(
            title=str(title),
            content=str(content),
            topic=str(topic or "general"),
            feature=str(feature or "main"),
            pinned=pinned,
        )


@dataclass(frozen=True)
class KnowledgeDashboardItem:
    """Immutable domain DTO representing a tactical knowledge item in the dashboard."""

    title: str
    summary: str = ""
    tier: Union[int, str] = "-"
    penetration: Union[int, float, str] = "-"
    damage: Union[int, float, str] = "-"
    data_json: str = "{}"

    @property
    def short_name(self) -> str:
        """Strip ammunition calibers for concise chart label display."""
        escaped_title = html.escape(self.title)
        return (
            escaped_title.replace("Bala 7.62x51mm ", "")
            .replace("Bala 9x19mm ", "")
            .replace("Bala 5.56x45mm ", "")
        )

    @property
    def has_ballistic_data(self) -> bool:
        """Check if penetration and damage values are numeric for charting."""
        return (
            isinstance(self.penetration, (int, float))
            and not isinstance(self.penetration, bool)
            and isinstance(self.damage, (int, float))
            and not isinstance(self.damage, bool)
        )

    @classmethod
    def from_raw(cls, item: Any) -> "KnowledgeDashboardItem":
        """Factory converting dict, TacticalFact entity, or generic object into KnowledgeDashboardItem."""
        if isinstance(item, cls):
            return item
        if item is None:
            return cls(title="")

        if isinstance(item, dict):
            title = str(item.get("title") or "")
            summary = str(item.get("summary") or "")
            data_json_raw = item.get("data_json", "{}")
            payload: Dict[str, Any] = {}

            if isinstance(data_json_raw, str) and data_json_raw.strip():
                try:
                    parsed = json.loads(data_json_raw)
                    payload = parsed if isinstance(parsed, dict) else {}
                except Exception:
                    payload = {}
            elif isinstance(data_json_raw, dict):
                payload = data_json_raw
            elif isinstance(item.get("data"), dict):
                payload = item["data"]
            elif isinstance(item.get("data_payload"), dict):
                payload = item["data_payload"]
            else:
                payload = {}

            tier = item.get("tier") if item.get("tier") is not None else payload.get("tier", "-")
            pen = item.get("penetration") if item.get("penetration") is not None else payload.get("penetration", "-")
            dmg = item.get("damage") if item.get("damage") is not None else payload.get("damage", "-")

            tier = _try_numeric(tier) if tier is not None else "-"
            pen = _try_numeric(pen) if pen is not None else "-"
            dmg = _try_numeric(dmg) if dmg is not None else "-"

            data_json_str = data_json_raw if isinstance(data_json_raw, str) else json.dumps(payload)
            return cls(
                title=title,
                summary=summary,
                tier=tier,
                penetration=pen,
                damage=dmg,
                data_json=data_json_str,
            )

        # Duck typing for domain entity TacticalFact or generic object
        title = str(getattr(item, "title", "") or "")
        summary = str(getattr(item, "summary", "") or "")
        raw_payload = getattr(item, "data_payload", {})
        payload = raw_payload if isinstance(raw_payload, dict) else {}

        tier = getattr(item, "tier", None)
        if tier is None:
            tier = payload.get("tier", "-")

        pen = getattr(item, "penetration", None)
        if pen is None:
            pen = payload.get("penetration", "-")

        dmg = getattr(item, "damage", None)
        if dmg is None:
            dmg = payload.get("damage", "-")

        tier = _try_numeric(tier) if tier is not None else "-"
        pen = _try_numeric(pen) if pen is not None else "-"
        dmg = _try_numeric(dmg) if dmg is not None else "-"

        data_json_str = json.dumps(payload) if payload else str(getattr(item, "data_json", "{}") or "{}")
        return cls(
            title=title,
            summary=summary,
            tier=tier,
            penetration=pen,
            damage=dmg,
            data_json=data_json_str,
        )


__all__ = [
    "MemoryDashboardItem",
    "KnowledgeDashboardItem",
]
