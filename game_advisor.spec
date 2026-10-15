# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for LLM Game Advisor (Windows Release)."""

from pathlib import Path
import sysconfig
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

block_cipher = None

# Datas: presets, initial knowledge data, and default configurations
presets_src = 'presets' if Path('presets').is_dir() else 'src/abi_coach/presets'
data_src = 'data' if (Path('data') / 'abi_knowledge.json').is_file() else 'src/abi_coach/data'

datas = [
    (presets_src, 'presets'),
    (data_src, 'data'),
    ('config.yaml', '.'),
    ('keys.env.example', '.'),
]
datas += collect_data_files('faster_whisper')
datas += collect_data_files('ctranslate2')
datas += collect_data_files('google.genai')

# Dynamic binaries: ctranslate2 and CUDA / CUDNN runtime DLLs
binaries = []
binaries += collect_dynamic_libs('ctranslate2')

sp_path = Path(sysconfig.get_path('purelib'))
nvidia_path = sp_path / 'nvidia'
if nvidia_path.is_dir():
    for dll in nvidia_path.glob('**/*.dll'):
        binaries.append((str(dll), '.'))
        binaries.append((str(dll), f"nvidia/{dll.parent.parent.name}/bin"))

hiddenimports = [
    'sounddevice',
    'miniaudio',
    'faster_whisper',
    'ctranslate2',
    'dxcam',
    'mss',
    'PIL',
    'PIL.Image',
    'yaml',
    'dotenv',
    'google.genai',
    'google.genai.types',
    'sqlite3',
    'edge_tts',
    'pyttsx3',
    'pyttsx3.drivers',
    'pyttsx3.drivers.sapi5',
    'pynput',
    'pynput.keyboard',
    'pynput.mouse',
    'ctypes',
    'winsound',
]
hiddenimports += collect_submodules('abi_coach')

a = Analysis(
    ['src/abi_coach/__main__.py'],
    pathex=['src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'IPython'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='game-advisor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='game-advisor',
)
