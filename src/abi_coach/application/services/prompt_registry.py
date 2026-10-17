"""System prompt registry and dynamic preset loader for Tactical Copilots."""

from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Any, Callable, Dict, List, Optional

SYSTEM_INSTRUCTION_ABI = (
    "Eres 'ABI Coach', copiloto táctico y squadmate de élite para 'Arena Breakout: Infinite' (PC).\n"
    "Hablas directo al auricular del jugador con monitor secundario para dashboards tácticos.\n\n"
    "PERFIL: Compañero leal, analítico y directo en la zona oscura de Kamona. Jerga de extracción "
    "(alijo, Koens, contratos de Deke, tier de balas, penetración, TTK, leg meta). Disciplina de radio en combate.\n\n"
    "REGLAS:\n"
    "1. Voz (TTS): SIEMPRE español, profesional y ágil. Máximo 1 a 3 oraciones. NUNCA markdown en voz.\n"
    "2. Reportes (create_html_report): ESTRICTAMENTE BAJO DEMANDA. Solo si el jugador pide explícitamente "
    "tabla, gráfico o comparar. Generar tabla HTML estilizada y gráfico Chart.js (<280px). Indicar en voz que se abrió.\n"
    "3. Táctica: La munición define penetración y TTK. Priorizar valor por casilla y contratos de Deke. "
    "Honestidad si no distingues un objeto en pantalla."
)

SYSTEM_INSTRUCTION_GENERIC = (
    "Eres 'Game Advisor', copiloto táctico y squadmate con IA multimodal para PC en tiempo real.\n"
    "Hablas al auricular del jugador mientras juega en monitor principal con secundario para dashboards.\n\n"
    "PERFIL: Compañero leal, atento y analítico. Jerga gamer/militar natural. Disciplina de radio en acción. "
    "Honestidad estricta si no distingues detalles en pantalla.\n\n"
    "REGLAS:\n"
    "1. Voz (TTS): SIEMPRE español, ágil y motivador. 1 a 3 oraciones. NUNCA markdown en voz.\n"
    "2. Reportes (create_html_report): ESTRICTAMENTE BAJO DEMANDA. Solo con petición explícita. "
    "Card con tabla y Chart.js interactivo (<280px). Avisar en voz.\n"
    "3. Disciplina: Avisos de <5 palabras en peligro. Respetar silencio de radio."
)

SYSTEM_INSTRUCTION_ONCE_HUMAN = (
    "Eres 'Once Human Companion', copiloto táctico y metahumano experto en 'Once Human' (PC).\n"
    "Hablas al auricular del jugador con monitor secundario para dashboards.\n\n"
    "PERFIL: Compañero de clan leal y analítico en Nalcott. Dominas builds meta (Shrapnel, Unstable Bomber, "
    "Power Surge, Burn, Frost Vortex, Bounce). Fórmula 1-4-1 (1 Key Armor + 4 Lonewolf + 1 Bastille). "
    "Sufijos <Violent> y <Talent>. Silos de contención y monolitos.\n\n"
    "REGLAS:\n"
    "1. Voz (TTS): SIEMPRE español, 1 a 3 oraciones, sin markdown.\n"
    "2. Reportes (create_html_report): ESTRICTAMENTE BAJO DEMANDA. Tabla de piezas, mods, sufijos y silo. "
    "Chart.js (<280px). Avisar en voz.\n"
    "3. Disciplina de radio en combate intenso."
)

ABI_SYSTEM_INSTRUCTION = SYSTEM_INSTRUCTION_ABI
COACH_SYSTEM_INSTRUCTION = SYSTEM_INSTRUCTION_ABI
GENERIC_SYSTEM_INSTRUCTION = SYSTEM_INSTRUCTION_GENERIC
ONCE_HUMAN_SYSTEM_INSTRUCTION = SYSTEM_INSTRUCTION_ONCE_HUMAN

_PRESET_CACHE: Dict[str, str] = {}


def load_preset(game_name: str) -> str:
    """Load game system instruction markdown from presets directory with in-memory cache."""
    clean = (game_name or "").lower().strip()
    if clean in ("abi", "arena_breakout", "arena_breakout_infinite", "arena-breakout"):
        canonical = "abi"
    elif clean in ("once_human", "oncehuman", "once-human", "once human"):
        canonical = "once_human"
    elif clean:
        canonical = re.sub(r"[^a-z0-9]+", "_", clean).strip("_")
    else:
        canonical = "generic"

    if canonical in _PRESET_CACHE:
        return _PRESET_CACHE[canonical]

    candidates: List[Path] = []
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
        candidates.extend([base / "presets" / f"{canonical}.md", base / "presets" / f"{clean}.md"])
        if hasattr(sys, "_MEIPASS"):
            meipass = Path(sys._MEIPASS)
            candidates.extend([meipass / "presets" / f"{canonical}.md", meipass / "presets" / f"{clean}.md"])

    for p in Path(__file__).resolve().parents:
        for folder in ("presets", "infrastructure/resources/presets", "src/abi_coach/infrastructure/resources/presets"):
            candidates.append(p / folder / f"{canonical}.md")
            candidates.append(p / folder / f"{clean}.md")

    for cand in candidates:
        if cand.is_file():
            try:
                text = cand.read_text(encoding="utf-8").strip()
                _PRESET_CACHE[canonical] = text
                return text
            except Exception:
                pass

    fallbacks = {"abi": SYSTEM_INSTRUCTION_ABI, "once_human": SYSTEM_INSTRUCTION_ONCE_HUMAN}
    fallback = fallbacks.get(canonical, SYSTEM_INSTRUCTION_GENERIC)
    _PRESET_CACHE[canonical] = fallback
    return fallback


class PromptTemplateRegistry:
    """Registry and formatter for system prompts, dynamic presets, and memory enrichments."""

    def __init__(self, preset_loader: Callable[[str], str] = load_preset) -> None:
        self._preset_loader = preset_loader

    def get_preset(self, game_name: str) -> str:
        return self._preset_loader(game_name)

    def build_system_instruction(
        self,
        game_id: str,
        custom_instruction: Optional[str] = None,
        archetype_mgr: Optional[Any] = None,
        memory: Optional[Any] = None,
    ) -> str:
        """Compose the full system instruction with custom prompts, presets, and memory profiles."""
        gid = game_id or "generic"
        if custom_instruction:
            base_prompt = custom_instruction
        else:
            base_prompt = None
            if gid not in ("generic", "") and archetype_mgr:
                ctx = archetype_mgr.get_context(gid)
                if ctx:
                    arch = archetype_mgr.get_archetype(ctx.archetype_id)
                    if arch and arch.default_system_prompt:
                        base_prompt = f"Eres un copiloto táctico para '{ctx.display_name}'.\n{arch.default_system_prompt}"
            if not base_prompt:
                base_prompt = self.get_preset(gid)

        enrichments: List[str] = []
        if memory and hasattr(memory, "format_profile_for_prompt"):
            profile_context = memory.format_profile_for_prompt(game=gid)
            if profile_context:
                enrichments.append(profile_context)
        if archetype_mgr and hasattr(archetype_mgr, "format_profile_for_prompt"):
            engram_context = archetype_mgr.format_profile_for_prompt(context_id=gid)
            if engram_context:
                enrichments.append(engram_context)

        return f"{base_prompt}\n" + "\n".join(enrichments) if enrichments else base_prompt
