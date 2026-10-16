"""Automation script to compile PyInstaller and build Inno Setup installer."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def find_iscc() -> Path | None:
    """Find the Inno Setup command-line compiler executable (ISCC.exe)."""
    # 1. Check PATH
    in_path = shutil.which("iscc") or shutil.which("ISCC")
    if in_path:
        return Path(in_path)

    # 2. Check standard Windows installation paths
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe"),
        Path("C:/Program Files/Inno Setup 6/ISCC.exe"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def ensure_icon() -> Path:
    """Ensure assets/app_icon.ico is present."""
    icon_path = Path("assets/app_icon.ico")
    if icon_path.is_file():
        return icon_path

    png_path = Path("assets/app_icon.png")
    if not png_path.is_file():
        raise FileNotFoundError("No se encontró assets/app_icon.png para generar assets/app_icon.ico")

    print("🎨 Generando assets/app_icon.ico desde app_icon.png...")
    from PIL import Image

    img = Image.open(png_path)
    img.save(
        icon_path,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("✅ Icono multirresolución generado.")
    return icon_path


def build_pyinstaller(force: bool = False) -> None:
    """Compile binaries with PyInstaller if needed."""
    dist_exe = Path("dist/game-advisor/game-advisor.exe")
    if dist_exe.is_file() and not force:
        print(f"📦 Binarios de PyInstaller ya compilados en: {dist_exe}")
        return

    print("🔨 Compilando binarios de Companion Advisor con PyInstaller...")
    cmd = ["uv", "run", "pyinstaller", "game_advisor.spec"]
    res = subprocess.run(cmd, check=True)
    if res.returncode != 0:
        raise RuntimeError("Fallo en la compilación de PyInstaller.")
    print("✅ Compilación de PyInstaller finalizada con éxito.")


def build_installer() -> None:
    """Compile the Inno Setup installer."""
    ensure_icon()
    build_pyinstaller(force=False)

    iscc_path = find_iscc()
    if not iscc_path:
        print("\n" + "=" * 76)
        print(" ⚠️  INNO SETUP NO ESTÁ INSTALADO O NO SE ENCONTRÓ ISCC.EXE")
        print("=" * 76)
        print(" Para compilar el instalador profesional en Windows, necesitas Inno Setup 6.")
        print(" Puedes instalarlo en 1 minuto ejecutando este comando en PowerShell:")
        print("\n    winget install JRSoftware.InnoSetup\n")
        print(" O descargarlo directamente desde: https://jrsoftware.org/isdl.php")
        print("=" * 76 + "\n")
        sys.exit(1)

    print(f"🚀 Compilando instalador profesional con: {iscc_path}")
    Path("dist/installer").mkdir(parents=True, exist_ok=True)
    res = subprocess.run([str(iscc_path), "installer.iss"])
    if res.returncode != 0:
        print("❌ Error al compilar con Inno Setup.")
        sys.exit(res.returncode)

    installer_output = Path("dist/installer/CompanionAdvisor-Installer-v0.2.0.exe")
    if installer_output.is_file():
        size_mb = installer_output.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 76)
        print(" 🎉 ¡INSTALADOR COMPILADO CON ÉXITO!")
        print("=" * 76)
        print(f" Archivo: {installer_output.resolve()}")
        print(f" Tamaño:  {size_mb:.2f} MB (comprimido con LZMA2)")
        print("=" * 76 + "\n")
    else:
        print("⚠️ El proceso finalizó pero no se detectó el archivo de salida.")


if __name__ == "__main__":
    build_installer()
