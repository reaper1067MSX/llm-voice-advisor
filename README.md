# 🎙️ LLM Voice Advisor - Real-Time AI Gaming Co-pilot

Un asistente táctico y copiloto por voz con IA multimodal para PC en tiempo real. Diseñado para gamers que buscan optimizar su juego, economía y estrategia sin apartar las manos del teclado ni tapar la pantalla del juego.

Cuenta con detección de voz manos libres (**Voice Activity Detection / VAD**), transcripción local ultrarrápida en GPU (**Whisper**), síntesis de voz femenina natural (**TTS**), inferencia visual inteligente y **dashboards tácticos interactivos** (tablas estilizadas y gráficos Chart.js) que se despliegan automáticamente en tu segundo monitor.

> 🎮 **Juego pre-configurado de muestra:** Incluye preset completo para *Arena Breakout: Infinite (PC)* (reglas económicas, comparador de penetración de blindaje, precios de mercado y análisis de alijo). Es **fácilmente adaptable a cualquier otro juego** (*Once Human*, *Escape from Tarkov*, *Rust*, *DayZ*, *PUBG*, etc.).

---

## 🧭 Guía de Instalación para Gamers (Sin conocimientos técnicos)

No necesitas ser programador ni saber usar la terminal para poner a funcionar tu copiloto. Sigue estos 4 pasos:

### Paso 1: Descargar el proyecto
1. En esta página de GitHub, haz clic en el botón verde **Code** (arriba a la derecha).
2. Selecciona **Download ZIP**.
3. Descomprime el archivo descargado en cualquier carpeta de tu preferencia (por ejemplo en tus `Documentos`).

---

### Paso 2: Obtener tu clave gratuita de Google Gemini (Free Tier)

Google ofrece acceso a sus modelos más rápidos (Gemini 2.5 Flash y 3.1 Flash) de forma **100% gratuita** y sin pedirte tarjeta de crédito.

1. Abre tu navegador e ingresa a: **[https://aistudio.google.com](https://aistudio.google.com)**
2. Inicia sesión con cualquier cuenta de Google (tu correo Gmail habitual).
3. En la barra lateral o superior, haz clic en el botón azul **"Get API key"** (Obtener clave de API).
4. Haz clic en **"Create API key in new project"** (Crear clave de API en un nuevo proyecto).
5. Se generará un código largo que empieza por `AIzaSy...`. Haz clic en **Copy** (Copiar) y guárdalo.

> 💡 **¿El Free Tier cuesta dinero o tiene letra pequeña?**  
> **No.** El nivel gratuito de Google AI Studio te da hasta 15 consultas por minuto y 1.000.000 de tokens por minuto. Para tus partidas diarias es más que suficiente y cuesta **$0.00 USD**.

---

### Paso 3: Iniciar con 1 Clic (Configuración Automática)

1. Entra a la carpeta descomprimida del proyecto.
2. Haz doble clic en el archivo **`iniciar_advisor.bat`** (o `iniciar_coach.bat`).
3. **Solo la primera vez:** Se abrirá una ventana que te pedirá tu clave de Gemini. Haz clic derecho para pegarla y presiona `ENTER`.
4. El lanzador se encargará de todo automáticamente:
   * Instalará el gestor rápido de dependencias (`uv`).
   * Descargará las librerías necesarias y el modelo de voz Whisper.
   * Conectará con tu micrófono y tarjeta gráfica.

¡Listo! Cuando veas el mensaje `🎙️ [MODO CONTINUO VAD ACTIVO] Escuchando tu micrófono...`, tu copiloto ya está en guardia.

---

### Paso 4: ¿Cómo usarlo mientras juegas?

1. **Juega en modo Ventana sin bordes:** En los ajustes gráficos de tu juego, selecciona *"Ventana sin bordes"* (*Borderless Windowed*) para que Windows permita capturar imágenes limpiamente.
2. **Habla por tu micrófono:**
   * **Modo Manos Libres (Por defecto):** Simplemente haz tu pregunta en voz alta por el micrófono (ej: *"¿Qué balas uso para farmear?"* o *"¿Vale la pena lootear este objeto?"*). El coach detectará tu voz, procesará la duda y te responderá hablando directamente a tus auriculares.
   * **Push-to-Talk (Opcional):** Si prefieres activar la escucha manteniendo una tecla, puedes presionar **`F9`**.
3. **Reportes Visuales en el Segundo Monitor:**
   * Si tienes dos pantallas, coloca tu juego en la pantalla principal (DISPLAY1) y deja la pantalla secundaria (DISPLAY2) visible.
   * Cada vez que pidas una comparativa de daño, precios o balance de armas, el copiloto generará una tabla interactiva con gráficos y la **abrirá y maximizará automáticamente en tu segundo monitor** sin tapar tu juego ni hacer parpadear la barra de tareas.
4. **Para cerrar el copiloto:**
   * Haz doble clic en **`detener_advisor.bat`** o presiona `Ctrl+C` en la ventana negra. Todos los procesos y micrófonos se cerrarán limpiamente.

---

## 🖥️ Requisitos de Sistema

### Requisitos Mínimos:
* **Sistema Operativo:** Windows 10 o Windows 11 (64-bit).
* **Procesador (CPU):** Intel Core i5 / AMD Ryzen 5 o superior.
* **Memoria RAM:** 8 GB mínimo (16 GB recomendado para multitarea con juegos).
* **Micrófono:** Cualquier micrófono USB, headset o integrado (compatible con Discord y Nvidia Broadcast).
* **Navegador Web:** 
  * **Mozilla Firefox** (Recomendado por ser ultraligero y libre de plugins pesados).
  * **Microsoft Edge** (Viene preinstalado con Windows 10/11; el programa lo detecta automáticamente como respaldo).
  * **Google Chrome**.
* **Conexión a Internet:** Para comunicarse con la API de Gemini y síntesis de voz.

### Requisitos Recomendados (Máximo Rendimiento):
* **Tarjeta Gráfica (GPU):** NVIDIA GeForce RTX (Serie 30 o 40, ej: RTX 3060, 4070 Ti, 4080) con soporte CUDA. Permite ejecutar el modelo local `large-v3-turbo` en `float16` con transcripción casi instantánea. *(Si no tienes tarjeta NVIDIA, el programa funciona automáticamente usando tu CPU).*
* **Configuración de Pantalla:** Dos monitores:
  * **Monitor 1 (Principal):** 1440p (2560x1440) o 1080p para el juego.
  * **Monitor 2 (Secundario):** 1080p para visualizar las tablas, gráficas de daño y estadísticas tácticas.

---

## ❓ Preguntas Frecuentes (FAQ)

### ¿Qué pasa si solo tengo instalado Microsoft Edge en mi PC?
**Funciona a la perfección.** El programa incluye un sistema de detección inteligente:
1. Intenta abrir **Firefox** (si está instalado).
2. Si no tienes Firefox, pasa automáticamente a **Microsoft Edge**, el cual viene integrado en todos los Windows 10 y 11.
3. El programa detecta la ruta oficial de Edge, abre el reporte en una ventana limpia, lo traslada a tu monitor secundario y lo maximiza automáticamente. No tienes que configurar nada.

### ¿Puedo usarlo mientras hablo por Discord o uso otras apps de micrófono?
**Sí.** El audio de Windows permite que múltiples programas escuchen el mismo dispositivo de entrada al mismo tiempo. Puedes estar en llamada con tu escuadrón en Discord y tu copiloto te escuchará sin interferir en la voz de tus compañeros.

### ¿Puede darme baneo el Anti-Cheat del juego?
**No.** El copiloto opera 100% a nivel de sistema operativo:
* No inyecta DLLs ni código dentro del proceso del juego.
* No lee ni modifica la memoria RAM del juego.
* Toma capturas del escritorio de Windows mediante la API estándar de gráficos (Windows Desktop GDI / Desktop Duplication), exactamente igual a cómo lo hace Discord al compartir pantalla o el software de NVIDIA GeForce Experience.

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

## ⚙️ Personalización Avanzada (`config.yaml`)

Si deseas cambiar ajustes más profundos, abre el archivo `config.yaml` con el Bloc de notas:

```yaml
listener:
  mode: "continuous"        # "continuous" (manos libres), "ptt" (pulsar tecla) o "hybrid"
  ptt_key: "f9"             # Tecla de Push-to-Talk
  vad_threshold: 0.012      # Sensibilidad del micro (0.010 a 0.020)
  silence_duration_sec: 1.0 # Segundos de silencio para enviar la pregunta

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
