"""Main entry point and CLI for ABI Voice Coach."""

import argparse
import os
import sys
import time
from typing import Optional

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from abi_coach.brain import Brain
from abi_coach.capture import capture_screen
from abi_coach.config import load_config
from abi_coach.listener import AudioListener
from abi_coach.speaker import Speaker


BANNER = """
==================================================================
           {title}
==================================================================
  * Preset de juego: {game_display}
  * Optimizado para 1440p (DISPLAY1) + Navegador en DISPLAY2
  * Push-to-Talk: Mantén presionado [{key}] para hablar
  * Transcripción local en GPU: {gpu}
  * Voz de respuesta: {voice}
  * Modelo visual: {model}
==================================================================
"""


def cmd_list_models(config) -> None:
    """List available Gemini models for the current API key."""
    from google import genai

    api_key = config.gemini.api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: No se encontró GEMINI_API_KEY. Configúrala en .env")
        sys.exit(1)

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
    print(f"Texto: \"{text}\"")
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
        print(f"\n✅ Transcripción exitosa: \"{transcript}\"")
    else:
        print("\n⚠️ No se detectó voz clara o el volumen fue demasiado bajo.")


def cmd_ask(config, prompt: str) -> None:
    """Ask a question using text prompt + live screen capture without microphone."""
    print(f"💬 Pregunta: \"{prompt}\"", flush=True)
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


import atexit
import ctypes
import signal
import threading
import sounddevice as sd


def should_inspect_screen(prompt: str) -> bool:
    """Infer if question requires examining the live screen or is conceptual/strategic."""
    p = prompt.lower().strip()

    # 1. Direct visual triggers
    visual_triggers = [
        "mira", "mirá", "mire", "miren", "observa", "fijate", "fíjate", "revisa", "analiza mi pantalla",
        "en pantalla", "mi pantalla", "la pantalla", "ves", "veo", "viendo",
    ]
    if any(trigger in p for trigger in visual_triggers):
        return True

    # 2. Deictic references (referring to something currently displayed)
    deictic_patterns = [
        " esto", "esta ", "este ", "estos ", "estas ", " aqui", " acá", " acá",
        "cuál me llevo", "cuál guardo", "qué me llevo", "qué guardo", "vale la pena lootear",
        "dónde estoy", "donde estoy", "por dónde salgo", "por donde salgo", "hacia dónde voy",
    ]
    if any(pat in p for pat in deictic_patterns):
        return True

    # 3. In-game object & inventory references
    context_triggers = [
        "mi alijo", "en mi alijo", "mi inventario", "en mi inventario", "mi mochila",
        "este cuerpo", "el cuerpo", "esta caja", "el cadáver", "el cadaver",
        "cuánto vale esto", "a cuánto se vende esto", "precio de esto",
    ]
    if any(ctx in p for ctx in context_triggers):
        return True

    return False


def run_interactive_loop(config) -> None:
    """Start the main event-driven Push-to-Talk coach loop."""
    game_lower = (config.gemini.game or "generic").lower().strip()
    if game_lower in ("abi", "arena_breakout", "arena_breakout_infinite", "arena-breakout"):
        title_str = "🎯 ABI TACTICAL COACH - Arena Breakout: Infinite"
        game_display = "Arena Breakout: Infinite (S7 Balística & Alijo)"
    else:
        title_str = "🎮 GAME ADVISOR - AI Gaming Voice Co-pilot"
        game_display = "Universal / Multijuego (Análisis en vivo de pantalla)"

    active_provider = getattr(config.llm, "provider", "gemini").lower()
    active_model = config.nvidia.model if active_provider == "nvidia" else config.gemini.model
    provider_label = "NVIDIA NIM" if active_provider == "nvidia" else "Gemini Vision"

    print(
        BANNER.format(
            title=title_str,
            game_display=game_display,
            key=config.listener.ptt_key.upper(),
            gpu=f"{config.listener.whisper_device.upper()} ({config.listener.whisper_compute_type})",
            voice=config.speaker.voice,
            model=f"{provider_label} ({active_model})",
        ),
        flush=True,
    )

    print("🚀 Inicializando componentes del Coach...", flush=True)
    print(f"  [1/4] 🔊 Configurando motor de voz TTS ({config.speaker.voice})...", flush=True)
    speaker = Speaker(config.speaker)
    print(f"  [2/4] 🎙️ Cargando faster-whisper ({config.listener.whisper_model}) en GPU ({config.listener.whisper_device.upper()})...", flush=True)
    listener = AudioListener(config.listener)
    listener.init_whisper()
    print(f"  [3/4] 🧠 Conectando con {provider_label} ({active_model})...", flush=True)
    brain = Brain(config)
    print("  [4/4] 🎧 Abriendo stream de micrófono y búfer circular (16 kHz)...", flush=True)
    listener.start_stream()

    # Setup 100% clean teardown on exit, Ctrl+C, or window close
    is_shutting_down = False

    def cleanup_and_exit(signum=None, frame=None):
        nonlocal is_shutting_down
        if is_shutting_down:
            return
        is_shutting_down = True
        print("\n🛑 Cerrando ABI Voice Coach y liberando recursos (audio, GPU, hilos)...", flush=True)
        try:
            speaker.stop()
        except Exception:
            pass
        try:
            listener.stop_ptt_loop()
            listener.close()
        except Exception:
            pass
        try:
            sd.stop()
        except Exception:
            pass
        print("✅ Todo cerrado limpiamente. ¡Hasta la próxima raid!\n", flush=True)
        # os._exit immediately terminates all threads, bypasses any hung C-extensions,
        # and guarantees zero orphan python.exe processes remain in Task Manager.
        os._exit(0)

    # Register standard signals
    signal.signal(signal.SIGINT, cleanup_and_exit)
    signal.signal(signal.SIGTERM, cleanup_and_exit)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, cleanup_and_exit)
    atexit.register(cleanup_and_exit)

    # Register Windows console close handler (handles clicking the 'X' button on console window)
    if sys.platform == "win32":
        HandlerRoutine = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong)

        def win_ctrl_handler(ctrl_type):
            cleanup_and_exit()
            return True

        global_handler = HandlerRoutine(win_ctrl_handler)
        ctypes.windll.kernel32.SetConsoleCtrlHandler(global_handler, True)

    target_key = config.listener.ptt_key.upper()
    is_vad = config.listener.mode.lower() in ("continuous", "hybrid")
    mode_title = "🎙️ MODO MANOS LIBRES ACTIVO (Detección de voz automática)" if is_vad else f"🔘 MODO PUSH-TO-TALK (Tecla [{target_key}])"

    print("\n" + "=" * 66, flush=True)
    print("✅ ¡ABI Voice Coach listo para el combate!", flush=True)
    print(f"   {mode_title}", flush=True)
    if is_vad:
        print("👉 Simplemente HABLA cuando quieras en tu micrófono (sin tocar teclas).")
        print(f"   (También puedes usar [{target_key}] si prefieres pulsar).")
    else:
        print(f"👉 Mantén presionado [{target_key}] mientras hablas y suéltalo al terminar.")
    print("   • Al detectar voz: bip agudo + captura de pantalla + grabación.")
    print("   • Al callar: bip grave + transcripción GPU + análisis Gemini + respuesta por voz.")
    print("   • Para salir: Presiona Ctrl+C o cierra la ventana (liberación total de memoria).", flush=True)
    print("=" * 66 + "\n", flush=True)

    # Vocal greeting to confirm sound output and indicate readiness
    greeting = "Hola, soy tu coach táctico. Estoy listo y atento a tu partida. Hazme cualquier pregunta."
    print("🔊 Saludando por voz en tus auriculares...", flush=True)
    listener.pause_listening()
    try:
        speaker.speak(greeting)
    finally:
        listener.resume_listening()
    print("🎧 Esperando tus preguntas...\n", flush=True)

    latest_capture = None

    def on_press():
        nonlocal latest_capture
        speaker.stop()
        # Capture screen in background worker thread so it never blocks audio recording or PTT polling
        def do_capture():
            nonlocal latest_capture
            try:
                latest_capture = capture_screen(config.capture)
            except Exception as e:
                print(f"\n⚠️ Error al capturar pantalla: {e}", flush=True)
                latest_capture = None

        t = threading.Thread(target=do_capture, daemon=True)
        t.start()

    def on_release(transcript: str):
        nonlocal latest_capture
        now_str = time.strftime("%H:%M:%S")
        print(f"[{now_str}] 🗣️ Tú preguntaste: \"{transcript}\"", flush=True)

        cap = latest_capture
        latest_capture = None

        # Smart visual inference
        needs_screen = should_inspect_screen(transcript)
        if needs_screen and cap:
            print(f"[{now_str}] 👁️ Consulta visual detectada (\"mira\" / deíctica). Analizando captura 1440p...", flush=True)
            img_bytes = cap.full_image_bytes
            crp_bytes = cap.crop_bytes
        else:
            print(f"[{now_str}] 💡 Consulta estratégica/conceptual (respuesta directa ultra-rápida)...", flush=True)
            img_bytes = None
            crp_bytes = None

        try:
            resp = brain.ask(
                prompt=transcript,
                image_bytes=img_bytes,
                crop_bytes=crp_bytes,
            )

            now_resp = time.strftime("%H:%M:%S")
            print(f"\n[{now_resp}] 🎯 Coach ({resp.latency_ms:.0f} ms):", flush=True)
            print(f"   \"{resp.spoken_text}\"\n", flush=True)
            if resp.report_path:
                print(f"📊 Tabla/Gráfico interactiva abierta en pantalla secundaria: {resp.report_path}", flush=True)

            print(f"[{now_resp}] 🔊 Reproduciendo consejo por voz en tus auriculares...", flush=True)
            # Mute listener while speaking to prevent the coach from hearing itself
            listener.pause_listening()
            try:
                speaker.speak(resp.spoken_text)
            finally:
                listener.resume_listening()

            print(f"[{time.strftime('%H:%M:%S')}] 🎧 Listo. Esperando tu siguiente pregunta...\n", flush=True)

        except Exception as e:
            print(f"❌ Error al procesar respuesta con la IA: {e}", flush=True)
            print("🎧 Listo. Esperando tu siguiente pregunta...\n", flush=True)

    # Setup global uncaught exception handler to prevent any orphan processes on crash
    def global_excepthook(exctype, value, tb):
        import traceback
        print("\n💥 Excepción inesperada detectada:", flush=True)
        traceback.print_exception(exctype, value, tb)
        cleanup_and_exit()

    sys.excepthook = global_excepthook

    try:
        listener.listen_ptt_loop(on_press, on_release)
    except KeyboardInterrupt:
        cleanup_and_exit()
    except Exception as e:
        import traceback
        print(f"\n💥 Error inesperado durante la ejecución: {e}", flush=True)
        traceback.print_exc()
        cleanup_and_exit()


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
        cmd_ask(cfg, args.ask)
    else:
        run_interactive_loop(cfg)


if __name__ == "__main__":
    main()
