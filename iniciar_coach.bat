@echo off
title ABI Voice Coach
chcp 65001 >nul
cd /d "%~dp0"

echo ==================================================================
echo         🎯 ABI VOICE COACH - ARENA BREAKOUT: INFINITE
echo ==================================================================
echo.
echo Limpiando instancias previas si las hubiera...
taskkill /F /FI "WINDOWTITLE eq ABI Voice Coach*" /IM python.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq ABI Voice Coach*" /IM uv.exe 2>nul

echo Iniciando Coach con aceleracion GPU en RTX 4070 Ti...
echo.
uv run python -m abi_coach.main

echo.
echo Cerrando dependencias y liberando recursos...
taskkill /F /FI "WINDOWTITLE eq ABI Voice Coach*" /IM python.exe 2>nul
echo Sesion terminada completamente.
