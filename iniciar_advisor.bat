@echo off
title LLM Voice Advisor
chcp 65001 >nul
cd /d "%~dp0"

echo ==================================================================
echo         🎙️ LLM VOICE ADVISOR - AI GAMING CO-PILOT
echo ==================================================================
echo.

:: 1. Verificar si existe .env
if not exist ".env" (
    echo [AVISO] No se encontró el archivo de configuración .env.
    if exist ".env.example" (
        copy .env.example .env >nul
    )
    echo.
    echo ==============================================================
    echo  Configuración inicial rápida (Solo la primera vez)
    echo ==============================================================
    echo  Para que el copiloto funcione, necesitas una clave gratuita de
    echo  Google Gemini API (100%% gratis, no requiere tarjeta de crédito).
    echo.
    echo  1. Abre en tu navegador: https://aistudio.google.com
    echo  2. Inicia sesión con tu cuenta de Google.
    echo  3. Haz clic en "Get API key" y luego en "Create API key".
    echo  4. Copia tu clave (empieza con AIzaSy...).
    echo ==============================================================
    echo.
    set /p USER_API_KEY="👉 Pega tu clave de Gemini aquí y presiona ENTER: "
    if not "%USER_API_KEY%"=="" (
        echo GEMINI_API_KEY=%USER_API_KEY%>.env
        echo.
        echo [OK] ¡Clave configurada con éxito en .env!
        echo.
    ) else (
        echo.
        echo [ERROR] No ingresaste ninguna clave. Abre el archivo .env con el Bloc de notas y pégala allí.
        pause
        exit /b 1
    )
)

:: 2. Verificar si uv está disponible
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] El gestor 'uv' no está en el PATH. Buscando en rutas estándar...
    if exist "%USERPROFILE%\.local\bin\uv.exe" (
        set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    ) else if exist "%USERPROFILE%\.cargo\bin\uv.exe" (
        set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
    ) else (
        echo [INFO] Instalando 'uv' automáticamente (tarda 5 segundos)...
        powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
        set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    )
)

:: 3. Limpiar procesos antiguos colgados
taskkill /F /FI "WINDOWTITLE eq LLM Voice Advisor*" /IM python.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq ABI Voice Coach*" /IM python.exe 2>nul

echo Iniciando LLM Voice Advisor...
echo [TIP] Puedes hablar por tu micrófono directamente o presionar F9.
echo [TIP] Si tienes 2 monitores, las tablas y gráficos se abrirán en el monitor secundario.
echo.
uv run python -m abi_coach.main

echo.
echo Cerrando dependencias y liberando recursos...
taskkill /F /FI "WINDOWTITLE eq LLM Voice Advisor*" /IM python.exe 2>nul
echo Sesión terminada completamente.
