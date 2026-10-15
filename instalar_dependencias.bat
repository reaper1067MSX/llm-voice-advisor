@echo off
title Instalador de Dependencias - LLM Voice Advisor
chcp 65001 >nul
cd /d "%~dp0"

echo ==================================================================
echo   📦 INSTALADOR AUTOMÁTICO DE DEPENDENCIAS - LLM VOICE ADVISOR
echo ==================================================================
echo.
echo Este asistente preparará todo tu entorno en 1 solo paso:
echo   1. Instala el gestor ultra rápido de paquetes (uv).
echo   2. Configura Python 3.12 de forma aislada y limpia.
echo   3. Descarga todas las dependencias de IA, audio y GPU.
echo   4. Configura tu archivo de clave .env.
echo.
echo ==================================================================
echo.

:: 1. Verificar / Instalar uv (gestor de paquetes ultra rápido)
echo [1/4] Verificando gestor de paquetes (uv)...
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
        echo      Instalando uv automáticamente en tu usuario (toma 5 segundos)...
        powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
        if exist "%USERPROFILE%\.local\bin\uv.exe" (
            set "UV_BIN=%USERPROFILE%\.local\bin\uv.exe"
            set "PATH=%USERPROFILE%\.local\bin;%PATH%"
        )
    )
)
echo      [OK] Gestor uv listo.
echo.

:: 2. Instalar y asegurar Python 3.12 de forma aislada
echo [2/4] Verificando e instalando Python 3.12 gestionado...
"%UV_BIN%" python install 3.12
if %errorlevel% neq 0 (
    echo [ERROR] Falló la instalación de Python con uv. Verificando conexión a internet...
    pause
    exit /b 1
)
echo      [OK] Python 3.12 listo.
echo.

:: 3. Instalar dependencias del proyecto (audio, GPU, IA, captura)
echo [3/4] Instalando dependencias de terceros (Whisper, Gemini, SoundDevice, etc.)...
echo      Descargando paquetes optimizados según uv.lock...
"%UV_BIN%" sync
if %errorlevel% neq 0 (
    echo [ERROR] Hubo un problema al sincronizar las dependencias.
    pause
    exit /b 1
)
echo      [OK] ¡Todas las librerías instaladas con éxito!
echo.

:: 4. Configurar .env si no existe
echo [4/4] Verificando archivo de configuración .env...
if not exist ".env" (
    if exist ".env.example" (
        copy /y ".env.example" ".env" >nul
    )
    echo.
    echo ==================================================================
    echo Para que el copiloto funcione, necesitas tu clave de Google Gemini.
    echo Es 100%% GRATUITA en: https://aistudio.google.com
    echo ==================================================================
    echo.
    set /p USER_KEY="👉 Pega tu clave de Gemini aquí (o presiona ENTER para omitir): "
    if not "%USER_KEY%"=="" (
        echo GEMINI_API_KEY=%USER_KEY%>.env
        echo [OK] ¡Clave guardada con éxito en .env!
    ) else (
        echo [AVISO] Puedes pegar tu clave luego editando el archivo .env con el Bloc de notas.
    )
) else (
    echo      [OK] El archivo .env ya existe.
)

echo.
echo ==================================================================
echo   🎉 ¡INSTALACIÓN COMPLETADA EXITOSAMENTE!
echo ==================================================================
echo Ahora puedes iniciar el copiloto en cualquier momento haciendo
echo doble clic en:
echo.
echo    👉 iniciar_advisor.bat  (o iniciar_coach.bat)
echo.
echo O ejecutando en tu terminal:
echo    uv run llm-voice-advisor
echo ==================================================================
echo.
pause
