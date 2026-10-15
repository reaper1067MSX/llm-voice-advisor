# 🎙️ LLM Voice Advisor - Real-Time AI Gaming Co-pilot

Un asistente táctico y copiloto por voz con Inteligencia Artificial multimodal para PC en tiempo real. Diseñado para gamers que buscan optimizar su juego, economía y estrategia sin apartar las manos del teclado ni tapar la pantalla del juego.

Cuenta con detección de voz manos libres (**Voice Activity Detection / VAD**), transcripción local ultrarrápida en GPU (**Whisper**), síntesis de voz femenina natural (**TTS**), inferencia visual inteligente y **dashboards tácticos interactivos** (tablas estilizadas y gráficos Chart.js) que se despliegan automáticamente en tu segundo monitor.

> 🎮 **Juego pre-configurado de muestra:** Incluye preset completo para *Arena Breakout: Infinite (PC)* (reglas económicas, comparador de penetración de blindaje, precios de mercado y análisis de alijo). Es **fácilmente adaptable a cualquier otro juego** (*Once Human*, *Escape from Tarkov*, *Rust*, *DayZ*, *PUBG*, etc.).

---

## 🛑 Antes de empezar: Preguntas Frecuentes para No Desarrolladores

Para que cualquier persona pueda usar este proyecto sin complicaciones técnicas:

| Pregunta | Respuesta sencilla |
| :--- | :--- |
| **¿Tengo que instalar Python a mano?** | **NO.** Si no tienes Python, el script `instalar_dependencias.bat` o `iniciar_advisor.bat` lo descarga y configura automáticamente de forma 100% aislada. |
| **¿Tengo que instalar UV a mano?** | **NO.** Al hacer doble clic en `instalar_dependencias.bat` o `iniciar_advisor.bat`, el sistema detecta si lo tienes; si no, lo instala automáticamente en 5 segundos. |
| **¿Qué drivers de NVIDIA necesito?** | Simplemente tener los **drivers normales de tu tarjeta gráfica NVIDIA actualizados** (los Game Ready Drivers que actualizas desde la app de [NVIDIA GeForce Experience](https://www.nvidia.com/es-la/geforce/geforce-experience/) o [NVIDIA App](https://www.nvidia.com/es-la/software/nvidia-app/)). **NO** necesitas instalar CUDA Toolkit, ni C++, ni Visual Studio. |
| **¿Y si mi PC tiene tarjeta gráfica AMD, Intel o no tiene NVIDIA?** | **Funciona igual.** Si el programa no detecta una tarjeta NVIDIA compatible, se activa automáticamente el modo CPU de Whisper sin dar errores. |
| **¿Qué pasa si solo tengo Microsoft Edge instalado?** | **Funciona directamente.** El programa busca primero Firefox, y si no lo tienes, usa de forma nativa el **Microsoft Edge** que ya viene preinstalado en Windows 10 y 11. |
| **¿Puedo usarlo mientras hablo por Discord?** | **SÍ.** Windows permite que varias aplicaciones escuchen tu micrófono al mismo tiempo. Puedes estar en llamada con tu escuadrón y tu copiloto te escuchará en paralelo sin interferencias. |
| **¿Cobra dinero la clave de Google Gemini?** | **NO.** El plan gratuito (*Free Tier*) de Google AI Studio ofrece hasta 15 consultas por minuto y 1.000.000 de tokens por minuto **sin solicitar tarjeta de crédito** ($0.00 USD). |

---

## 🐍 Instalación de Python (2 Opciones: Automática o Manual)

Para ejecutar el copiloto necesitas el lenguaje Python (versión 3.12 recomendada). Tienes dos formas muy sencillas de tenerlo:

### Opción A (Recomendada): Automática con 1 Clic (Sin páginas web ni configuraciones)
No necesitas hacer nada previo.
1. Ejecuta el archivo **`instalar_dependencias.bat`** (haciendo doble clic).
2. El instalador descargará un entorno de Python 3.12 totalmente aislado y de alto rendimiento utilizando `uv` (un gestor ultra rápido de Python).
3. **Ventajas:** No altera el registro de Windows, no ensucia tus variables de entorno y no entra en conflicto con ningún otro programa que tengas en tu computadora.

### Opción B: Instalación Manual Tradicional desde python.org
Si prefieres instalar Python en tu sistema por tu cuenta:
1. Ve a la página oficial de descargas: **[https://www.python.org/downloads/](https://www.python.org/downloads/)**
2. Descarga la versión **Python 3.12** (Windows Installer de 64 bits).
3. Ejecuta el instalador descargado.
4. ⚠️ **PASO MUY IMPORTANTE:** En la primerísima pantalla del instalador, **marca la casilla que dice:**
   ```text
   [X] Add python.exe to PATH
   ```
   *(Si olvidas marcar esa casilla, Windows no reconocerá el comando `python` en tu consola).*
5. Haz clic en **Install Now** y espera a que termine.
6. Para comprobar que quedó bien instalado, abre PowerShell o la Consola de Windows (`cmd`) y escribe:
   ```powershell
   python --version
   ```
   Debe responder `Python 3.12.x`.

---

## 📦 Dependencias de Terceros y Manejador de Paquetes en 1 Comando

### ¿Qué librerías de terceros utiliza este proyecto?
El copiloto integra componentes especializados para garantizar latencia casi nula y alta fidelidad:

* **`faster-whisper` + `ctranslate2`:** Motor de Inteligencia Artificial que transcribe lo que dices por el micrófono en milisegundos directamente en los núcleos Tensor de tu tarjeta gráfica.
* **`nvidia-cublas-cu12` + `nvidia-cudnn-cu12`:** Bibliotecas de aceleración de NVIDIA precompiladas. Permiten que la GPU procese el audio al instante **sin** necesidad de instalar el pesado SDK de NVIDIA CUDA Toolkit ni Microsoft Visual Studio.
* **`edge-tts`:** Síntesis de voz neural de alta calidad de Microsoft. Genera respuestas habladas con voces humanas hiperrealistas de forma gratuita y sin consumir cuota de tu API.
* **`sounddevice` + `numpy`:** Captura de audio en tiempo real desde tu micrófono con buffer circular de baja latencia.
* **`dxcam` y `mss`:** Motores de captura de pantalla ultra rápidos (utilizan la API de duplicación de escritorio de Windows DirectX) para capturar el juego sin reducir tus FPS.
* **`google-genai`:** SDK oficial de Google para conectar con los modelos de visión y razonamiento multimodal de Gemini.
* **`pillow`:** Algoritmo de escalado Lanczos de alta fidelidad para comprimir las capturas antes de enviarlas al modelo.
* **`pynput`:** Monitorización del teclado para el modo Push-to-Talk (tecla F9 por defecto).

### ⚡ ¿Cómo instalar todas las dependencias con 1 solo comando?

**¡NO tienes que instalar las dependencias una por una!** El proyecto cuenta con un manejador de paquetes automatizado y un archivo de bloqueo (`uv.lock`) que asegura que todo se instale exactamente en las versiones correctas.

#### Método 1 (Con interfaz / 1 Clic):
Haz doble clic en:
```text
👉 instalar_dependencias.bat
```
*(O también en su alias `setup.bat`). El instalador verificará uv, instalará Python 3.12, descargará todas las librerías necesarias y te ayudará a colocar tu clave de Gemini.*

#### Método 2 (Por consola / 1 solo comando):
Si estás usando PowerShell o CMD dentro de la carpeta del proyecto:
```powershell
uv sync
```
*(Si usas Python tradicional instalado en el sistema, puedes ejecutar `pip install -e .`).*

---

## 🔑 Obtener tu Clave Gratuita de Google Gemini (Free Tier)

Para que el copiloto pueda razonar tus preguntas y ver tu pantalla, utiliza la inteligencia artificial de Google Gemini en su nivel gratuito ($0.00 USD).

1. Abre tu navegador e ingresa a: **[https://aistudio.google.com](https://aistudio.google.com)**
2. Inicia sesión con cualquier cuenta de Google normal (tu correo `@gmail.com`).
3. En la esquina superior izquierda o central, haz clic en el botón azul **"Get API key"** (o "Crear clave de API").
4. Haz clic en **"Create API key in new project"** (Crear clave de API en un nuevo proyecto).
5. Aparecerá en pantalla una clave larga que empieza con `AIzaSy...`. Haz clic en **Copy** (Copiar).
6. Pega esta clave en el archivo `.env` del proyecto:
   ```env
   GEMINI_API_KEY=AIzaSyTuClaveDeGoogleGeminiAqui
   ```
   *(Si usas `iniciar_advisor.bat` o `instalar_dependencias.bat`, la ventana te la pedirá directamente y la guardará por ti).*

---

## 🚀 Inicio Rápido con 1 Clic

Una vez instalado:
1. Haz doble clic en **`iniciar_advisor.bat`** (o `iniciar_coach.bat`).
2. Cuando veas en la consola:
   ```text
   🎙️ [MODO CONTINUO VAD ACTIVO] Escuchando tu micrófono...
   ```
   ¡Ya puedes entrar a tu partida y hablarle con naturalidad!
3. Para apagarlo al terminar de jugar, haz doble clic en **`detener_advisor.bat`** o presiona `Ctrl+C`.

---

## 🕹️ Guía Completa de Comandos CLI (Referencia Exhaustiva)

Además de los archivos `.bat`, el proyecto cuenta con una potente Interfaz de Línea de Comandos (CLI) que te permite realizar diagnósticos, probar componentes individuales y hacer consultas sin micrófono.

Puedes invocar los comandos usando `uv run llm-voice-advisor <comando>` (o `python -m abi_coach.main <comando>`):

| Comando / Parámetro | Acción y Utilidad | ¿Consume Tokens de Gemini? |
| :--- | :--- | :---: |
| *(sin parámetros)* | **Modo Principal:** Inicia el bucle continuo del copiloto en tiempo real (VAD manos libres o PTT). | Solo al preguntar |
| `--test-mic` | **Prueba de Micrófono:** Graba 3 segundos de tu voz, la procesa en GPU con Whisper y muestra la transcripción. | ❌ NO (100% local) |
| `--test-tts "<texto>"` | **Prueba de Voz:** Reproduce por tus audífonos el texto indicado usando el motor neural para verificar volumen y entonación. | ❌ NO (Gratis) |
| `--list-voices` | **Catálogo de Voces:** Lista todas las voces femeninas en español disponibles con sus IDs, países y descripciones. | ❌ NO |
| `--voice <id>` | **Selector de Voz Temporal:** Permite probar una voz específica junto con `--test-tts` sin tocar `config.yaml`. | ❌ NO |
| `--test-capture` | **Prueba de Captura:** Captura tu monitor de juego, mide los milisegundos que tarda DirectX y el peso de la imagen. | ❌ NO |
| `--ask "<pregunta>"` | **Consulta Silenciosa:** Envía una pregunta por texto + captura en vivo de tu juego sin activar el micrófono. | SÍ (1 consulta) |
| `--list-models` | **Listar Modelos Gemini:** Consulta a Google AI Studio y muestra todos los modelos disponibles para tu clave. | ❌ NO |
| `--config <archivo.yaml>` | **Configuración Alternativa:** Permite cargar un archivo `.yaml` distinto (ideal para alternar entre diferentes juegos). | Depende del uso |
| `-h`, `--help` | **Ayuda:** Muestra el manual de ayuda de la consola en pantalla. | ❌ NO |

---

### 📖 Ejemplos Prácticos de Cada Comando

#### 1. Probar que tu micrófono y Whisper en GPU funcionen bien:
```powershell
uv run llm-voice-advisor --test-mic
```
*Salida esperada:*
```text
🎙️ Inicializando motor Whisper en GPU...
Habla ahora durante 3 segundos...
Procesando y transcribiendo...
✅ Transcripción exitosa: "hola probando micrófono para el copiloto"
```

#### 2. Probar la voz del asistente por tus audífonos:
```powershell
uv run llm-voice-advisor --test-tts "¡Atención! Munición enemiga nivel 5 detectada en el objetivo."
```

#### 3. Ver qué voces hay disponibles y probar una con acento de España:
```powershell
uv run llm-voice-advisor --list-voices
uv run llm-voice-advisor --test-tts "Hola, soy Elvira y seré tu copiloto táctico." --voice es-ES-ElviraNeural
```

#### 4. Probar la captura de pantalla sin bajar rendimiento del juego:
```powershell
uv run llm-voice-advisor --test-capture
```
*Salida esperada:*
```text
📸 Tomando captura del monitor configurado...
✅ Captura exitosa:
  • Tamaño original: 2560x1440
  • Tamaño procesado (Lanczos): 1280x720
  • Peso JPEG comprimido: 142.3 KB
  • Tiempo de captura de SO: 12.4 ms
  • Tiempo total: 24.8 ms
```

#### 5. Hacer una pregunta mediante texto con análisis de tu pantalla en vivo:
*(Ideal si estás jugando de noche y no quieres hacer ruido con el micrófono)*
```powershell
uv run llm-voice-advisor --ask "¿Cuál de las armas que tengo en el inventario tiene mejor penetración?"
```

#### 6. Comprobar qué modelos de Google Gemini tienes habilitados:
```powershell
uv run llm-voice-advisor --list-models
```

---

## 🎮 ¿Cómo interactuar con el Copiloto mientras juegas?

1. **Ajuste en tu juego (Importante):**  
   Configura tu juego en modo **Ventana sin bordes** (*Borderless Windowed*). Esto permite que Windows capture fotogramas limpiamente sin interferir con el juego ni activar alertas de anti-cheat.
2. **Haz tus preguntas por el micrófono:**
   * **Modo Manos Libres (Por defecto):** Habla con naturalidad en cualquier momento (ej: *"¿Qué balas me recomiendas para farmear?"* o *"Mira mi pantalla, ¿vale la pena este loot?"*). El copiloto detectará tu voz, analizará la situación y te responderá hablando directamente a tus auriculares.
   * **Modo Push-to-Talk (Opcional):** Si prefieres presionar una tecla para hablar, mantén presionado **`F9`** mientras formulas tu pregunta.
3. **Tablas y Gráficos en tu Segundo Monitor:**
   * Si tienes dos pantallas, mantén el juego en la pantalla principal (DISPLAY1) y tu pantalla secundaria (DISPLAY2) visible.
   * Cada vez que tu consulta involucre números, comparativas de daño de munición o valor de objetos, el copiloto generará un dashboard interactivo en HTML con **Chart.js** y lo **abrirá y maximizará automáticamente en tu segundo monitor** sin desviar el foco de tu juego ni hacer parpadear la barra de tareas.
4. **Para apagar el copiloto al terminar:**
   * Haz doble clic en **`detener_advisor.bat`** o presiona `Ctrl+C` en la consola. Todos los procesos de audio, GPU y micrófono se cerrarán inmediatamente sin dejar procesos colgados.

---

## 🖥️ Requisitos de Sistema Detallados

### Requisitos Mínimos:
* **Sistema Operativo:** Windows 10 o Windows 11 (64-bit).
* **Procesador (CPU):** Intel Core i5 / AMD Ryzen 5 o superior.
* **Memoria RAM:** 8 GB (16 GB recomendado si juegas títulos pesados).
* **Micrófono:** Cualquier micrófono USB, headset o de escritorio (compatible con Corsair, HyperX, Logitech, Razer, etc.).
* **Navegador Web:** Mozilla Firefox, Microsoft Edge (nativo) o Google Chrome.
* **Conexión a Internet:** Para conectarse a la API de Gemini.

### Requisitos Recomendados (Máxima Velocidad y Cero Latencia):
* **Tarjeta Gráfica (GPU):** NVIDIA GeForce RTX serie 30 o 40 (RTX 3060, 4060, 4070 Ti, 4080, etc.) con los últimos [Game Ready Drivers de NVIDIA](https://www.nvidia.com/Download/index.aspx). Ejecuta el modelo Whisper `large-v3-turbo` en `float16` con transcripción instantánea en GPU.
* **Monitores:** Configuración dual:
  * **Monitor 1 (Principal):** 1440p o 1080p para el videojuego.
  * **Monitor 2 (Secundario):** 1080p para visualizar las tablas tácticas y gráficos interactivos.

---

## 🛡️ Seguridad Anti-Cheat (ACE, Vanguard, Easy Anti-Cheat)

* **100% externo al juego:** Opera exclusivamente a nivel de escritorio de Windows mediante la API estándar de duplicación de escritorio (Windows Desktop GDI / Desktop Duplication).
* **Cero inyección:** No inyecta DLLs, no lee la memoria RAM del juego (`.exe`), ni dibuja overlays invasivos sobre la ventana del juego. Funciona exactamente de la misma manera que Discord al compartir pantalla o NVIDIA ShadowPlay al grabar.

---

## 🔀 ¿Cómo adaptar o hacer Fork de este proyecto para otro juego?

El proyecto está diseñado de forma modular para que puedas crear tu propio copiloto para cualquier juego:

1. **Cambiar la personalidad y reglas del juego (`src/abi_coach/brain.py`):**
   * Edita `COACH_SYSTEM_INSTRUCTION` y describe las mecánicas de tu juego objetivo (ej. calibración de armas en *Once Human*, balística y blindajes en *Tarkov*, rutas en *DayZ* o builds en *Path of Exile*).
2. **Definir zonas de recorte de pantalla (`config.yaml`):**
   * En `capture.regions`, puedes definir coordenadas en píxeles para que la IA recorte con zoom el inventario, minimapa o barra de salud de tu juego a resolución nativa.
3. **Personalizar las tablas y gráficas (`src/abi_coach/reports.py`):**
   * Modifica las plantillas HTML y los colores de Chart.js para que combinen con la temática visual de tu juego.

---

## ⚙️ Personalización de Ajustes (`config.yaml`)

Si deseas personalizar teclas, micrófonos o voces, abre `config.yaml` con el Bloc de notas:

```yaml
listener:
  mode: "continuous"        # "continuous" (manos libres), "ptt" (pulsar tecla) o "hybrid"
  ptt_key: "f9"             # Tecla para hablar si usas PTT
  vad_threshold: 0.012      # Sensibilidad del micro (0.010 a 0.020)
  silence_duration_sec: 1.0 # Segundos de silencio para enviar tu pregunta

speaker:
  voice: "es-CO-SalomeNeural" # Voz de Salomé (Colombia). Otras: es-ES-ElviraNeural, es-MX-DaliaNeural
  rate: "+0%"                 # Velocidad de voz
  volume: "+0%"

reports:
  auto_open_browser: true
  preferred_browser: "firefox" # "firefox", "edge" o "chrome"
```

---

## 📄 Licencia

Este proyecto está bajo la licencia **MIT**. Eres libre de usarlo, modificarlo, compartirlo y adaptarlo a cualquier videojuego.
