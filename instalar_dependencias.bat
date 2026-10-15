@echo off
title Instalador de Dependencias - LLM Voice Advisor
cd /d "%~dp0"

echo ==================================================================
echo   INSTALADOR AUTOMATICO DE DEPENDENCIAS - LLM VOICE ADVISOR
echo ==================================================================
echo.
echo Este asistente preparara todo tu entorno en 1 solo paso:
echo   1. Instala el gestor ultra rapido de paquetes (uv).
echo   2. Configura Python 3.12 de forma aislada y limpia.
echo   3. Descarga todas las dependencias de IA, audio y GPU.
echo   4. Configura tu archivo de clave .env.
echo.
echo ==================================================================
echo.

:: 1. Verificar / Instalar uv
echo [1/4] Verificando gestor de paquetes (uv)...
set "UV_BIN=uv"
where uv >nul 2>nul
if %errorlevel% equ 0 goto :UV_INSTALLED

if exist "%USERPROFILE%\.local\bin\uv.exe" (
    set "UV_BIN=%USERPROFILE%\.local\bin\uv.exe"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    goto :UV_INSTALLED
)
if exist "%USERPROFILE%\.cargo\bin\uv.exe" (
    set "UV_BIN=%USERPROFILE%\.cargo\bin\uv.exe"
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
    goto :UV_INSTALLED
)

echo      Instalando uv automaticamente en tu usuario (5 segundos)...
powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
if exist "%USERPROFILE%\.local\bin\uv.exe" (
    set "UV_BIN=%USERPROFILE%\.local\bin\uv.exe"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

:UV_INSTALLED
echo      [OK] Gestor uv listo.
echo.

:: 2. Instalar y asegurar Python 3.12
echo [2/4] Verificando e instalando Python 3.12 gestionado...
"%UV_BIN%" python install 3.12
if %errorlevel% neq 0 (
    echo [ERROR] Fallo la instalacion de Python con uv. Verificando conexion a internet...
    pause
    exit /b 1
)
echo      [OK] Python 3.12 listo.
echo.

:: 3. Instalar dependencias del proyecto
echo [3/4] Instalando dependencias de terceros (Whisper, Gemini, SoundDevice, etc.)...
echo      Descargando paquetes optimizados segun uv.lock...
"%UV_BIN%" sync
if %errorlevel% neq 0 (
    echo [ERROR] Hubo un problema al sincronizar las dependencias.
    pause
    exit /b 1
)
echo      [OK] Todas las librerias instaladas con exito.
echo.

:: 4. Configurar .env si no existe o no tiene clave valida
echo [4/4] Verificando archivo de configuracion .env...

if not exist ".env" goto :ASK_KEY

findstr /I /C:"GEMINI_API_KEY=AIza" ".env" >nul 2>nul
if %errorlevel% equ 0 goto :KEY_ALREADY_SET

findstr /I /C:"tu_clave_aqui" ".env" >nul 2>nul
if %errorlevel% equ 0 goto :ASK_KEY

for /f "usebackq tokens=1,2 delims==" %%A in (".env") do (
    if /i "%%A"=="GEMINI_API_KEY" (
        if not "%%B"=="" goto :KEY_ALREADY_SET
    )
)

:ASK_KEY
echo.
echo ==================================================================
echo Para que el copiloto funcione, necesitas tu clave de Google Gemini.
echo Es 100%% GRATUITA en: https://aistudio.google.com
echo ==================================================================
echo.
set "USER_KEY="
set /p USER_KEY="Pega tu clave de Gemini aqui (o presiona ENTER para omitir): "
if "%USER_KEY%"=="" goto :SKIP_KEY

echo GEMINI_API_KEY=%USER_KEY%>.env
echo      [OK] Clave guardada con exito en .env
goto :DONE

:SKIP_KEY
if not exist ".env" (
    if exist ".env.example" (
        copy /y ".env.example" ".env" >nul
    ) else (
        echo GEMINI_API_KEY=>.env
    )
)
echo      [AVISO] Puedes pegar tu clave luego editando el archivo .env con el Bloc de notas.
goto :DONE

:KEY_ALREADY_SET
echo      [OK] El archivo .env ya cuenta con una clave valida configurada.

:DONE
echo.
echo ==================================================================
echo   INSTALACION COMPLETADA EXITOSAMENTE
echo ==================================================================
echo Ahora puedes iniciar el copiloto en cualquier momento haciendo
echo doble clic en:
echo.
echo      iniciar_advisor.bat  (o iniciar_coach.bat)
echo.
echo O ejecutando en tu terminal:
echo    uv run llm-voice-advisor
echo ==================================================================
echo.
pause
