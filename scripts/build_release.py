"""Build and bundle standalone Windows release for LLM Game Advisor."""

from pathlib import Path
import shutil
import subprocess
import sys


def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    root = Path(__file__).resolve().parent.parent
    spec_path = root / "game_advisor.spec"
    dist_dir = root / "dist" / "game-advisor"

    print(">> Iniciando compilacion de Game Advisor para Windows...", flush=True)
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", str(spec_path)]
    res = subprocess.run(cmd, cwd=root)
    if res.returncode != 0:
        print(f"[ERROR] Error durante la compilacion de PyInstaller (codigo {res.returncode})")
        sys.exit(res.returncode)

    print(">> Organizando archivos complementarios en la carpeta de distribucion...")

    # 1. Copiar config.yaml al directorio raíz de la distribución si no está
    src_config = root / "config.yaml"
    dst_config = dist_dir / "config.yaml"
    if src_config.is_file() and not dst_config.is_file():
        shutil.copy2(src_config, dst_config)
        print("  * config.yaml copiado a dist/")

    # 2. Copiar keys.env.example y crear keys.env por defecto
    src_keys_ex = root / "keys.env.example"
    dst_keys_ex = dist_dir / "keys.env.example"
    dst_keys_env = dist_dir / "keys.env"
    if src_keys_ex.is_file():
        shutil.copy2(src_keys_ex, dst_keys_ex)
        if not dst_keys_env.is_file():
            shutil.copy2(src_keys_ex, dst_keys_env)
            print("  * keys.env generado en dist/ listo para que el usuario ingrese sus claves")

    # 3. Asegurar que presets/ esté accesible en la raíz del release
    src_presets = root / "presets" if (root / "presets").is_dir() else root / "src" / "abi_coach" / "presets"
    dst_presets = dist_dir / "presets"
    if src_presets.is_dir() and not dst_presets.is_dir():
        shutil.copytree(src_presets, dst_presets, dirs_exist_ok=True)
        print("  * presets/ copiado a dist/")

    # 4. Asegurar que data/ esté accesible en la raíz del release
    src_data = root / "src" / "abi_coach" / "data" if (root / "src" / "abi_coach" / "data").is_dir() else root / "data"
    dst_data = dist_dir / "data"
    if src_data.is_dir():
        dst_data.mkdir(parents=True, exist_ok=True)
        for f in src_data.glob("*.json"):
            shutil.copy2(f, dst_data / f.name)
        print("  * data/ copiado a dist/")

    # 5. Crear guía rápida para el usuario final (LEEME.txt)
    readme_path = dist_dir / "LEEME.txt"
    readme_content = """==============================================================================
  LLM GAME ADVISOR — Copiloto Táctico y Analista por Voz para Videojuegos
==============================================================================

¡Bienvenido! Este paquete es completamente portable y autónomo.

PASOS RÁPIDOS DE CONFIGURACIÓN:
------------------------------------------------------------------------------
1. Abre el archivo 'keys.env' con el Bloc de notas.
2. Agrega tu clave de API de Google Gemini (puedes obtenerla gratis en):
   https://aistudio.google.com/
   
   Ejemplo:
   GEMINI_API_KEY="AIzaSyTuClaveDeGoogleGemini..."

3. (Opcional) Si prefieres usar modelos de NVIDIA NIM, coloca:
   NVIDIA_API_KEY="nvapi-..."
   y activa 'llm.provider: nvidia' en config.yaml.

4. Guarda 'keys.env' e inicia 'game-advisor.exe'.

COMANDOS Y PRUEBAS RÁPIDAS:
------------------------------------------------------------------------------
Puedes abrir un PowerShell o CMD en esta carpeta y ejecutar diagnósticos:
  • Probar micrófono y Whisper local:
      .\\game-advisor.exe --test-mic

  • Probar captura de pantalla:
      .\\game-advisor.exe --test-capture

  • Probar síntesis de voz (TTS):
      .\\game-advisor.exe --test-tts "Hola, soy tu copiloto táctico"

  • Ver catálogo de voces naturales disponibles:
      .\\game-advisor.exe --list-voices

  • Iniciar en modo multijuego universal:
      .\\game-advisor.exe --game generic

  • Iniciar en modo Arena Breakout Infinite:
      .\\game-advisor.exe --game abi

USO EN PARTIDA:
------------------------------------------------------------------------------
Por defecto, mantén presionada la tecla F9 para hablarle a tu copiloto o usa la
detección automática por umbral de voz (VAD) según lo configurado en config.yaml.
Los informes tácticos y gráficos comparativos interactivos se abrirán
automáticamente en tu segundo monitor.
==============================================================================
"""
    readme_path.write_text(readme_content, encoding="utf-8")
    print("  * LEEME.txt generado con exito en dist/")

    print("\n[OK] Release generado exitosamente en:")
    print(f"   {dist_dir.resolve()}")


if __name__ == "__main__":
    main()
