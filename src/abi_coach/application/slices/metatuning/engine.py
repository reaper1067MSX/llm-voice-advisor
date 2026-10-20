"""Conversational Meta-Tuning Engine Facade (<=140 LOC)."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from abi_coach.application.services.config_mutator import ConfigMutator
from abi_coach.application.slices.archetypes.manager import ArchetypeManager, EngramObservation
from abi_coach.application.slices.archetypes.scaffolder import ArchetypeScaffolder
from abi_coach.application.slices.metatuning.clarification_fsm import (
    CANCELLATION_PHRASES, CLARIFICATION_TTL_SEC, ClarificationFSM, ClarificationResolution, ClarificationState, is_cancellation_phrase,
)
from abi_coach.application.slices.metatuning.intent_parser import IntentParser
from abi_coach.application.slices.reporting.reports import create_html_report
from abi_coach.domain.enums.metatuning_enums import MetaTuningAction
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager
from abi_coach.infrastructure.config.settings import AppConfig


@dataclass
class MetaTuningResult:
    """Result of a conversational meta-tuning operation."""

    action_taken: str = MetaTuningAction.CANCELLED
    spoken_response: str = ""
    report_path: Optional[str] = None
    is_clarification: bool = False
    target_type: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    handled: bool = True


class MetaTuningEngine:
    """Thin facade orchestrating IntentParser, ClarificationFSM, and ConfigMutator (<=140 LOC)."""

    _QUESTIONS = {
        "combat": "Para calibrar mi asistencia en combate: ¿Prefieres que priorice penetración máxima contra blindajes pesados, builds de armas de bajo retroceso, o tácticas de posicionamiento y flanqueo?",
        "voice": "Para ajustar mi sistema de voz: ¿Deseas respuestas breves de una sola frase, cambiar a una voz más rápida del catálogo, o desactivar las confirmaciones verbales?",
    }

    def __init__(
        self, db: DatabaseManager, archetype_mgr: ArchetypeManager, scaffolder: ArchetypeScaffolder,
        config: AppConfig, config_path: Optional[str] = None, report_opener: Optional[Callable[[str], Any]] = None,
    ):
        self.db, self.archetype_mgr, self.scaffolder = db, archetype_mgr, scaffolder
        self.config, self.config_path, self.report_opener = config, config_path or "config.yaml", report_opener
        self.parser, self.fsm, self.config_mutator = IntentParser(), ClarificationFSM(), ConfigMutator(self.config_path, self.config)

    @property
    def pending_clarification(self) -> Optional[ClarificationState]:
        return self.fsm.pending

    @pending_clarification.setter
    def pending_clarification(self, val: Optional[ClarificationState]) -> None:
        self.fsm.pending = val

    def detect_intent(self, prompt: str) -> Optional[str]:
        return self.parser.detect_intent(prompt)
    def is_vague(self, prompt: str) -> bool:
        return self.parser.is_vague(prompt)
    def _is_clarification_expired(self) -> bool:
        return self.fsm.is_expired()
    def _is_cancellation_phrase(self, text: str) -> bool:
        return self.fsm.is_cancellation(text)

    def generate_clarification(self, prompt: str, context_id: str) -> MetaTuningResult:
        ctx = self.archetype_mgr.get_context(context_id)
        dname, cat = ctx.display_name if ctx else context_id.title(), self.parser.detect_category(prompt)
        q = f"Para afinar mi criterio de loot en {dname}: ¿Deseas que priorice el valor económico por casilla, que filtre solo objetos de tier alto (morado o dorado), o que te avise sobre objetos requeridos para contratos y crafteo?" if cat == "loot" else self._QUESTIONS.get(cat, "Para aplicar este ajuste exactamente como prefieres: ¿Podrías especificar qué regla concreta, umbral numérico o comportamiento deseas que modifique?")
        self.fsm.start(prompt, context_id=context_id, category=cat)
        return MetaTuningResult(action_taken=MetaTuningAction.CLARIFICATION_NEEDED, spoken_response=q, is_clarification=True, target_type="rule", details={"pending_category": cat, "original_prompt": prompt})

    def _save_rule(self, ctx: str, slug: str, title: str, what: str, why: str, learned: str) -> EngramObservation:
        obs = EngramObservation(context_id=ctx, scope="project", topic_key=f"{ctx}/rules/{slug}", observation_type="rule", title=title, pinned=True, content=f"**What**: {what}\n**Why**: {why}\n**Where**: Contexto {ctx}.\n**Learned**: {learned}")
        self.archetype_mgr.save_engram_observation(obs)
        return obs

    def apply_clarification_response(self, response_text: str, context_id: str = "generic") -> Optional[MetaTuningResult]:
        if self.fsm.is_expired():
            self.fsm.reset()
            return self.process(response_text, context_id)
        if self.fsm.is_cancellation(response_text):
            self.fsm.reset()
            return MetaTuningResult(action_taken=MetaTuningAction.CANCELLED, spoken_response="Entendido, cancelé la configuración pendiente.", target_type="rule")

        state, res = self.fsm.resolve(response_text)
        obs = self._save_rule(context_id, res.slug, res.title, res.what, "Calibración conversacional del copiloto.", res.learned)
        rep = self._build_report(res.title, res.what, context_id)
        return MetaTuningResult(action_taken=MetaTuningAction.RULE_SAVED, spoken_response=f"He calibrado mi criterio y guardado la regla de {res.title} en mi memoria persistente. Te abrí los detalles en tu pantalla secundaria.", report_path=rep, target_type="rule", details={"title": res.title, "topic_key": obs.topic_key})

    def _build_report(self, title: str, what: str, context_id: str) -> Optional[str]:
        html = f"""<div class="card"><h2>🧠 Nueva Regla Persistente Activada</h2><div class="badge-row"><span class="badge badge-purple">Contexto: {context_id}</span><span class="badge badge-green">Tipo: Regla Táctica</span><span class="badge badge-blue">Estado: Persistido en Engram</span></div><p><strong>{title}</strong></p><p>{what}</p></div>"""
        try:
            return str(create_html_report(title=f"Regla: {title}", html_body=html, output_dir=self.config.reports.output_dir, auto_open=self.config.reports.auto_open_browser, opener=self.report_opener, preferred_browser=self.config.reports.preferred_browser, focus_browser=getattr(self.config.reports, "focus_browser", False)))
        except Exception:
            return None

    def apply_tuning(self, prompt: str, context_id: str) -> MetaTuningResult:
        if (intent := self.detect_intent(prompt) or "rule") == "config":
            return self._apply_config_update(prompt)
        if intent == "rag":
            return self._apply_rag_ingest(prompt, context_id)
        rule = self.parser.parse_rule(prompt)
        obs = self._save_rule(context_id, rule.slug, rule.title, rule.what, "Instrucción directa del jugador.", rule.learned)
        return MetaTuningResult(action_taken=MetaTuningAction.RULE_SAVED, spoken_response=f"Entendido. He registrado la regla '{rule.title}' en mi memoria persistente y la aplicaré de ahora en adelante.", target_type="rule", details={"title": rule.title, "topic_key": obs.topic_key})

    def _apply_config_update(self, prompt: str) -> MetaTuningResult:
        if not (parsed := self.parser.parse_config(prompt)):
            return MetaTuningResult(action_taken=MetaTuningAction.CLARIFICATION_NEEDED, spoken_response="He recibido la solicitud de configuración global, pero requiero el parámetro exacto (ej. voz, tecla PTT o proveedor).", is_clarification=True, target_type="config")
        self.config_mutator.mutate(parsed.key_path, parsed.value)
        return MetaTuningResult(action_taken=MetaTuningAction.CONFIG_UPDATED, spoken_response=f"{parsed.message} Los cambios fueron guardados permanentemente en config.yaml.", target_type="config", details={"key": parsed.key_name})

    def _apply_rag_ingest(self, prompt: str, context_id: str) -> MetaTuningResult:
        f = self.parser.parse_rag_fact(prompt)
        e = self.scaffolder.auto_ingest_fact(context_id=context_id, category=f.category, title=f.title, summary=f.summary, facets={"source_prompt": prompt})
        return MetaTuningResult(action_taken=MetaTuningAction.RAG_INGESTED, spoken_response=f"He indexado la información sobre {e.title} en la base de conocimientos de {context_id}.", target_type="rag", details={"entity_key": e.entity_key})

    def _save_config_key(self, key_path: List[str], value: Any) -> None:
        self.config_mutator.save_key(key_path, value)
    _handle_config_update = _apply_config_update
    _handle_rule_creation = apply_tuning
    _handle_rag_fact = _apply_rag_ingest

    def process(self, prompt: str, context_id: str = "generic") -> Optional[MetaTuningResult]:
        if self.pending_clarification is not None:
            if not self.fsm.is_expired():
                return self.apply_clarification_response(prompt, context_id)
            self.fsm.reset()
        if (intent := self.detect_intent(prompt)) is None:
            return None
        if self.is_vague(prompt):
            return self.generate_clarification(prompt, context_id)
        return self.apply_tuning(prompt, context_id)

    process_turn = process


__all__ = [
    "CANCELLATION_PHRASES", "CLARIFICATION_TTL_SEC", "ClarificationFSM", "ClarificationResolution",
    "ClarificationState", "MetaTuningEngine", "MetaTuningResult", "is_cancellation_phrase",
]
