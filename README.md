# 🎙️ LLM Voice Advisor - Real-Time AI Gaming Co-pilot

Un asistente táctico y copiloto por voz con Inteligencia Artificial multimodal para PC en tiempo real. Diseñado para gamers que buscan optimizar su juego, economía y estrategia sin apartar las manos del teclado ni tapar la pantalla del juego.

Cuenta con detección de voz manos libres (**Voice Activity Detection / VAD**), transcripción local ultrarrápida en GPU (**Whisper**), síntesis de voz femenina natural (**TTS**), inferencia visual inteligente y **dashboards tácticos interactivos** (tablas estilizadas y gráficos Chart.js) que se despliegan automáticamente en tu segundo monitor.

> 🎮 **Juego pre-configurado de muestra:** Incluye preset completo para *Arena Breakout: Infinite (PC)* (reglas económicas, comparador de penetración de blindaje, precios de mercado y análisis de alijo). Es **fácilmente adaptable a cualquier otro juego** (*Once Human*, *Escape from Tarkov*, *Rust*, *DayZ*, *PUBG*, etc.).

---

## 🛑 Antes de empezar: Preguntas Frecuentes para No Desarrolladores

Para que cualquier persona pueda usar este proyecto sin complicaciones técnicas:

| Pregunta | Respuesta sencilla |
| :--- | :--- |
| **¿Tengo que instalar Python a mano?** | **NO.** El lanzador incluido (`iniciar_advisor.bat`) se encarga de descargar y configurar Python automáticamente de forma limpia y aislada. |
| **¿Tengo que instalar UV a mano?** | **NO.** Al hacer doble clic en el archivo `.bat`, este detecta si tienes `uv` instalado; si no lo tienes, lo instala automáticamente en 5 segundos. |
| **¿Qué drivers de NVIDIA necesito?** | Simplemente tener los **drivers normales de tu tarjeta gráfica NVIDIA actualizados** (los Game Ready Drivers que actualizas desde la app de [NVIDIA GeForce Experience](https://www.nvidia.com/es-la/geforce/geforce-experience/) o [NVIDIA App](https://www.nvidia.com/es-la/software/nvidia-app/)). **NO** necesitas instalar CUDA Toolkit, ni C++, ni Visual Studio. |
| **¿Y si mi PC tiene tarjeta gráfica AMD, Intel o no tiene NVIDIA?** | **Funciona igual.** Si el programa no detecta una tarjeta NVIDIA compatible, se activa automáticamente el modo CPU de Whisper sin dar errores. |
| **¿Qué pasa si solo tengo Microsoft Edge instalado?** | **Funciona directamente.** El programa busca primero Firefox, y si no lo tienes, usa de forma nativa el **Microsoft Edge** que ya viene preinstalado en Windows 10 y 11. |
| **¿Puedo usarlo mientras hablo por Discord?** | **SÍ.** Windows permite que varias aplicaciones escuchen tu micrófono al mismo tiempo. Puedes estar en llamada con tu escuadrón y tu copiloto te escuchará en paralelo. |
| **¿Cobra dinero la clave de Google Gemini?** | **NO.** El plan gratuito (*Free Tier*) de Google AI Studio ofrece hasta 15 consultas por minuto y 1.000.000 de tokens por minuto **sin solicitar tarjeta de crédito** ($0.00 USD). |

---

## 🧭 Guía de Instalación Paso a Paso (Para Gamers)

Sigue estos 3 sencillos pasos:

### Paso 1: Descargar el proyecto
1. En esta página de GitHub, haz clic en el botón verde **Code** (arriba a la derecha).
2. Selecciona **Download ZIP**.
3. Descomprime la carpeta en cualquier lugar de tu PC (por ejemplo, en tus `Documentos`).

---

### Paso 2: Obtener tu Clave Gratuita de Google Gemini (Free Tier)

Para que el copiloto pueda razonar tus preguntas y ver tu pantalla, utiliza la inteligencia artificial de Google Gemini en su nivel gratuito.

1. Abre tu navegador e ingresa a: **[https://aistudio.google.com](https://aistudio.google.com)**
2. Inicia sesión con cualquier cuenta de Google normal (tu correo `@gmail.com`).
3. En la esquina superior izquierda o central, haz clic en el botón azul **"Get API key"** (o "Crear clave de API").
4. Haz clic en **"Create API key in new project"** (Crear clave de API en un nuevo proyecto).
5. Aparecerá en pantalla una clave larga que empieza con `AIzaSy...`. Haz clic en **Copy** (Copiar).

---

### Paso 3: Iniciar el Asistente con 1 Clic

1. Abre la carpeta del proyecto que descomprimiste.
2. Haz doble clic en el archivo **`iniciar_advisor.bat`** (o `iniciar_coach.bat`).
3. **Solo la primera vez:** La ventana te pedirá tu clave de Gemini. Haz clic derecho para pegarla y presiona `ENTER`.
4. El programa instalará todo automáticamente en segundo plano. Cuando veas el mensaje:
   ```text
   🎙️ [MODO CONTINUO VAD ACTIVO] Escuchando tu micrófono...
   ```
   ¡Ya está listo para jugar!

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

* **100% externo al juego:** Opera exclusivamente a nivel de escritorio de Windows mediante la API estándar de duplicación de escritorio (Windows Desktop GDI).
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
