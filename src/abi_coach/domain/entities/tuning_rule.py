"""Tuning Rule and Meta-Tuning Entities (Domain Layer)."""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, Optional


@dataclass
class TuningRule:
    """Represents a dynamic behavioral rule established through voice conversation."""

    rule_id: str
    context_id: str
    target_type: str  # rule, config, prompt, rag
    title: str
    directive: str
    rationale: str
    is_active: bool = True
    created_at: float = field(default_factory=time.time)


@dataclass
class MetaTuningDirective:
    """Parsed user directive for adjusting behavior or system settings."""

    intent: str  # rule, config, prompt, rag
    action_taken: str
    spoken_feedback: str
    is_clarification_needed: bool = False
    details: Dict[str, Any] = field(default_factory=dict)
