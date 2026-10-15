@echo off
title Detener ABI Voice Coach
chcp 65001 >nul
echo ==================================================================
echo   Deteniendo ABI Voice Coach y liberando memoria / VRAM...
echo ==================================================================
echo.

taskkill /F /FI "WINDOWTITLE eq ABI Voice Coach*" /IM python.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq ABI Voice Coach*" /IM uv.exe 2>nul

echo ✅ Proceso completado. Todos los recursos han sido liberados.
timeout /t 3 >nul
