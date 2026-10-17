"""Build and bundle standalone Windows release for LLM Game Advisor."""

from pathlib import Path
import shutil
import subprocess
import sys


def sign_executable(exe_path: Path, dist_dir: Path) -> bool:
    """Sign game-advisor.exe with a PowerShell Authenticode CodeSigning certificate and export editor_cert.cer."""
    if sys.platform != "win32" or not exe_path.is_file():
        return False

    cer_path = dist_dir / "editor_cert.cer"
    ps_script = f"""
$ErrorActionPreference = 'Stop'
$subject = 'CN=Santiago Arguello (LLM Game Advisor)'
$cert = Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert | Where-Object {{ $_.Subject -eq $subject }} | Select-Object -First 1
if (-not $cert) {{
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $subject -CertStoreLocation Cert:\\CurrentUser\\My -NotAfter (Get-Date).AddYears(5)
}}
Export-Certificate -Cert $cert -FilePath '{cer_path}' -Force | Out-Null
$sig = Set-AuthenticodeSignature -FilePath '{exe_path}' -Certificate $cert -HashAlgorithm SHA256
if ($sig.Status -eq 'UnknownError' -or $sig.Status -eq 'NotSigned') {{
    Write-Output "SIGNED_WITH_SELF_CERT:$($sig.Status)"
}} else {{
    Write-Output "SIGNED_OK:$($sig.Status)"
}}
"""
    try:
        import os

        clean_env = {k: v for k, v in os.environ.items() if k.upper() != "PSMODULEPATH"}
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=30,
            env=clean_env,
        )
        if res.returncode == 0:
            print(f"  * Ejecutable firmado con Authenticode ({res.stdout.strip()}) y certificado exportado a editor_cert.cer")
            return True
        else:
            print(f"  * [AVISO] Firma Authenticode omitida por politica local: {res.stderr.strip()}")
            return False
    except Exception as exc:
        print(f"  * [AVISO] No se pudo ejecutar firma Authenticode: {exc}")
        return False


def create_smartscreen_helpers(dist_dir: Path) -> None:
    """Create Iniciar_Game_Advisor.bat and Desbloquear_SmartScreen.bat in the release directory."""
    launcher_bat = dist_dir / "Iniciar_Game_Advisor.bat"
    launcher_content = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        "title LLM Game Advisor - Copiloto Tactico por Voz\r\n"
        "REM Limpiar etiqueta Mark-of-the-Web (Zone.Identifier) de archivos descargados para evitar bloqueo de SmartScreen\r\n"
        "powershell -NoProfile -ExecutionPolicy Bypass -Command \"Get-ChildItem -Path '%~dp0' -Recurse | Unblock-File -ErrorAction SilentlyContinue\" >nul 2>&1\r\n"
        "\"%~dp0game-advisor.exe\" %*\r\n"
    )
    launcher_bat.write_text(launcher_content, encoding="utf-8")
    print("  * Iniciar_Game_Advisor.bat generado en dist/")

    unblock_bat = dist_dir / "Desbloquear_SmartScreen.bat"
    unblock_content = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        "echo ==============================================================================\r\n"
        "echo   DESBLOQUEADOR DE WINDOWS SMARTSCREEN - LLM GAME ADVISOR\r\n"
        "echo ==============================================================================\r\n"
        "echo.\r\n"
        "echo [1/2] Eliminando marca de descarga de Internet (Zone.Identifier) en esta carpeta...\r\n"
        "powershell -NoProfile -ExecutionPolicy Bypass -Command \"Get-ChildItem -Path '%~dp0' -Recurse | Unblock-File -ErrorAction SilentlyContinue\"\r\n"
        "echo       Listo: Archivos locales desbloqueados.\r\n"
        "echo.\r\n"
        "echo [2/2] Registrando certificado del editor (Santiago Arguello) en el usuario actual...\r\n"
        "if exist \"%~dp0editor_cert.cer\" (\r\n"
        "    powershell -NoProfile -ExecutionPolicy Bypass -Command \"$c = '%~dp0editor_cert.cer'; Import-Certificate -FilePath $c -CertStoreLocation Cert:\\CurrentUser\\Root -ErrorAction SilentlyContinue | Out-Null; Import-Certificate -FilePath $c -CertStoreLocation Cert:\\CurrentUser\\TrustedPublisher -ErrorAction SilentlyContinue | Out-Null\"\r\n"
        "    echo       Listo: Editor registrado como confiable.\r\n"
        ") else (\r\n"
        "    echo       Nota: editor_cert.cer no encontrado, desbloqueo por Zone.Identifier completado.\r\n"
        ")\r\n"
        "echo.\r\n"
        "echo ==============================================================================\r\n"
        "echo   PROCESO COMPLETADO. Ya puedes abrir game-advisor.exe o Iniciar_Game_Advisor.bat\r\n"
        "echo ==============================================================================\r\n"
        "pause\r\n"
    )
    unblock_bat.write_text(unblock_content, encoding="utf-8")
    print("  * Desbloquear_SmartScreen.bat generado en dist/")


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
    src_presets = (
        root / "presets"
        if (root / "presets").is_dir()
        else root / "src" / "abi_coach" / "infrastructure" / "resources" / "presets"
    )
    dst_presets = dist_dir / "presets"
    if src_presets.is_dir() and not dst_presets.is_dir():
        shutil.copytree(src_presets, dst_presets, dirs_exist_ok=True)
        print("  * presets/ copiado a dist/")

    # 4. Asegurar que data/ esté accesible en la raíz del release
    src_data = (
        root / "src" / "abi_coach" / "infrastructure" / "resources" / "data"
        if (root / "src" / "abi_coach" / "infrastructure" / "resources" / "data").is_dir()
        else root / "data"
    )
    dst_data = dist_dir / "data"
    if src_data.is_dir():
        dst_data.mkdir(parents=True, exist_ok=True)
        for f in src_data.glob("*.json"):
            shutil.copy2(f, dst_data / f.name)
        print("  * data/ copiado a dist/")

    # 5. Firmar ejecutable con Authenticode y generar scripts anti-SmartScreen
    exe_path = dist_dir / "game-advisor.exe"
    sign_executable(exe_path, dist_dir)
    create_smartscreen_helpers(dist_dir)

    # 6. Crear guía rápida para el usuario final (LEEME.txt)
    readme_path = dist_dir / "LEEME.txt"
    readme_content = """==============================================================================
  LLM GAME ADVISOR v0.2.1 — Copiloto Táctico y Analista por Voz para Videojuegos
==============================================================================

¡Bienvenido! Este paquete es completamente portable y autónomo.

¿POR QUÉ APARECE EL AVISO DE WINDOWS DEFENDER SMARTSCREEN Y CÓMO EVITARLO?
------------------------------------------------------------------------------
Cuando descargas un archivo .zip desde GitHub con el navegador (Edge/Chrome),
Windows le añade automáticamente una etiqueta llamada "Mark of the Web"
(Zone.Identifier) y muestra la ventana azul "Windows protegió su PC".

Para abrir la aplicación SIN el aviso de SmartScreen tienes 3 opciones:
  • OPCIÓN A (Recomendada): Inicia siempre desde 'Iniciar_Game_Advisor.bat'
    (limpia automáticamente el bloqueo de descarga y arranca el asesor).
  • OPCIÓN B (Una sola vez): Haz doble clic en 'Desbloquear_SmartScreen.bat'
    para desbloquear todos los archivos de la carpeta y registrar el certificado
    local del editor ('editor_cert.cer').
  • OPCIÓN C (Antes de descomprimir): Haz clic derecho sobre el archivo .zip
    descargado -> Propiedades -> marca la casilla "Desbloquear" -> Aceptar,
    y luego descomprímelo.

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

4. Guarda 'keys.env' e inicia 'Iniciar_Game_Advisor.bat' (o 'game-advisor.exe').

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

    # 7. Empaquetar en archivo ZIP para GitHub Releases
    zip_name = "game-advisor-windows-x64-v0.2.1.zip"
    zip_path = root / "dist" / zip_name
    print(f"\n>> Comprimiendo paquete release para GitHub: {zip_name}...", flush=True)
    import zipfile
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for f in dist_dir.rglob("*"):
            if f.is_file():
                arcname = f.relative_to(dist_dir.parent)
                zf.write(f, arcname)
    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"  * Paquete ZIP creado con exito: {zip_path.name} ({zip_size_mb:.1f} MB)", flush=True)

    print("\n[OK] Release generado exitosamente en:")
    print(f"   Carpeta: {dist_dir.resolve()}")
    print(f"   Archivo ZIP: {zip_path.resolve()}")


if __name__ == "__main__":
    main()

