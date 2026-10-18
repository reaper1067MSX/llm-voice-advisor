"""Adversarial stress testing and empirical verification suite for PR #7 Remediation.

Authored by Challenger 1 (Adversarial Correctness & Boundary Stress).
Empirically stress-tests:
- RuleMapping 5-tuple unpacking vs attribute access and edge-case strings.
- ClarificationState TTL expiration, missing key handling, and multi-threaded race conditions.
- MemoryDashboardItem.from_raw and KnowledgeDashboardItem.from_raw with malformed dicts,
  None values, unusual types, and corrupted/non-dict JSON.
- MetaTuningIntent, MetaTuningCategory, MetaTuningAction StrEnum equality, sets, dict keys,
  and JSON serialization.
- DashboardPresenter HTML escaping and XSS boundary behavior.
"""

from dataclasses import FrozenInstanceError
import json
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
import pytest

from abi_coach.domain.entities.metatuning_records import (
    ClarificationResolution,
    ClarificationState,
    RuleMapping,
    RESOLUTION_RULES,
)
from abi_coach.domain.enums.metatuning_enums import (
    MetaTuningAction,
    MetaTuningCategory,
    MetaTuningIntent,
)
from abi_coach.application.slices.metatuning.clarification_fsm import (
    CLARIFICATION_TTL_SEC,
    ClarificationFSM,
)
from abi_coach.domain.entities.dashboard_records import (
    KnowledgeDashboardItem,
    MemoryDashboardItem,
)
from abi_coach.infrastructure.presentation.dashboard_presenter import DashboardPresenter


# ===========================================================================
# 1. RuleMapping Adversarial & Boundary Stress Tests
# ===========================================================================

class TestRuleMappingAdversarial:
    """Adversarial challenge on RuleMapping 5-tuple unpacking vs attribute access."""

    def test_5_tuple_unpacking_and_attribute_parity(self):
        """Verify full parity between 5-tuple unpacking and named attributes."""
        for mapping in RESOLUTION_RULES:
            kws, title, slug, what, learned = mapping
            assert kws == mapping.keywords
            assert title == mapping.title
            assert slug == mapping.slug
            assert what == mapping.what
            assert learned == mapping.learned
            assert len(mapping) == 5

    def test_extended_unpacking_and_membership(self):
        """Verify extended unpacking (*rest) and element containment."""
        mapping = RuleMapping(
            keywords=("k1", "k2"),
            title="Title Test",
            slug="title_test",
            what="What Test",
            learned="Learned Test",
        )
        first, *middle, last = mapping
        assert first == ("k1", "k2")
        assert middle == ["Title Test", "title_test", "What Test"]
        assert last == "Learned Test"

        # Membership checks against iterated tuple values
        assert "Title Test" in mapping
        assert ("k1", "k2") in mapping
        assert "unrelated_str" not in mapping

    def test_negative_indexing_and_slicing(self):
        """Verify indexing, negative bounds, slicing, and IndexError."""
        mapping = RuleMapping(
            keywords=("a", "b"),
            title="T",
            slug="S",
            what="W",
            learned="L",
        )
        assert mapping[0] == ("a", "b")
        assert mapping[1] == "T"
        assert mapping[-1] == "L"
        assert mapping[-5] == ("a", "b")

        # Slicing
        assert mapping[1:3] == ("T", "S")
        assert mapping[::-1] == ("L", "W", "S", "T", ("a", "b"))

        # Out-of-bounds raises IndexError
        with pytest.raises(IndexError):
            _ = mapping[5]
        with pytest.raises(IndexError):
            _ = mapping[-6]

    def test_frozen_immutability(self):
        """Verify RuleMapping cannot be mutated after instantiation."""
        mapping = RuleMapping(
            keywords=("a",),
            title="Immutable",
            slug="imm",
            what="W",
            learned="L",
        )
        with pytest.raises((FrozenInstanceError, AttributeError)):
            mapping.title = "Mutated Title"  # type: ignore

    def test_hashability_and_set_operations(self):
        """Verify RuleMapping instances are hashable and behave cleanly in sets and dict keys."""
        rm1 = RuleMapping(("k",), "T", "S", "W", "L")
        rm2 = RuleMapping(("k",), "T", "S", "W", "L")
        rm3 = RuleMapping(("k_other",), "T", "S", "W", "L")

        # Set deduplication
        s = {rm1, rm2, rm3}
        assert len(s) == 2
        assert rm1 in s
        assert rm2 in s

        # Dict key resolution
        d = {rm1: "first_value"}
        assert d[rm2] == "first_value"

    def test_edge_case_strings(self):
        """Verify RuleMapping handles blank, unicode, emoji, null-byte, and 50k char strings."""
        massive_string = "X" * 50000
        emoji_string = "🛡️ Armadura Pesada Nivel 6 ⚔️ 💥"
        null_byte_string = "prefix\x00middle\x00suffix"
        crlf_string = "Line 1\r\nLine 2\tTabbed\nLine 3"

        mapping = RuleMapping(
            keywords=(emoji_string, null_byte_string),
            title=crlf_string,
            slug="custom_slug",
            what="",
            learned=massive_string,
        )

        kws, title, slug, what, learned = mapping
        assert kws == (emoji_string, null_byte_string)
        assert title == crlf_string
        assert what == ""
        assert learned == massive_string
        assert len(learned) == 50000


# ===========================================================================
# 2. ClarificationState & ClarificationFSM Concurrency and TTL Stress Tests
# ===========================================================================

class TestClarificationFSMStress:
    """Adversarial stress tests for ClarificationState and ClarificationFSM."""

    def test_clarification_state_backward_compatibility_and_duck_typing(self):
        """Verify .timestamp property, .get(), and __getitem__ on ClarificationState."""
        t_start = time.time()
        state = ClarificationState(
            original_prompt="Haz que sea mejor",
            context_id="abi",
            category="combat",
            created_at=t_start,
        )

        assert state.timestamp == t_start
        assert state.get("timestamp") == t_start
        assert state["timestamp"] == t_start

        # Known attributes via get and index
        assert state.get("original_prompt") == "Haz que sea mejor"
        assert state["original_prompt"] == "Haz que sea mejor"
        assert state.get("category") == "combat"
        assert state["category"] == "combat"

        # Missing attributes with default
        assert state.get("non_existent_key", "default_val") == "default_val"
        assert state.get("non_existent_key") is None

    def test_ttl_precision_boundaries(self):
        """Verify strict TTL behavior at 59s, 59.999s, 60.0s, and 60.001s."""
        fsm = ClarificationFSM(ttl_sec=60.0)
        t_base = 500000.0
        fsm.start("prompt", context_id="abi", category="combat")
        fsm.pending.created_at = t_base

        # 59.0s -> Not expired
        assert fsm.is_expired(now=t_base + 59.0) is False
        # 59.999s -> Not expired
        assert fsm.is_expired(now=t_base + 59.999) is False
        # 60.0s exact -> Not expired (condition is strict > 60.0)
        assert fsm.is_expired(now=t_base + 60.0) is False
        # 60.001s -> Expired
        assert fsm.is_expired(now=t_base + 60.001) is True
        # 120.0s -> Expired
        assert fsm.is_expired(now=t_base + 120.0) is True

    def test_ttl_auto_reset(self):
        """Verify auto_reset=True clears pending state when expired and retains when active."""
        fsm = ClarificationFSM(ttl_sec=60.0)
        t_base = 500000.0
        fsm.start("prompt", context_id="abi", category="combat")
        fsm.pending.created_at = t_base

        # Under TTL: state retained
        assert fsm.is_expired(now=t_base + 30.0, auto_reset=True) is False
        assert fsm.has_pending is True

        # Over TTL: state cleared atomically
        assert fsm.is_expired(now=t_base + 65.0, auto_reset=True) is True
        assert fsm.has_pending is False
        assert fsm.pending is None

    def test_future_timestamp_does_not_expire(self):
        """Verify timestamps set in the future do not trigger expiration."""
        fsm = ClarificationFSM(ttl_sec=60.0)
        now = time.time()
        fsm.start("future prompt", context_id="abi", category="general")
        fsm.pending.created_at = now + 1000.0

        assert fsm.is_expired(now=now) is False

    def test_timestamp_zero_falsy_bug(self):
        """Demonstrate falsy timestamp bug: created_at=0.0 fails to register as expired."""
        fsm = ClarificationFSM(ttl_sec=60.0)
        fsm.pending = ClarificationState("test", created_at=0.0)
        # 100.0s after epoch 0 should be expired (> 60s)
        assert fsm.is_expired(now=100.0) is True

    def test_resolve_with_none_category_bug(self):
        """Demonstrate crash in resolve when state.category is explicitly None."""
        fsm = ClarificationFSM()
        fsm.pending = ClarificationState("test prompt", category=None)  # type: ignore
        state, res = fsm.resolve("unrelated reply")
        assert res.title.startswith("Regla Personalizada")

    def test_heavy_concurrency_race_conditions(self):
        """Stress-test ClarificationFSM across 40 concurrent threads performing rapid state changes."""
        fsm = ClarificationFSM(ttl_sec=60.0)
        errors: List[Exception] = []
        stop_event = threading.Event()

        def worker_start(tid: int):
            try:
                for i in range(100):
                    if stop_event.is_set():
                        break
                    fsm.start(f"prompt_{tid}_{i}", context_id="abi", category="combat")
                    time.sleep(0.0001)
            except Exception as e:
                errors.append(e)

        def worker_resolve(tid: int):
            try:
                for _ in range(100):
                    if stop_event.is_set():
                        break
                    fsm.resolve("prioriza penetracion")
                    time.sleep(0.0001)
            except Exception as e:
                errors.append(e)

        def worker_expire(tid: int):
            try:
                for _ in range(100):
                    if stop_event.is_set():
                        break
                    fsm.is_expired(auto_reset=True)
                    time.sleep(0.0001)
            except Exception as e:
                errors.append(e)

        def worker_reset(tid: int):
            try:
                for _ in range(100):
                    if stop_event.is_set():
                        break
                    fsm.reset()
                    time.sleep(0.0001)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(10):
            threads.append(threading.Thread(target=worker_start, args=(i,)))
            threads.append(threading.Thread(target=worker_resolve, args=(i,)))
            threads.append(threading.Thread(target=worker_expire, args=(i,)))
            threads.append(threading.Thread(target=worker_reset, args=(i,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)
            if t.is_alive():
                stop_event.set()
                pytest.fail("Deadlock detected in ClarificationFSM under concurrency!")

        assert len(errors) == 0, f"Concurrent operations raised exceptions: {errors}"


# ===========================================================================
# 3. Dashboard Records Adversarial & Malformed Input Tests
# ===========================================================================

class TestDashboardRecordsAdversarial:
    """Stress testing MemoryDashboardItem and KnowledgeDashboardItem against malformed inputs."""

    def test_memory_dashboard_item_from_raw_resilience(self):
        """Verify MemoryDashboardItem.from_raw handles None, empty dict, and corrupted fields."""
        # 1. None
        m_none = MemoryDashboardItem.from_raw(None)
        assert m_none.title == ""
        assert m_none.content == ""
        assert m_none.topic == "general"
        assert m_none.feature == "main"
        assert m_none.pinned is False

        # 2. Empty dict
        m_empty = MemoryDashboardItem.from_raw({})
        assert m_empty.title == ""
        assert m_empty.pinned is False

        # 3. Dict with None values
        m_nulls = MemoryDashboardItem.from_raw({
            "title": None,
            "content": None,
            "topic": None,
            "feature": None,
            "pinned": None,
        })
        assert m_nulls.title == ""
        assert m_nulls.content == ""
        assert m_nulls.topic == "general"
        assert m_nulls.feature == "main"
        assert m_nulls.pinned is False

        # 4. Unusual types in dict
        m_types = MemoryDashboardItem.from_raw({
            "title": 99999,
            "content": ["item1", "item2"],
            "topic": {"sub": "combat"},
            "feature": 12.34,
            "pinned": "yes",
        })
        assert m_types.title == "99999"
        assert m_types.content == "['item1', 'item2']"
        assert m_types.pinned is True

        # 5. Duck typing with custom object
        class CustomMemory:
            title = "CustomTitle"
            content = "CustomContent"
            pinned = True
            topic_key = None
            topic = "custom_topic"
            feature = "custom_feature"

        m_duck = MemoryDashboardItem.from_raw(CustomMemory())
        assert m_duck.title == "CustomTitle"
        assert m_duck.topic == "custom_topic"
        assert m_duck.pinned is True

        # 6. Idempotency
        assert MemoryDashboardItem.from_raw(m_duck) is m_duck

    def test_knowledge_dashboard_item_from_raw_clean_and_numeric_conversions(self):
        """Verify KnowledgeDashboardItem.from_raw with None, empty dict, and numeric strings."""
        # 1. None
        k_none = KnowledgeDashboardItem.from_raw(None)
        assert k_none.title == ""
        assert k_none.tier == "-"
        assert k_none.penetration == "-"
        assert k_none.damage == "-"
        assert k_none.has_ballistic_data is False

        # 2. String numeric conversion
        k_num = KnowledgeDashboardItem.from_raw({
            "title": "Bala 7.62x51mm M80",
            "tier": "4",
            "penetration": "45",
            "damage": "72.5",
        })
        assert k_num.tier == 4
        assert k_num.penetration == 45
        assert k_num.damage == 72.5
        assert k_num.has_ballistic_data is True
        assert k_num.short_name == "M80"

        # 3. Invalid JSON string in data_json safely defaults to empty dict
        k_broken_json = KnowledgeDashboardItem.from_raw({
            "title": "Broken JSON",
            "data_json": "{unclosed: json syntax, ",
        })
        assert k_broken_json.title == "Broken JSON"
        assert k_broken_json.tier == "-"

    def test_knowledge_item_from_raw_non_dict_json_payload_bug(self):
        """Demonstrate crash when data_json contains valid JSON that is not a dictionary."""
        non_dict_payloads = [
            "[1, 2, 3]",
            "123",
            "true",
            "null",
            '"scalar string"',
        ]
        for payload_str in non_dict_payloads:
            item = KnowledgeDashboardItem.from_raw({
                "title": "Test Non-Dict JSON",
                "data_json": payload_str,
            })
            assert item.title == "Test Non-Dict JSON"
            assert item.tier == "-"

    def test_knowledge_item_from_raw_duck_typing_non_dict_payload_bug(self):
        """Demonstrate crash when duck-typed object has non-dict data_payload."""
        class MockFact:
            title = "MockFact"
            summary = "Summary"
            data_payload = [1, 2, 3]  # List instead of dict
            tier = None
            penetration = None
            damage = None

        item = KnowledgeDashboardItem.from_raw(MockFact())
        assert item.title == "MockFact"
        assert item.tier == "-"

    def test_knowledge_item_ballistic_properties(self):
        """Verify has_ballistic_data rejects booleans, strings, and non-numerics."""
        # True is an instance of int in Python, must be explicitly excluded
        k_bool = KnowledgeDashboardItem(title="T", penetration=True, damage=False)  # type: ignore
        assert k_bool.has_ballistic_data is False

        # Strings are excluded
        k_str = KnowledgeDashboardItem(title="T", penetration="50", damage="60")
        assert k_str.has_ballistic_data is False

        # Valid numerics
        k_valid = KnowledgeDashboardItem(title="T", penetration=50, damage=60)
        assert k_valid.has_ballistic_data is True


# ===========================================================================
# 4. Dashboard Presenter HTML Escaping & Injection Tests
# ===========================================================================

class TestDashboardPresenterEscaping:
    """Stress testing DashboardPresenter HTML escaping and injection defenses."""

    def test_render_memory_card_escapes_xss(self):
        """Verify render_memory_card escapes HTML tags and quotes."""
        item = MemoryDashboardItem(
            title="<script>alert('title')</script>",
            content="<img src=x onerror=alert('content')>",
            topic="<b>topic</b>",
            feature="<i>feature</i>",
            pinned=True,
        )
        html_out = DashboardPresenter.render_memory_card(item)
        assert "<script>" not in html_out
        assert "&lt;script&gt;" in html_out
        assert "<img src=x" not in html_out
        assert "&lt;img" in html_out
        assert "⭐" in html_out

    def test_render_knowledge_row_escapes_tier_and_ballistics_vulnerability(self):
        """Demonstrate unescaped HTML injection in tier, penetration, and damage."""
        item = KnowledgeDashboardItem(
            title="Safe Title",
            summary="Safe Summary",
            tier="<script>alert('tier')</script>",
            penetration="<img src=x onerror=alert('pen')>",
            damage="<svg onload=alert('dmg')>",
        )
        row = DashboardPresenter.render_knowledge_row(item)
        # Should be escaped, not emitted raw
        assert "<script>" not in row, "Vulnerability: unescaped <script> tag in tier column"
        assert "<img src=x" not in row, "Vulnerability: unescaped <img> tag in penetration column"
        assert "<svg" not in row, "Vulnerability: unescaped <svg> tag in damage column"

    def test_short_name_double_escaping_anomaly(self):
        """Document short_name behavior: html.escape in short_name creates HTML entities in Chart.js canvas labels."""
        k = KnowledgeDashboardItem(
            title="Bala 9x19mm Rip & Tear",
            penetration=30,
            damage=65,
        )
        chart_html = DashboardPresenter.render_ballistics_chart([k])
        # Canvas label in JSON will contain &amp; because short_name escapes &
        assert "Rip &amp; Tear" in chart_html


# ===========================================================================
# 5. MetaTuning StrEnum Adversarial & Compatibility Tests
# ===========================================================================

class TestMetaTuningEnumsAdversarial:
    """Adversarial challenge for MetaTuning StrEnum equality, serialization, and typing."""

    def test_strenum_raw_string_equality(self):
        """Verify MetaTuning StrEnums compare equal to raw Python strings."""
        assert MetaTuningIntent.CONFIG == "config"
        assert MetaTuningIntent.RULE == "rule"
        assert MetaTuningIntent.PROMPT == "prompt"
        assert MetaTuningIntent.RAG == "rag"

        assert MetaTuningCategory.LOOT == "loot"
        assert MetaTuningCategory.COMBAT == "combat"
        assert MetaTuningCategory.VOICE == "voice"
        assert MetaTuningCategory.GENERAL == "general"

        assert MetaTuningAction.CLARIFICATION_NEEDED == "clarification_needed"
        assert MetaTuningAction.RULE_SAVED == "rule_saved"
        assert MetaTuningAction.CONFIG_UPDATED == "config_updated"
        assert MetaTuningAction.PROMPT_UPDATED == "prompt_updated"
        assert MetaTuningAction.RAG_INGESTED == "rag_ingested"
        assert MetaTuningAction.CANCELLED == "cancelled"

        # Verify isinstance str
        assert isinstance(MetaTuningIntent.CONFIG, str)
        assert isinstance(MetaTuningCategory.LOOT, str)
        assert isinstance(MetaTuningAction.RULE_SAVED, str)

    def test_strenum_set_deduplication_and_membership(self):
        """Verify sets seamlessly deduplicate StrEnum members and equivalent raw strings."""
        # Mixed set
        s = {MetaTuningIntent.CONFIG, "config"}
        assert len(s) == 1
        assert "config" in s
        assert MetaTuningIntent.CONFIG in s

        # Membership test
        assert MetaTuningIntent.CONFIG in {"config", "rule"}
        assert "rule" in {MetaTuningIntent.CONFIG, MetaTuningIntent.RULE}

    def test_strenum_dict_key_lookup(self):
        """Verify StrEnum and raw string keys resolve identically in dictionaries."""
        d = {
            MetaTuningIntent.CONFIG: "config_handler",
            MetaTuningIntent.RULE: "rule_handler",
        }
        # Retrieve by raw string
        assert d["config"] == "config_handler"
        assert d["rule"] == "rule_handler"

        # Mutate via raw string
        d["config"] = "new_config_handler"
        assert d[MetaTuningIntent.CONFIG] == "new_config_handler"
        assert len(d) == 2

    def test_strenum_json_serialization(self):
        """Verify json.dumps serializes StrEnum directly as values and as dictionary keys."""
        payload = {
            "intent": MetaTuningIntent.CONFIG,
            "category": MetaTuningCategory.COMBAT,
            "action": MetaTuningAction.RULE_SAVED,
        }
        json_str = json.dumps(payload)
        parsed = json.loads(json_str)

        assert parsed["intent"] == "config"
        assert parsed["category"] == "combat"
        assert parsed["action"] == "rule_saved"

        # As dict keys
        key_payload = {MetaTuningCategory.LOOT: 100}
        key_json = json.dumps(key_payload)
        parsed_key = json.loads(key_json)
        assert parsed_key["loot"] == 100

    def test_strenum_formatting_and_str(self):
        """Verify f-strings and str() yield clean string values, not Enum representation."""
        assert f"{MetaTuningIntent.CONFIG}" == "config"
        assert str(MetaTuningCategory.LOOT) == "loot"
        assert str(MetaTuningAction.RULE_SAVED) == "rule_saved"

    def test_invalid_strenum_values_raise_value_error(self):
        """Verify invalid values cannot be constructed and raise ValueError."""
        with pytest.raises(ValueError):
            MetaTuningIntent("invalid_intent")
        with pytest.raises(ValueError):
            MetaTuningCategory("invalid_category")
        with pytest.raises(ValueError):
            MetaTuningAction("invalid_action")
