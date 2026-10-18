"""Focused tests verifying backward-compatible reexports across metatuning packages."""

from abi_coach.domain.entities.metatuning_records import (
    CANCELLATION_PHRASES,
    ClarificationResolution,
    ClarificationState,
    ParsedConfig,
    ParsedFact,
    ParsedRule,
    RESOLUTION_RULES,
    is_cancellation_phrase,
)
from abi_coach.application.slices.metatuning import (
    ClarificationState as ROOT_State,
    MetaTuningEngine as ROOT_Engine,
    MetaTuningResult as ROOT_Result,
)
from abi_coach.application.slices.metatuning.clarification_fsm import (
    CANCELLATION_PHRASES as FSM_CANCEL,
    CONFIRMATION_RULES as FSM_RULES,
    ClarificationResolution as FSM_Res,
    ClarificationState as FSM_State,
    is_cancellation_phrase as fsm_is_cancel,
)
from abi_coach.application.slices.metatuning.engine import (
    ClarificationState as ENG_State,
    MetaTuningEngine as ENG_Engine,
    MetaTuningResult as ENG_Result,
)
from abi_coach.application.slices.metatuning.intent_parser import (
    CANCELLATION_PHRASES as IP_CANCEL,
    RESOLUTION_RULES as IP_RULES,
    ParsedConfig as IP_Cfg,
    ParsedFact as IP_Fact,
    ParsedRule as IP_Rule,
)


def test_reexports_backward_compatibility():
    """Verify all legacy imports continue to resolve without breaking consumer code."""
    assert IP_CANCEL is FSM_CANCEL
    assert IP_RULES is FSM_RULES
    assert IP_Cfg is ParsedConfig
    assert IP_Fact is ParsedFact
    assert IP_Rule is ParsedRule
    assert FSM_State is ClarificationState
    assert FSM_Res is ClarificationResolution
    assert fsm_is_cancel is is_cancellation_phrase
    assert ENG_State is ClarificationState
    assert ROOT_State is ClarificationState
    assert ROOT_Engine is ENG_Engine
    assert ROOT_Result is ENG_Result
