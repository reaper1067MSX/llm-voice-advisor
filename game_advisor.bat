@echo off
title Game Advisor
cd /d "%~dp0"

echo ==================================================================
echo           GAME ADVISOR - AI GAMING VOICE CO-PILOT
echo ==================================================================
echo.

:: 1. Verificar si existe y es valida la clave en .env
if not exist ".env" goto :PROMPT_KEY

findstr /I /C:"GEMINI_API_KEY=AIza" ".env" >nul 2>nul
if %errorlevel% equ 0 goto :KEY_VALID

findstr /I /C:"tu_clave_aqui" ".env" >nul 2>nul
if %errorlevel% equ 0 goto :PROMPT_KEY

for /f "usebackq tokens=1,2 delims==" %%A in (".env") do (
    if /i "%%A"=="GEMINI_API_KEY" (
        if not "%%B"=="" goto :KEY_VALID
    )
)

:PROMPT_KEY
echo [PASO 1/3] Configuracion inicial de tu clave de Inteligencia Artificial
echo ==================================================================
echo Para que el copiloto funcione, necesitas una clave de Google Gemini.
echo Es 100%% GRATUITA y NO pide tarjeta de credito.
echo.
echo Pasos rapidos para obtenerla:
echo   1. Abre en tu navegador: https://aistudio.google.com
echo   2. Inicia sesion con tu cuenta de Google (Gmail).
echo   3. Haz clic en "Get API key" y luego en "Create API key".
echo   4. Copia tu clave (empieza con AIzaSy...).
echo ==================================================================
echo.
set "USER_API_KEY="
set /p USER_API_KEY="Pega tu clave de Gemini aqui y presiona ENTER: "
if "%USER_API_KEY%"=="" goto :NO_KEY_ENTERED

(echo GEMINI_API_KEY=%USER_API_KEY%)>.env
echo.
echo [OK] Clave guardada con exito en .env
echo.
goto :KEY_VALID

:NO_KEY_ENTERED
echo.
echo [AVISO] No ingresaste ninguna clave.
echo Abre el archivo .env con el Bloc de notas cuando la tengas y pegala alli.
pause
exit /b 1

:KEY_VALID
:: 2. Verificar gestor de ejecucion ultra rapido (uv)
set "UV_BIN=uv"
where uv >nul 2>nul
if %errorlevel% equ 0 goto :UV_READY

if exist "%USERPROFILE%\.local\bin\uv.exe" (
    set "UV_BIN=%USERPROFILE%\.local\bin\uv.exe"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    goto :UV_READY
)
if exist "%USERPROFILE%\.cargo\bin\uv.exe" (
    set "UV_BIN=%USERPROFILE%\.cargo\bin\uv.exe"
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
    goto :UV_READY
)

echo [PASO 2/3] Instalando el motor de ejecucion automatizado uv (5 segundos)...
powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
if exist "%USERPROFILE%\.local\bin\uv.exe" (
    set "UV_BIN=%USERPROFILE%\.local\bin\uv.exe"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

:UV_READY
:: 3. Limpiar procesos antiguos colgados si los hubiera
taskkill /F /FI "WINDOWTITLE eq Game Advisor*" /IM python.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq LLM Voice Advisor*" /IM python.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq ABI Voice Coach*" /IM python.exe 2>nul

echo [PASO 3/3] Iniciando Game Advisor...
echo.
echo [TIPS DE USO EN PARTIDA]
echo  - Habla normalmente por tu microfono (manos libres) o manten F9 si prefieres PTT.
echo  - Si tienes 2 pantallas, las tablas y graficos se abriran solos en tu segundo monitor.
echo  - Compatible con Discord, NVIDIA Broadcast y tu juego al mismo tiempo.
echo.

"%UV_BIN%" run python -m abi_coach %*
set "EXIT_CODE=%errorlevel%"

if not "%EXIT_CODE%"=="0" goto :ERROR_EXIT

echo.
echo Sesion terminada completamente.
pause
exit /b 0

:ERROR_EXIT
echo.
echo ==================================================================
echo Error al ejecutar Game Advisor (Codigo %EXIT_CODE%).
echo ==================================================================
pause
exit /b %EXIT_CODE%
