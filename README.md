# 🎯 ABI Voice Coach - Arena Breakout: Infinite

Copiloto táctico y asesor económico para **Arena Breakout: Infinite (PC)** activado por voz y basado en eventos (*Push-to-Talk*), diseñado para optimizar el gasto de tokens y brindar asistencia en tiempo real mediante **visión por IA (Google Gemini Flash)** y **síntesis de voz**.

---

## ⚡ Características Principales

1. **Eficiencia Extrema de Tokens (Event-Driven):**
   * **Cero streaming continuo:** No gasta tokens innecesarios mientras corres o estás en colas. Solo captura **un único fotograma optimizado** en el momento exacto en que presionas la tecla para hablar.
   * **Downscale Inteligente para 1440p:** Reduce la captura completa a 1080p mediante interpolación *Lanczos* para mantener textos y números legibles gastando una fracción de los tokens (~2.500 tokens por consulta vs ~15.000 por minuto de video).
2. **Push-to-Talk Global (Sin interferencias):**
   * Escucha la tecla configurada (por defecto **`F9`** o botón lateral del ratón) sin inyectar teclas ni simular entradas.
3. **Transcripción Local Ultrarrápida en GPU:**
   * Utiliza **faster-whisper** con aceleración por hardware en tu tarjeta **NVIDIA GeForce RTX 4070 Ti** (`float16`). Latencia mínima y costo \$0 en transcripción.
4. **Voz Femenina Natural (TTS):**
   * Respuestas habladas fluidas en español latinoamericano (**`es-MX-DaliaNeural`**) reproducidas directamente en tus auriculares.
5. **Generador de Reportes HTML y Gráficos (Segundo Monitor):**
   * Cuando pides tablas comparativas, desgloses de alijo o estadísticas de munición, el coach crea un informe HTML oscuro con **Chart.js** y lo abre automáticamente en tu navegador.
6. **Seguridad frente al Anti-Cheat (ACE):**
   * Funciona 100% a nivel de sistema operativo (Windows Desktop GDI / Desktop Duplication).
   * **No inyecta DLLs**, no lee la memoria de `ArenaBreakoutInfinite.exe`, no dibuja overlays invasivos dentro del juego.

---

## 🛠️ Requisitos Previos

* **Windows 10 / 11**
* **NVIDIA GPU** con controladores actualizados (probado en RTX 4070 Ti con CUDA).
* **Gestor `uv`** (o Python 3.12+).
* **Clave de API de Google Gemini** (obtenible en [Google AI Studio](https://aistudio.google.com)).

---

## 🚀 Instalación y Configuración

1. **Clonar o abrir el repositorio:**
   ```powershell
   cd c:\Users\geova\Documents\antigravity\calm-archimedes
   ```

2. **Sincronizar el entorno con `uv`:**
   ```powershell
   uv sync
   ```

3. **Configurar la clave de API:**
   Copia `.env.example` a `.env` y pega tu clave:
   ```powershell
   Copy-Item .env.example .env
   ```
   Edita `.env`:
   ```env
   GEMINI_API_KEY=tu_clave_de_gemini_aqui
   ```

4. **Ajustar `config.yaml` (Opcional):**
   Puedes modificar la tecla de Push-to-Talk, el monitor del juego o la voz:
   ```yaml
   listener:
     ptt_key: "f9" # Tecla para hablar
     whisper_model: "large-v3-turbo"
     whisper_device: "cuda"

   speaker:
     voice: "es-MX-DaliaNeural" # Voz femenina en español

   capture:
     monitor_index: 1 # 1 para monitor primario (2560x1440)
     downscale_width: 1920
     downscale_height: 1080
   ```

---

## 🎮 Comandos de Uso y Pruebas

### 1. Iniciar el Coach en Modo Interactivo
```powershell
uv run python -m abi_coach.main
```
* Abre tu juego (preferiblemente en modo **Ventana sin bordes / Borderless Windowed**).
* Mantén presionado **`F9`**, haz tu pregunta (por ejemplo: *"¿Qué vale más de lo que tengo en el alijo?"* o *"Revisa si me conviene este contrato de Deke"*) y suelta la tecla.
* El coach analizará la captura tomada al inicio y te responderá por voz.

### 2. Comandos de Diagnóstico / Smoke Tests

* **Probar captura de pantalla (sin gastar tokens ni micro):**
  ```powershell
  uv run python -m abi_coach.main --test-capture
  ```
* **Probar la voz femenina (TTS):**
  ```powershell
  uv run python -m abi_coach.main --test-tts "Hola, soy tu coach táctico de Arena Breakout Infinite."
  ```
* **Probar el micrófono y transcripción local en GPU:**
  ```powershell
  uv run python -m abi_coach.main --test-mic
  ```
* **Hacer una consulta con captura usando texto (sin micro):**
  ```powershell
  uv run python -m abi_coach.main --ask "¿Qué munición me recomiendas para farmear en Granja?"
  ```
* **Ejecutar la suite de pruebas unitarias:**
  ```powershell
  uv run pytest
  ```

---

## ⚠️ Consejos de Seguridad Anti-Cheat

* **Juega en Borderless Windowed:** Permite que Windows capture el fotograma limpiamente sin necesidad de engancharse a la pantalla exclusiva.
* **Segundo Monitor:** Mantén la consola y el navegador en tu segundo monitor (DISPLAY2) para ver los reportes y gráficas sin tapar el juego.
* **Uso Recomendado:** El uso ideal es **entre partidas** (en el menú principal, alijo, mercado libre, armería o pantalla post-combate). Aunque la captura de escritorio es indetectable por memoria, usar cualquier asistente durante tiroteos en partidas clasificatorias es bajo tu propio criterio de juego limpio.
