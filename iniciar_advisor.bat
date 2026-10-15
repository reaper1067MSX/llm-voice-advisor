@echo off
title LLM Voice Advisor
chcp 65001 >nul
cd /d "%~dp0"

echo ==================================================================
echo         🎙️ LLM VOICE ADVISOR - AI GAMING CO-PILOT
echo ==================================================================
echo.

:: 1. Verificar si existe el archivo de configuración .env
if not exist ".env" (
    echo [PASO 1/3] Configuración inicial de tu clave de Inteligencia Artificial
    echo ==================================================================
    echo Para que el copiloto funcione, necesitas una clave de Google Gemini.
    echo Es 100%% GRATUITA y NO pide tarjeta de crédito.
    echo.
    echo Pasos rápidos para obtenerla:
    echo   1. Abre en tu navegador: https://aistudio.google.com
    echo   2. Inicia sesión con tu cuenta de Google (Gmail).
    echo   3. Haz clic en "Get API key" y luego en "Create API key".
    echo   4. Copia tu clave (empieza con AIzaSy...).
    echo ==================================================================
    echo.
    set /p USER_API_KEY="👉 Pega tu clave de Gemini aquí (clic derecho) y presiona ENTER: "
    if not "%USER_API_KEY%"=="" (
        echo GEMINI_API_KEY=%USER_API_KEY%>.env
        echo.
        echo [OK] ¡Clave guardada con éxito en .env!
        echo.
    ) else (
        echo.
        echo [AVISO] No ingresaste ninguna clave.
        echo Abre el archivo .env con el Bloc de notas cuando la tengas y pégala allí.
        pause
        exit /b 1
    )
)

:: 2. Verificar gestor de ejecución ultra rápido (uv)
set "UV_BIN=uv"
where uv >nul 2>nul
if %errorlevel% neq 0 (
    if exist "%USERPROFILE%\.local\bin\uv.exe" (
        set "UV_BIN=%USERPROFILE%\.local\bin\uv.exe"
        set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    ) else if exist "%USERPROFILE%\.cargo\bin\uv.exe" (
        set "UV_BIN=%USERPROFILE%\.cargo\bin\uv.exe"
        set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
    ) else (
        echo [PASO 2/3] Instalando el motor de ejecución automatizado uv (5 segundos)...
        powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
        if exist "%USERPROFILE%\.local\bin\uv.exe" (
            set "UV_BIN=%USERPROFILE%\.local\bin\uv.exe"
            set "PATH=%USERPROFILE%\.local\bin;%PATH%"
        )
    )
)

:: 3. Limpiar procesos antiguos colgados si los hubiera
taskkill /F /FI "WINDOWTITLE eq LLM Voice Advisor*" /IM python.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq ABI Voice Coach*" /IM python.exe 2>nul

echo [PASO 3/3] Iniciando LLM Voice Advisor...
echo.
echo [TIPS DE USO EN PARTIDA]
echo  • Habla normalmente por tu micrófono (manos libres) o mantén F9 si prefieres PTT.
echo  • Si tienes 2 pantallas, las tablas y gráficos se abrirán solos en tu segundo monitor.
echo  • Compatible con Discord, NVIDIA Broadcast y tu juego al mismo tiempo.
echo.
"%UV_BIN%" run python -m abi_coach.main

echo.
echo Cerrando dependencias y liberando recursos...
taskkill /F /FI "WINDOWTITLE eq LLM Voice Advisor*" /IM python.exe 2>nul
echo Sesión terminada completamente.
