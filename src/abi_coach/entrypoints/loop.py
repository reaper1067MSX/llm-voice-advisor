"""Event-driven interactive Push-to-Talk / Continuous VAD loop (Entrypoints Layer)."""

import atexit
import ctypes
import os
import signal
import sys
import threading
import time
from typing import Optional
import sounddevice as sd

from abi_coach.core.audio.listener import AudioListener
from abi_coach.core.audio.speaker import Speaker
from abi_coach.core.vision.capture import capture_screen
from abi_coach.orchestration.brain import Brain


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
        title_str = "🎮 GAME ADVISOR - AI Gaming Voice Co-pilot & Configurator"
        game_display = "Universal / Multijuego (Modo Advisor Onboarding)"

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
    print("   • Para salir: Presiona Ctrl+C o cierra la ventana (liberación total de memoria).")
    if game_lower not in ("abi", "arena_breakout", "arena_breakout_infinite", "arena-breakout"):
        print("   • 💡 Conmutador en caliente: Di 'Vamos a jugar [Juego]' para auto-configurar y activar otro juego.", flush=True)
    print("=" * 66 + "\n", flush=True)

    # Vocal greeting to confirm sound output and indicate readiness
    if game_lower in ("abi", "arena_breakout", "arena_breakout_infinite", "arena-breakout"):
        greeting = "Hola, soy tu coach táctico de Arena Breakout. Estoy listo y atento a tu partida. Hazme cualquier pregunta."
    else:
        greeting = "Hola, soy tu Game Advisor. Estoy listo para cualquier juego. Di 'Vamos a jugar' y el nombre del juego para configurarlo en caliente."
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
