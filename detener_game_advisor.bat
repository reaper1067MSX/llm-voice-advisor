@echo off
title Detener Game Advisor
cd /d "%~dp0"
echo ==================================================================
echo   Deteniendo Game Advisor y liberando memoria / VRAM...
echo ==================================================================
echo.

taskkill /F /FI "WINDOWTITLE eq Game Advisor*" /IM python.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq Game Advisor*" /IM uv.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq ABI Tactical Coach*" /IM python.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq ABI Tactical Coach*" /IM uv.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq ABI Voice Coach*" /IM python.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq ABI Voice Coach*" /IM uv.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq LLM Voice Advisor*" /IM python.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq LLM Voice Advisor*" /IM uv.exe 2>nul

echo [OK] Proceso completado. Todos los recursos han sido liberados.
timeout /t 3 >nul
