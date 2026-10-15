"""Conversational Meta-Tuning Engine with Clarification Loop (Meta-Tuning Slice).

Allows conversational tuning of system prompts, Engram persistent rules,
knowledge base facts (RAG), and global configurations (config.yaml).
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import time
from typing import Any, Callable, Dict, List, Optional
import yaml

from abi_coach.core.config import AppConfig
from abi_coach.core.storage.db import DatabaseManager
from abi_coach.reports import create_html_report
from abi_coach.slices.archetypes.manager import ArchetypeManager, DynamicEntity, EngramObservation, TopicContext
from abi_coach.slices.archetypes.scaffolder import ArchetypeScaffolder


@dataclass
class MetaTuningResult:
    """Result of a conversational meta-tuning operation."""

    action_taken: str  # "clarification_needed", "rule_saved", "config_updated", "prompt_updated", "rag_ingested"
    spoken_response: str
    report_path: Optional[str] = None
    is_clarification: bool = False
    target_type: Optional[str] = None  # "rule", "config", "prompt", "rag"
    details: Dict[str, Any] = field(default_factory=dict)


class MetaTuningEngine:
    """Detects, clarifies, and compiles conversational meta-tuning instructions."""

    def __init__(
        self,
        db: DatabaseManager,
        archetype_mgr: ArchetypeManager,
        scaffolder: ArchetypeScaffolder,
        config: AppConfig,
        config_path: Optional[str] = None,
        report_opener: Optional[Callable[[str], Any]] = None,
    ):
        self.db = db
        self.archetype_mgr = archetype_mgr
        self.scaffolder = scaffolder
        self.config = config
        self.config_path = config_path or "config.yaml"
        self.report_opener = report_opener
        self.pending_clarification: Optional[Dict[str, Any]] = None

    def detect_intent(self, prompt: str) -> Optional[str]:
        """Detect whether user input is requesting meta-configuration or behavioral tuning.

        Returns one of 'config', 'rule', 'prompt', 'rag', or None.
        """
        p = prompt.strip().lower()

        # 1. Explicit global configuration triggers
        if any(term in p for term in ("configuración global", "configuracion global", "ajustes globales", "cambiar configuración", "cambiar configuracion")):
            return "config"

        # 2. Behavioral rule modification triggers
        rule_triggers = [
            "a partir de ahora", "de ahora en adelante", "recuerda esta regla", "recuerda la regla",
            "agrega una regla", "añade una regla", "nueva regla", "guarda esta regla",
            "aumentar capacidades", "aumenta tus capacidades", "nueva capacidad", "aprende que",
            "haz que el coach sea", "haz que el advisor sea", "quiero que el coach", "quiero que el advisor",
            "sé más", "se mas", "no me recomiendes", "descarta siempre", "prioriza siempre",
        ]
        if any(trigger in p for trigger in rule_triggers):
            return "rule"

        # 3. System prompt / tone tuning
        prompt_triggers = [
            "cambia tu prompt", "mejora tu prompt", "cambia tu tono", "habla más rápido", "habla mas rapido",
            "sé más breve", "se mas breve", "modo táctico", "modo tactico",
        ]
        if any(trigger in p for trigger in prompt_triggers):
            return "prompt"

        # 4. RAG fact ingestion triggers
        rag_triggers = [
            "registra el dato", "registra este dato", "agrega a la base de datos", "guarda que el objeto",
            "registra que", "guarda que el rifle", "guarda que la bala",
        ]
        if any(trigger in p for trigger in rag_triggers):
            return "rag"

        return None

    def is_vague(self, prompt: str) -> bool:
        """Evaluate if the user directive lacks specific actionable parameters."""
        p = prompt.strip().lower()

        # Check for explicitly vague phrases
        vague_signals = [
            "más inteligente", "mas inteligente", "mejor con el loot", "ayúdame mejor", "ayudame mejor",
            "quiero que seas mejor", "optimiza todo", "sé más pro", "se mas pro",
            "ayúdame más", "ayudame mas", "mejora tu comportamiento",
        ]
        if any(signal in p for signal in vague_signals):
            return True

        # If it's a short command (< 7 words) that uses general superlatives without concrete parameters
        words = p.split()
        if len(words) <= 7:
            if any(w in words for w in ("mejor", "rápido", "inteligente", "bueno", "loot", "combate")):
                # Check if it has concrete numbers, tier levels, item names, or key bindings
                has_concrete = any(c.isdigit() for c in p) or any(
                    k in p for k in ("tier", "f8", "f9", "salome", "salomé", "koen", "morado", "dorado", "m80")
                )
                if not has_concrete:
                    return True

        return False

    def generate_clarification(self, prompt: str, context_id: str) -> MetaTuningResult:
        """Generate a clarifying question offering discrete actionable options."""
        p = prompt.strip().lower()
        ctx = self.archetype_mgr.get_context(context_id)
        dname = ctx.display_name if ctx else context_id.title()

        category = "general"
        if any(w in p for w in ("loot", "inventario", "mochila", "alijo", "objetos")):
            category = "loot"
            question = (
                f"Para afinar mi criterio de loot en {dname}: "
                f"¿Deseas que priorice el valor económico por casilla, que filtre solo objetos de tier alto (morado o dorado), "
                f"o que te avise sobre objetos requeridos para contratos y crafteo?"
            )
        elif any(w in p for w in ("combate", "pelea", "disparo", "arma", "balas")):
            category = "combat"
            question = (
                f"Para calibrar mi asistencia en combate: "
                f"¿Prefieres que priorice penetración máxima contra blindajes pesados, "
                f"builds de armas de bajo retroceso, o tácticas de posicionamiento y flanqueo?"
            )
        elif any(w in p for w in ("voz", "audio", "habla", "rápido", "rapido", "breve")):
            category = "voice"
            question = (
                f"Para ajustar mi sistema de voz: "
                f"¿Deseas respuestas breves de una sola frase, cambiar a una voz más rápida del catálogo, "
                f"o desactivar las confirmaciones verbales?"
            )
        else:
            question = (
                f"Para aplicar este ajuste exactamente como prefieres: "
                f"¿Podrías especificar qué regla concreta, umbral numérico o comportamiento deseas que modifique?"
            )

        self.pending_clarification = {
            "original_prompt": prompt,
            "context_id": context_id,
            "category": category,
            "timestamp": time.time(),
        }

        return MetaTuningResult(
            action_taken="clarification_needed",
            spoken_response=question,
            report_path=None,
            is_clarification=True,
            target_type="rule",
            details={"pending_category": category, "original_prompt": prompt},
        )

    def apply_clarification_response(self, response_text: str, context_id: str) -> MetaTuningResult:
        """Apply the user's answer to a pending clarification."""
        clarification_data = self.pending_clarification or {}
        self.pending_clarification = None

        category = clarification_data.get("category", "general")
        resp_lower = response_text.strip().lower()

        # Build clean title and slug
        if "casilla" in resp_lower or "valor" in resp_lower:
            title = "Prioridad de Loot por Casilla"
            slug = "loot_value_per_slot"
            what = "Priorizar estrictamente objetos con mayor valor económico estimado por casilla de inventario."
            learned = "Descartar objetos voluminosos de bajo valor unitario para maximizar rentabilidad."
        elif "morado" in resp_lower or "dorado" in resp_lower or "tier" in resp_lower:
            title = "Filtro de Objetos de Alto Tier"
            slug = "high_tier_loot_only"
            what = "Filtrar y alertar únicamente sobre objetos morados, dorados o de Tier 4 o superior."
            learned = "Ignorar loot común o gris para acelerar el ritmo de juego."
        elif "contrato" in resp_lower or "craft" in resp_lower or "mision" in resp_lower:
            title = "Objetos de Contratos y Crafteo"
            slug = "quest_craft_items"
            what = "Destacar objetos requeridos para contratos de comerciantes o materiales raros de crafteo."
            learned = "Notificar inmediatamente cuando un objeto coincida con contratos activos."
        elif "penetracion" in resp_lower or "penetración" in resp_lower or "blindaje" in resp_lower:
            title = "Prioridad Balística: Penetración Máxima"
            slug = "max_penetration"
            what = "Recomendar exclusivamente munición con penetración capaz de perforar blindajes pesados."
            learned = "Evitar munición de daño a extremidades cuando el objetivo porte armadura Tier 5 o 6."
        elif "retroceso" in resp_lower or "build" in resp_lower:
            title = "Builds de Bajo Retroceso"
            slug = "low_recoil_builds"
            what = "Priorizar estabilidad y reducción de retroceso vertical y horizontal en modificaciones de armas."
            learned = "Favorecer empuñaduras y bocachas de compensación sobre ergonomía pura."
        else:
            title = f"Regla Personalizada: {category.title()}"
            slug = f"{category}_{int(time.time())}"
            what = f"Regla establecida: {response_text.strip()}"
            learned = "Comportamiento calibrado a petición del jugador."

        obs = EngramObservation(
            context_id=context_id,
            scope="project",
            topic_key=f"{context_id}/rules/{slug}",
            observation_type="rule",
            title=title,
            content=f"**What**: {what}\n**Why**: Calibración conversacional del copiloto.\n**Where**: Contexto {context_id}.\n**Learned**: {learned}",
            pinned=True,
        )
        self.archetype_mgr.save_engram_observation(obs)

        # Generate report for DISPLAY2
        html_body = f"""
        <div class="card">
            <h2>🧠 Nueva Regla Persistente Activada</h2>
            <div class="badge-row" style="margin-top: 10px; margin-bottom: 15px;">
                <span class="badge badge-purple">Contexto: {context_id}</span>
                <span class="badge badge-green">Tipo: Regla Táctica</span>
                <span class="badge badge-blue">Estado: Persistido en Engram</span>
            </div>
            <p style="color: #f3f4f6; font-size: 1.1em; margin-bottom: 10px;"><strong>{title}</strong></p>
            <p style="color: #9ca3af; line-height: 1.6;">{what}</p>
        </div>
        """
        report_path = None
        try:
            p = create_html_report(
                title=f"Regla: {title}",
                html_body=html_body,
                output_dir=self.config.reports.output_dir,
                auto_open=self.config.reports.auto_open_browser,
                opener=self.report_opener,
                preferred_browser=self.config.reports.preferred_browser,
                focus_browser=getattr(self.config.reports, "focus_browser", False),
            )
            report_path = str(p)
        except Exception:
            pass

        spoken = f"He calibrado mi criterio y guardado la regla de {title} en mi memoria persistente. Te abrí los detalles en tu pantalla secundaria."
        return MetaTuningResult(
            action_taken="rule_saved",
            spoken_response=spoken,
            report_path=report_path,
            is_clarification=False,
            target_type="rule",
            details={"title": title, "topic_key": obs.topic_key},
        )

    def apply_tuning(self, prompt: str, context_id: str) -> MetaTuningResult:
        """Apply a direct, unambiguous meta-tuning directive."""
        intent = self.detect_intent(prompt) or "rule"
        p_lower = prompt.lower().strip()

        # 1. Configuration updates (e.g., config.yaml)
        if intent == "config":
            return self._apply_config_update(prompt)

        # 2. Fact ingestion into RAG
        if intent == "rag":
            return self._apply_rag_ingest(prompt, context_id)

        # 3. Direct rule persistence in Engram observations
        clean_text = prompt
        for prefix in ("a partir de ahora", "de ahora en adelante", "recuerda esta regla", "agrega una regla", "aprende que"):
            if prefix in p_lower:
                idx = p_lower.find(prefix) + len(prefix)
                clean_text = prompt[idx:].strip().lstrip(",:.- ")
                break

        title = "Regla de Comportamiento"
        if len(clean_text) > 40:
            words = clean_text.split()
            title = " ".join(words[:5]).title()
        elif clean_text:
            title = clean_text.title()

        slug = "".join(c if c.isalnum() else "_" for c in title.lower())[:30].strip("_")
        obs = EngramObservation(
            context_id=context_id,
            scope="project",
            topic_key=f"{context_id}/rules/{slug}",
            observation_type="rule",
            title=title,
            content=f"**What**: {clean_text}\n**Why**: Instrucción directa del jugador.\n**Where**: Contexto {context_id}.\n**Learned**: Aplicar en cada interacción relevante.",
            pinned=True,
        )
        self.archetype_mgr.save_engram_observation(obs)

        spoken = f"Entendido. He registrado la regla '{title}' en mi memoria persistente y la aplicaré de ahora en adelante."
        return MetaTuningResult(
            action_taken="rule_saved",
            spoken_response=spoken,
            report_path=None,
            is_clarification=False,
            target_type="rule",
            details={"title": title, "topic_key": obs.topic_key},
        )

    def _apply_config_update(self, prompt: str) -> MetaTuningResult:
        """Modify runtime AppConfig and persist changes to config.yaml."""
        p_lower = prompt.lower()
        applied_msg = ""
        key_modified = ""

        # Voice update
        voice_map = {
            "salome": "es-CO-SalomeNeural",
            "salomé": "es-CO-SalomeNeural",
            "elvira": "es-ES-ElviraNeural",
            "ximena": "es-ES-XimenaNeural",
            "camila": "es-PE-CamilaNeural",
            "paloma": "es-US-PalomaNeural",
            "dalia": "es-MX-DaliaNeural",
            "elena": "es-AR-ElenaNeural",
            "catalina": "es-CL-CatalinaNeural",
        }
        for v_name, v_id in voice_map.items():
            if f"voz a {v_name}" in p_lower or f"voz de {v_name}" in p_lower:
                self.config.speaker.voice = v_id
                key_modified = "speaker.voice"
                applied_msg = f"Cambié la voz del sistema a {v_name.title()} ({v_id})."
                self._save_config_key(["speaker", "voice"], v_id)
                break

        # PTT key update
        ptt_match = re.search(r"(?:tecla|ptt|push to talk)\s+(?:a\s+|en\s+)?(f[1-9]|f1[0-2])\b", p_lower)
        if ptt_match and not applied_msg:
            new_key = ptt_match.group(1).lower()
            self.config.listener.ptt_key = new_key
            key_modified = "listener.ptt_key"
            applied_msg = f"Cambié la tecla de Push-to-Talk a [{new_key.upper()}]."
            self._save_config_key(["listener", "ptt_key"], new_key)

        # Provider switch
        if "nvidia" in p_lower and ("proveedor" in p_lower or "usar nvidia" in p_lower):
            self.config.llm.provider = "nvidia"
            key_modified = "llm.provider"
            applied_msg = "Cambié el proveedor de Inteligencia Artificial a NVIDIA NIM."
            self._save_config_key(["llm", "provider"], "nvidia")
        elif "gemini" in p_lower and ("proveedor" in p_lower or "usar gemini" in p_lower):
            self.config.llm.provider = "gemini"
            key_modified = "llm.provider"
            applied_msg = "Cambié el proveedor de Inteligencia Artificial a Gemini Vision."
            self._save_config_key(["llm", "provider"], "gemini")

        if not applied_msg:
            applied_msg = "He recibido la solicitud de configuración global, pero requiero el parámetro exacto (ej. voz, tecla PTT o proveedor)."
            return MetaTuningResult(
                action_taken="clarification_needed",
                spoken_response=applied_msg,
                report_path=None,
                is_clarification=True,
                target_type="config",
            )

        spoken = f"{applied_msg} Los cambios fueron guardados permanentemente en config.yaml."
        return MetaTuningResult(
            action_taken="config_updated",
            spoken_response=spoken,
            report_path=None,
            is_clarification=False,
            target_type="config",
            details={"key": key_modified},
        )

    def _apply_rag_ingest(self, prompt: str, context_id: str) -> MetaTuningResult:
        """Ingest a discovered or specified fact into the topic knowledge base."""
        p_lower = prompt.lower()
        title = "Dato Táctico Ingestado"
        category = "equipment"

        if "rifle" in p_lower or "arma" in p_lower or "pistola" in p_lower:
            category = "weapon"
        elif "bala" in p_lower or "municion" in p_lower or "munición" in p_lower:
            category = "ammo"
        elif "loot" in p_lower or "objeto" in p_lower:
            category = "loot"

        entity = self.scaffolder.auto_ingest_fact(
            context_id=context_id,
            category=category,
            title=prompt[:40].strip(),
            summary=prompt.strip(),
            facets={"source_prompt": prompt},
        )

        spoken = f"He indexado la información sobre {entity.title} en la base de conocimientos de {context_id}."
        return MetaTuningResult(
            action_taken="rag_ingested",
            spoken_response=spoken,
            report_path=None,
            is_clarification=False,
            target_type="rag",
            details={"entity_key": entity.entity_key},
        )

    def _save_config_key(self, key_path: List[str], value: Any) -> None:
        """Safely patch a key in config.yaml."""
        p = Path(self.config_path)
        if not p.is_file():
            return
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            cur = data
            for k in key_path[:-1]:
                if k not in cur or not isinstance(cur[k], dict):
                    cur[k] = {}
                cur = cur[k]
            cur[key_path[-1]] = value
            p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
        except Exception:
            pass

    def process(self, prompt: str, context_id: str) -> Optional[MetaTuningResult]:
        """Process an incoming prompt through the meta-tuning pipeline."""
        # 1. Check if user is responding to a pending clarification
        if self.pending_clarification:
            return self.apply_clarification_response(prompt, context_id)

        # 2. Detect meta-tuning intent
        intent = self.detect_intent(prompt)
        if intent is None:
            return None

        # 3. Check for vagueness
        if self.is_vague(prompt):
            return self.generate_clarification(prompt, context_id)

        # 4. Direct actionable tuning
        return self.apply_tuning(prompt, context_id)
