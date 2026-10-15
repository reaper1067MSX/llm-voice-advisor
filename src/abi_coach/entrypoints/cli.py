"""Command line interface and diagnostic tools (Entrypoints Layer)."""

import argparse
import os
import sys

from abi_coach.core.audio.listener import AudioListener
from abi_coach.core.audio.speaker import Speaker
from abi_coach.core.config import load_config
from abi_coach.core.vision.capture import capture_screen
from abi_coach.entrypoints.loop import run_interactive_loop
from abi_coach.orchestration.brain import Brain


def check_api_keys(config) -> bool:
    """Verifica si las claves necesarias de API están configuradas y orienta amigablemente al usuario."""
    provider = getattr(config.llm, "provider", "gemini").lower()
    missing = False
    provider_name = "Google Gemini"
    key_name = "GEMINI_API_KEY"
    url = "https://aistudio.google.com/"

    if provider == "gemini":
        api_key = config.gemini.api_key or os.getenv("GEMINI_API_KEY")
        if not api_key or api_key.strip() in ("", "tu_clave_de_gemini_aqui"):
            missing = True
    elif provider == "nvidia":
        provider_name = "NVIDIA NIM"
        key_name = "NVIDIA_API_KEY"
        url = "https://build.nvidia.com/"
        api_key = getattr(config.llm.nvidia, "api_key", None) or os.getenv("NVIDIA_API_KEY")
        if not api_key or api_key.strip() in ("", "tu_clave_de_nvidia_aqui"):
            missing = True

    if missing:
        print("\n" + "=" * 74, flush=True)
        print(" ⚠️  LLM GAME ADVISOR — CONFIGURACIÓN DE CLAVES REQUERIDA", flush=True)
        print("=" * 74, flush=True)
        print(f" No se encontró una clave de API válida para {provider_name}.", flush=True)
        print("\n Pasos para comenzar a usar el asesor:", flush=True)
        print(" 1. Abre el archivo 'keys.env' (ubicado junto a este ejecutable).", flush=True)
        print(f" 2. Obtén tu clave en: {url}", flush=True)
        print(" 3. Escribe tu clave dentro de 'keys.env':", flush=True)
        print(f'    {key_name}="tu_clave_aqui"', flush=True)
        print(" 4. Guarda los cambios e inicia la aplicación nuevamente.", flush=True)
        print("=" * 74 + "\n", flush=True)
        if sys.stdin.isatty():
            try:
                input("Presiona ENTER para salir...")
            except Exception:
                pass
        return False
    return True


def cmd_list_models(config) -> None:
    """List available Gemini models for the current API key."""
    from google import genai

    if not check_api_keys(config):
        sys.exit(1)

    api_key = config.gemini.api_key or os.getenv("GEMINI_API_KEY")

    print("🔍 Conectando con Google AI Studio...")
    client = genai.Client(api_key=api_key)
    models = list(client.models.list())
    print("\nModelos disponibles:")
    for m in models:
        name = getattr(m, "name", str(m))
        display = getattr(m, "display_name", "")
        print(f"  • {name} ({display})")


def cmd_test_capture(config) -> None:
    """Test screen capture on the configured monitor."""
    print("📸 Tomando captura del monitor configurado...")
    config.capture.save_captures = True
    result = capture_screen(config.capture)

    print("\n✅ Captura exitosa:")
    print(f"  • Tamaño original: {result.original_size[0]}x{result.original_size[1]}")
    print(f"  • Tamaño procesado (Lanczos): {result.processed_size[0]}x{result.processed_size[1]}")
    print(f"  • Peso JPEG comprimido: {len(result.full_image_bytes) / 1024:.1f} KB")
    print(f"  • Tiempo de captura de SO: {result.capture_time_ms:.1f} ms")
    print(f"  • Tiempo total (captura + downscale + compresión): {result.total_time_ms:.1f} ms")
    if config.capture.capture_dir:
        print(f"  • Guardada en carpeta: {config.capture.capture_dir}/")


def cmd_test_tts(config, text: str) -> None:
    """Test text-to-speech engine with sample text."""
    speaker = Speaker(config.speaker)
    print(f"🔊 Probando voz '{config.speaker.voice}'...")
    print(f'Texto: "{text}"')
    speaker.speak(text)
    print("✅ Reproducción finalizada.")


def cmd_test_mic(config) -> None:
    """Record 3 seconds from microphone and transcribe using faster-whisper."""
    print("🎙️ Inicializando motor Whisper en GPU...")
    listener = AudioListener(config.listener)
    listener.init_whisper()
    print("Habla ahora durante 3 segundos...")
    transcript = listener.record_seconds(3.0)
    if transcript:
        print(f'\n✅ Transcripción exitosa: "{transcript}"')
    else:
        print("\n⚠️ No se detectó voz clara o el volumen fue demasiado bajo.")


def cmd_ask(config, prompt: str) -> None:
    """Ask a question using text prompt + live screen capture without microphone."""
    print(f'💬 Pregunta: "{prompt}"', flush=True)
    print("📸 Capturando pantalla...", flush=True)
    capture_res = capture_screen(config.capture)
    print(f"  • Captura lista en {capture_res.total_time_ms:.1f} ms ({len(capture_res.full_image_bytes) / 1024:.1f} KB)", flush=True)

    print(f"🧠 Consultando con {config.gemini.model}...", flush=True)
    brain = Brain(config)
    speaker = Speaker(config.speaker)

    resp = brain.ask(
        prompt=prompt,
        image_bytes=capture_res.full_image_bytes,
        crop_bytes=capture_res.crop_bytes,
    )

    print("\n🎯 Respuesta del Coach:", flush=True)
    print(f"{resp.spoken_text}\n", flush=True)
    if resp.report_path:
        print(f"📊 Informe HTML abierto en navegador: {resp.report_path}", flush=True)

    tokens_info = []
    if resp.input_tokens:
        tokens_info.append(f"Prompt: {resp.input_tokens} tok")
    if resp.output_tokens:
        tokens_info.append(f"Respuesta: {resp.output_tokens} tok")
    tok_str = " | ".join(tokens_info) if tokens_info else "N/A"
    print(f"⏱️ Latencia: {resp.latency_ms:.1f} ms | Tokens: {tok_str}", flush=True)

    print("🔊 Reproduciendo respuesta por voz...", flush=True)
    speaker.speak(resp.spoken_text)
    print("✅ Respuesta finalizada.", flush=True)


def cmd_list_voices() -> None:
    """Print the curated catalogue of natural female voices."""
    print("\n" + "=" * 70, flush=True)
    print("      🎙️ CATÁLOGO DE VOCES FEMENINAS NATURALES (EDGE-TTS)", flush=True)
    print("=" * 70, flush=True)
    voices = [
        ("es-CO-SalomeNeural", "Salomé (Colombia)", "Cálida, dulce, muy humana y fluida (⭐ Recomendada)"),
        ("es-ES-ElviraNeural", "Elvira (España)", "Expresiva, natural, clara y con excelente prosodia"),
        ("es-ES-XimenaNeural", "Ximena (España)", "Joven, moderna, enérgica y dinámica"),
        ("es-PE-CamilaNeural", "Camila (Perú)", "Suave, pausada, amigable y muy clara"),
        ("es-US-PalomaNeural", "Paloma (EE.UU. / Neutro)", "Neutra, ágil y conversacional"),
        ("es-MX-DaliaNeural", "Dalia (México)", "Profesional, directa y formal"),
        ("es-AR-ElenaNeural", "Elena (Argentina)", "Natural, con cadencia rítmica argentina"),
        ("es-CL-CatalinaNeural", "Catalina (Chile)", "Natural y conversacional"),
    ]
    for vid, name, desc in voices:
        print(f"  • {vid:<22} | {name:<22} | {desc}", flush=True)
    print("=" * 70, flush=True)
    print("Para probar una voz: uv run python -m abi_coach.main --test-tts \"Hola soy tu coach\" --voice <id>", flush=True)
    print("Para usarla fijamente: cámbiala en el archivo config.yaml\n", flush=True)


def main() -> None:
    # Ensure UTF-8 output on Windows consoles
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="LLM Game Advisor - Copiloto Táctico Multimodal por Voz")
    parser.add_argument("--config", type=str, default=None, help="Ruta al archivo config.yaml")
    parser.add_argument("--game", type=str, default=None, help="Preset de juego: 'abi' (Arena Breakout) o 'generic' (Asesor multijuego)")
    parser.add_argument("--list-models", action="store_true", help="Listar modelos disponibles en Google AI Studio")
    parser.add_argument("--list-voices", action="store_true", help="Listar catálogo de voces femeninas naturales")
    parser.add_argument("--voice", type=str, default=None, help="Voz temporal para probar con --test-tts")
    parser.add_argument("--test-capture", action="store_true", help="Probar captura de pantalla a nivel de SO")
    parser.add_argument("--test-tts", type=str, default=None, help="Probar motor de voz con el texto indicado")
    parser.add_argument("--test-mic", action="store_true", help="Probar micrófono y transcripción local Whisper")
    parser.add_argument("--ask", type=str, default=None, help="Hacer una consulta con texto y captura sin usar micro")

    args = parser.parse_args()
    cfg = load_config(args.config)

    if args.game:
        cfg.gemini.game = args.game

    if args.voice:
        cfg.speaker.voice = args.voice

    if args.list_models:
        cmd_list_models(cfg)
    elif args.list_voices:
        cmd_list_voices()
    elif args.test_capture:
        cmd_test_capture(cfg)
    elif args.test_tts is not None:
        cmd_test_tts(cfg, args.test_tts)
    elif args.test_mic:
        cmd_test_mic(cfg)
    elif args.ask is not None:
        if not check_api_keys(cfg):
            sys.exit(1)
        cmd_ask(cfg, args.ask)
    else:
        if not check_api_keys(cfg):
            sys.exit(1)
        run_interactive_loop(cfg)


if __name__ == "__main__":
    main()
