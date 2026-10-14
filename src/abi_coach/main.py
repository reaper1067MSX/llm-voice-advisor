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
           🎯 ABI VOICE COACH - Arena Breakout: Infinite
==================================================================
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
    listener.start_recording()
    time.sleep(3.0)
    print("Procesando y transcribiendo...")
    transcript = listener.stop_recording_and_transcribe()
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


def run_interactive_loop(config) -> None:
    """Start the main event-driven Push-to-Talk coach loop."""
    print(
        BANNER.format(
            key=config.listener.ptt_key.upper(),
            gpu=f"{config.listener.whisper_device.upper()} ({config.listener.whisper_compute_type})",
            voice=config.speaker.voice,
            model=config.gemini.model,
        ),
        flush=True,
    )

    print("🚀 Inicializando componentes...", flush=True)
    speaker = Speaker(config.speaker)
    listener = AudioListener(config.listener)
    listener.init_whisper()
    brain = Brain(config)

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

    print("✅ Coach listo. Entra a tu partida y mantén presionado la tecla cuando necesites consejo.", flush=True)
    print("   • Sonido 'bip' agudo: grabando audio y capturando pantalla.")
    print("   • Sonido 'bip' grave: procesando con Whisper GPU y Gemini.")
    print("Presiona Ctrl+C o cierra la ventana para salir.\n", flush=True)

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
        print("🎙️ [PTT Activo] Escuchando...", end="\r", flush=True)

    def on_release(transcript: str):
        nonlocal latest_capture
        print(f"\n🗣️ Tú: \"{transcript}\"", flush=True)
        cap = latest_capture
        latest_capture = None

        print("🧠 Coach analizando la situación...", flush=True)
        try:
            resp = brain.ask(
                prompt=transcript,
                image_bytes=cap.full_image_bytes if cap else None,
                crop_bytes=cap.crop_bytes if cap else None,
            )

            print(f"\n🎯 Coach: {resp.spoken_text}", flush=True)
            if resp.report_path:
                print(f"📊 Tabla/Gráfico abierta en navegador: {resp.report_path}", flush=True)

            tokens_info = []
            if resp.input_tokens:
                tokens_info.append(f"Input: {resp.input_tokens} tok")
            if resp.output_tokens:
                tokens_info.append(f"Output: {resp.output_tokens} tok")
            tok_str = " | ".join(tokens_info) if tokens_info else "Tokens N/A"
            print(f"⏱️ Latencia IA: {resp.latency_ms:.1f} ms | {tok_str}\n", flush=True)

            speaker.speak(resp.spoken_text)

        except Exception as e:
            print(f"❌ Error al procesar respuesta con la IA: {e}", flush=True)

    try:
        listener.listen_ptt_loop(on_press, on_release)
    except KeyboardInterrupt:
        cleanup_and_exit()


def main() -> None:
    parser = argparse.ArgumentParser(description="ABI Voice Coach - Copiloto Táctico para Arena Breakout Infinite")
    parser.add_argument("--config", type=str, default=None, help="Ruta al archivo config.yaml")
    parser.add_argument("--list-models", action="store_true", help="Listar modelos disponibles en Google AI Studio")
    parser.add_argument("--test-capture", action="store_true", help="Probar captura de pantalla a nivel de SO")
    parser.add_argument("--test-tts", type=str, default=None, help="Probar motor de voz con el texto indicado")
    parser.add_argument("--test-mic", action="store_true", help="Probar micrófono y transcripción local Whisper")
    parser.add_argument("--ask", type=str, default=None, help="Hacer una consulta con texto y captura sin usar micro")

    args = parser.parse_args()
    cfg = load_config(args.config)

    if args.list_models:
        cmd_list_models(cfg)
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
