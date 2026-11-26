# 🎙️ LLM Voice Advisor — Real-Time AI Gaming Copilot

> Copiloto táctico multimodal con Inteligencia Artificial que **escucha**, **observa**, **habla** y despliega **dashboards en tu segundo monitor** en tiempo real sin apartar las manos del teclado ni perder FPS en tu juego.

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Architecture: Clean](https://img.shields.io/badge/architecture-Clean%20%2F%20Hexagonal-emerald.svg)](CAPABILITIES.md)
[![Tests Passing](https://img.shields.io/badge/tests-172%20passed-brightgreen.svg)](tests/)

---

## ⚡ Inicio Rápido (Gamers / Zero Coding)

No necesitas conocimientos de programación ni instalar herramientas complejas por tu cuenta.

### 🚀 Opciones de Lanzamiento en 1 Clic

| Método | Para quién es | Cómo iniciarlo | Qué hace el sistema |
| :--- | :--- | :--- | :--- |
| **Lanzador 1-Clic** *(Recomendado)* | Usuarios de repositorio / portable | Doble clic en `game_advisor.bat` | Instala `uv` en 5s, configura Python 3.12 aislado, solicita tu clave si falta y arranca el copiloto. |
| **Instalador de Windows** | Instalación formal en Windows | Ejecuta `dist/installer/CompanionAdvisor-Installer-v0.2.2.exe` | Asistente profesional Inno Setup en `C:\CompanionAdvisor`, con accesos directos y desinstalador limpio. |
| **Apagado en 1-Clic** | Fin de partida | Doble clic en `detener.bat` | Cierra todos los procesos, libera hilos de audio, micrófono y vacía la memoria VRAM de la GPU. |

---

### 🕹️ 3 Pasos para Jugar

1. **Inicia el asistente:** Haz doble clic en **`game_advisor.bat`**.
2. **Ingresa tu clave:** Pega tu clave gratuita de Google Gemini (o Moonshot Kimi) en la ventana cuando te la pida (solo la primera vez).
3. **Entra a tu partida:** Configura tu juego en **Ventana sin bordes** (*Borderless Windowed*), habla con naturalidad por tu micrófono y ¡recibe consejos tácticos al instante!

---

## 🔑 Configuración de Claves de API

El copiloto utiliza modelos multimodales de última generación. Puedes usar Google Gemini de forma gratuita o configurar Moonshot (Kimi) como respaldo resiliente de alta capacidad:

| Proveedor | Modelo Principal | Costo | Cómo Obtenerla | Variable en `.env` |
| :--- | :--- | :--- | :--- | :--- |
| **Google Gemini** *(Recomendado)* | `gemini-3.5-flash` / `gemini-3.1-flash-lite` | **100% Gratuito** ($0.00 USD, sin tarjeta de crédito) | 1. Entra a [Google AI Studio](https://aistudio.google.com)<br>2. Clic en **Get API Key** ➔ **Create API Key**<br>3. Copia tu clave `AIzaSy...` | `GEMINI_API_KEY=AIzaSy...` |
| **Moonshot (Kimi)** *(Respaldo Resiliente)* | `kimi-k2.6` | Pay-as-you-go / créditos iniciales | 1. Entra a [Moonshot AI Platform](https://platform.moonshot.ai) o [Moonshot CN](https://platform.moonshot.cn)<br>2. Genera una API Key en la consola | `MOONSHOT_API_KEY=sk-...`<br>`MOONSHOT_BASE_URL=https://api.moonshot.ai/v1` |
| **NVIDIA NIM** *(Opcional)* | `meta/llama-3.2-11b-vision-instruct` | Free Tier en catálogo de NVIDIA | 1. Entra a [build.nvidia.com](https://build.nvidia.com)<br>2. Genera tu Personal API Key | `NVIDIA_API_KEY=nvapi-...` |

### Plantilla de Configuración (`.env`)
Si prefieres editar el archivo directamente, crea o edita `.env` en la raíz del proyecto:
```env
# Proveedor principal (Gratis en Google AI Studio)
GEMINI_API_KEY=AIzaSyTuClaveDeGoogleGeminiAqui

# Proveedor de respaldo automático (Kimi / Moonshot)
MOONSHOT_API_KEY=sk-TuClaveDeMoonshotAqui
MOONSHOT_BASE_URL=https://api.moonshot.ai/v1
MOONSHOT_MODEL=kimi-k2.6
```

---

## 🎮 Experiencia en Partida y Controles

### ⌨️ Tabla de Teclas Rápidas (Hotkeys)

| Tecla | Acción | Comportamiento | Retroalimentación |
| :---: | :--- | :--- | :--- |
| **`F10`** | **Mute Toggle (Silencio Global)** | Alterna entre silenciar y reactivar el micrófono en cualquier momento (ideal si hablas por Discord). | Beep sonoro de Windows (`winsound` tono alto / bajo). |
| **`F9`** | **Push-To-Talk (PTT)** | Si activas modo PTT en `config.yaml`, mantén presionada esta tecla mientras formulas tu consulta. | Escucha únicamente mientras está presionada. |
| **`Ctrl + C`** | **Salida de Consola** | Cierra la sesión del asistente liberando hilos de fondo y memoria gráfica. | Mensaje de confirmación en consola. |

---

### 🗣️ Comandos de Voz Naturales (Meta-Tuning en Vivo)

No requieres memorizar comandos rígidos ni sintaxis de consola. Habla de forma natural durante la partida para afinar el comportamiento del copiloto:

| Lo que dices al micrófono | Acción del Copiloto | Resultado en Tiempo Real |
| :--- | :--- | :--- |
| *"Coach, prioriza daño"* | **Meta-Tuning Balístico** | Ajusta el razonamiento táctico para priorizar penetración de blindaje y daño letal. |
| *"Filtra solo loot morado o dorado"* | **Filtro de Inventario** | Ignora objetos de bajo valor (tier 1-3) y alerta solo sobre ítems de alto valor. |
| *"Prioriza valor por casilla"* | **Economía de Alijo** | Evalúa koen/rublos por ranura de inventario para decidir qué loot conservar. |
| *"Cambia a Rust"* *(o "Modo Tarkov", "Modo Once Human")* | **Scaffolding de Arquetipo** | Activa dinámicamente el arquetipo de *Survival Crafting* o *Extraction Shooter* con sus reglas y datos. |
| *"Cambia la voz a Elvira"* *(o Salomé, Dalia, Camila)* | **Voz en Caliente** | Modifica instantáneamente la voz neural de Microsoft en `config.yaml` sin reiniciar. |
| *"Cancela"* o *"Olvídalo"* | **FSM de Clarificación** | Cancela una aclaración pendiente o restablece el estado de diálogo. |

---

### 🖥️ Dashboards Tácticos en Segundo Monitor (Sin Perder el Foco)

* **Visión en vivo:** El motor DirectX captura fotogramas de tu pantalla sin mermar los FPS de tu juego.
* **Auto-despliegue en DISPLAY2:** Al formular preguntas comparativas (ej: *"¿Qué munición penetra mejor clase 5?"* o *"Analiza el valor de mi alijo"*), el copiloto genera un reporte interactivo en HTML5 con **Chart.js**.
* **Zero Focus Stealing:** Utiliza la API Win32 de Windows (`win32_window_manager.py`) para posicionar y maximizar el navegador en tu pantalla secundaria **sin robar el foco del teclado/ratón de tu juego ni hacer parpadear la barra de tareas**.

---

## 💻 Referencia de Comandos CLI

Para usuarios avanzados, streamers y desarrolladores, puedes ejecutar diagnósticos e invocar el copiloto mediante `uv run game-advisor` (o `uv run python -m abi_coach`):

| Comando | Propósito | ¿Consume Cuota de API? |
| :--- | :--- | :---: |
| `uv run game-advisor` | **Modo Principal:** Inicia el bucle continuo en tiempo real (VAD manos libres o PTT). | Solo al preguntar |
| `uv run game-advisor --game abi` | **Preset ABI:** Inicia con contexto especializado para Arena Breakout: Infinite. | Solo al preguntar |
| `uv run game-advisor --test-mic` | **Diagnóstico de Micrófono:** Graba 3s y valida transcripción en GPU con Whisper. | ❌ NO (100% local) |
| `uv run game-advisor --test-tts "<texto>"` | **Prueba de Voz:** Reproduce una frase por tus auriculares con síntesis neural Edge-TTS. | ❌ NO (Gratuito) |
| `uv run game-advisor --list-voices` | **Catálogo de Voces:** Lista las voces femeninas en español disponibles con sus IDs. | ❌ NO |
| `uv run game-advisor --voice <id>` | **Selector Temporal:** Prueba una voz específica (ej: `es-ES-ElviraNeural`). | ❌ NO |
| `uv run game-advisor --test-capture` | **Diagnóstico de Captura:** Mide milisegundos de captura DirectX y escalado Lanczos. | ❌ NO |
| `uv run game-advisor --ask "<pregunta>"` | **Consulta Silenciosa:** Envía una pregunta por texto junto con captura de pantalla. | SÍ (1 consulta) |
| `uv run game-advisor --list-models` | **Descubrimiento de Modelos:** Consulta dinámicamente endpoints activos en Gemini y Moonshot. | ❌ NO |

---

## 🏛️ Arquitectura y Referencia Técnica

El proyecto implementa **Clean Architecture (Hexagonal)** con separación estricta de responsabilidades en 4 capas concéntricas:

```text
src/abi_coach/
├── domain/                  # Entidades puras, Records inmutables, Enums y Puertos
│   ├── common/              # Result, Option, Value Objects de error
│   ├── entities/            # PlayerMemory, KnowledgeItem, MetatuningRecords, DTOs
│   ├── enums/               # MetaTuningIntent, MetaTuningCategory, MetaTuningAction
│   └── ports/               # WindowManagerPort, LLMPort, AudioPort, StoragePort
├── application/             # Casos de uso y orquestación de aplicación
│   ├── orchestration/       # AdvisorOrchestrator, ResilientLLMOrchestrator
│   ├── services/            # ModelDiscoveryService, ConfigMutator, AudioFeedback
│   └── slices/              # Metatuning FSM, Tactical RAG, Archetypes, Reporting
├── infrastructure/          # Adaptadores de plataforma e implementaciones de puertos
│   ├── adapters/            # DXCam/MSS (visión), Faster-Whisper/Silero (audio), Gemini/Moonshot (LLM)
│   ├── platform/            # Win32WindowManager (ctypes User32), BrowserLauncher, Hotkeys
│   ├── presentation/        # DashboardPresenter para renderizado HTML/CSS/Chart.js
│   └── resources/           # Plantillas HTML para reportes tácticos
└── presentation/            # Puntos de entrada para usuario y presentación
    ├── cli/                 # CLI entrypoints (game-advisor, llm-voice-advisor, abi-coach)
    └── voice/               # Bucle continuo de interacción por voz en tiempo real
```

### 📘 Documentación Arquitectónica Exhaustiva
Para profundizar en los 7 pilares técnicos del sistema, RAG determinístico en sub-3ms con SQLite FTS5, circuito de contingencia ante caídas de API y el motor de arquetipos dinámicos:
👉 Consulta la **[`CAPABILITIES.md`](CAPABILITIES.md)**.

---

## 🧪 Verificación de Calidad y Tests

El proyecto cuenta con suite de pruebas automatizadas y control estricto de fronteras arquitectónicas:

```powershell
# 1. Ejecutar la suite completa de pruebas unitarias e integración (170+ tests)
uv run pytest -q

# 2. Verificar que ninguna capa interna importe capas externas (Clean Architecture)
uv run lint-imports

# 3. Validar estilo de código, imports y convenciones con Ruff
uv run ruff check
```

---

## 🛡️ Seguridad Anti-Cheat (ACE, Vanguard, Easy Anti-Cheat)

* **100% Externo al juego:** Opera exclusivamente a nivel de escritorio mediante la API de duplicación de escritorio de Windows (DirectX Desktop Duplication / GDI).
* **Cero inyección:** No inyecta DLLs, no lee ni modifica la memoria RAM del juego (`.exe`), ni dibuja overlays invasivos sobre la ventana.
* **Mismo nivel de seguridad que OBS o Discord:** Funciona de la misma manera que Discord al compartir pantalla o NVIDIA ShadowPlay al grabar tus partidas.

---

## 📋 Requisitos del Sistema

| Componente | Mínimo | Recomendado (Máximo Rendimiento) |
| :--- | :--- | :--- |
| **Sistema Operativo** | Windows 10 (64-bit) | Windows 11 (64-bit) |
| **Procesador (CPU)** | Intel Core i5 / AMD Ryzen 5 | Intel Core i7 / AMD Ryzen 7 o superior |
| **Memoria RAM** | 8 GB | 16 GB o más |
| **Tarjeta Gráfica (GPU)** | Gráficos integrados o GPU compatible con CPU fallback | NVIDIA GeForce RTX serie 30 o 40 (Whisper `large-v3-turbo` en `float16` con núcleos Tensor) |
| **Micrófono** | Cualquier micrófono USB, headset o de escritorio | Headset con cancelación de ruido o micrófono dedicado |
| **Monitores** | 1 Monitor (Juego + Ventana de asistente) | **2 Monitores:** Display 1 (Juego 1440p/1080p) + Display 2 (Dashboards tácticos) |
| **Navegador** | Microsoft Edge (preinstalado en Windows) | Mozilla Firefox (ultraligero y rápido) o Google Chrome |

---

## 📄 Licencia

Este proyecto está bajo la licencia **MIT**. Eres libre de usarlo, adaptarlo a cualquier juego, modificarlo y compartirlo con tu comunidad.
