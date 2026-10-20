# LLM Game Advisor — Architecture & Capabilities Blueprint

> Comprehensive technical blueprint and capabilities mapping for the **LLM Voice Tactical Game Advisor** across its 7 architectural pillars, runtime configuration, and data workflows.

---

## Executive Summary

**LLM Game Advisor** is an ultra-low-latency, hands-free tactical gaming copilot built on **Clean Architecture** and **Hexagonal Ports & Adapters**. It monitors the gameplay screen in real time, listens continuously through noise-filtering neural Voice Activity Detection (VAD), responds via high-prosody neural speech synthesis, and renders interactive statistical dashboards on secondary displays without ever stealing Windows OS input focus from the active game.

```
                              ┌───────────────────────────────────┐
                              │     PLAYER & OS ENVIRONMENT       │
                              └─────────────────┬─────────────────┘
                                                │
                 ┌──────────────────────────────┼──────────────────────────────┐
                 │ Audio Input (Mic)            │ Screen (GPU/D3D11)           │ Voice / Display (Output)
                 ▼                              ▼                              ▼
      ┌──────────────────────┐       ┌──────────────────────┐       ┌──────────────────────┐
      │  Pillar 1: AUDIO     │       │  Pillar 2: VISION    │       │  Pillar 7: DASHBOARD │
      │  Silero VAD (ONNX)   │       │  WGC / DXCam / MSS   │       │  Win32 user32 ctypes │
      │  Whisper GPU / CUDA  │       │  Lanczos 1440p➔720p  │       │  SWP_NOACTIVATE      │
      │  F9 PTT / F10 Mute   │       │  Native Region Crops │       │  HTML5 + Chart.js    │
      └──────────┬───────────┘       └──────────┬───────────┘       └──────────▲───────────┘
                 │                              │                              │
                 └──────────────────────┐       │                              │
                                        ▼       ▼                              │
                               ┌────────────────────────────────┐              │
                               │   AdvisorOrchestrator Facade   │──────────────┘
                               └───────┬────────────────┬───────┘
                                       │                │
            ┌──────────────────────────┴────────┐       └─────────────────────────┐
            ▼                                   ▼                                 ▼
 ┌──────────────────────┐            ┌──────────────────────┐          ┌──────────────────────┐
 │  Pillar 3: FAST RAG  │            │  Pillar 4: MULTI-LLM │          │  Pillars 5 & 6:      │
 │  ContextFactualResolv│            │  Resilient Cascade   │          │  META-TUNING &       │
 │  Zero-LLM Sub-3ms    │            │  Circuit Breaker     │          │  DYNAMIC ARCHETYPES  │
 │  SQLite FTS5 BM25    │            │  Gemini / Kimi / NIM │          │  Clarification FSM   │
 │  MindCache L1 LRU    │            │  ModelDiscovery      │          │  ArchetypeScaffolder │
 └──────────────────────┘            └──────────────────────┘          └──────────────────────┘
```

---

## The 7 Architectural Pillars

### 1. Real-Time Audio Perception & Voice Activation

High-responsiveness auditory pipeline designed to prevent microphone feedback, handle noisy Discord environments, and provide instant auditory cues.

* **Neural Voice Activity Detection (Silero VAD)**:
  * Implemented in `src/abi_coach/infrastructure/adapters/audio/silero_vad_detector.py`.
  * Executes an ONNX runtime session (`SILERO_FRAME_SAMPLES = 512` at 16 kHz) bundled via `faster-whisper.vad.get_vad_model()`.
  * Evaluates chunk speech probability. Chunks failing VAD (<0.50 probability) are buffered in a 10-chunk pre-roll queue (`_pre_buffer`) to avoid clipping the first syllable.
  * Robust fallback to Root Mean Square (RMS) energy calculation if neural runtime initialization fails.
* **Whisper GPU Accelerated STT**:
  * Implemented in `src/abi_coach/infrastructure/adapters/audio/whisper_transcriber.py` and `listener.py`.
  * Powered by `faster-whisper` (`large-v3-turbo` model by default) using `float16` precision on NVIDIA CUDA.
  * **Automated CUDA DLL Resolution**: `_setup_cuda_dlls()` dynamically discovers and registers virtualenv NVIDIA wheels (`cublas64_12.dll`, `cublasLt64_12.dll`, `cudnn64_9.dll`, `cudnn_ops64_9.dll`), populating the Windows DLL search directory via `os.add_dll_directory` and `ctypes.CDLL`.
  * **Automatic CPU Fallback**: If GPU VRAM allocation or driver initialization encounters an error, the pipeline automatically re-initializes on CPU with `int8` quantization without crashing the session.
  * **Greedy Beam Decoding**: Default `whisper_beam_size: 1` yields ultra-low transcription latency (<150ms).
* **Global Hotkeys & Push-To-Talk (PTT)**:
  * Implemented in `src/abi_coach/infrastructure/adapters/platform/win32_audio_hotkey.py`.
  * **F10 Global Mute**: Background daemon thread polling `user32.GetAsyncKeyState(0x79)` every 40ms. Allows instant microphone muting while speaking in external VoIP apps (Discord/Teamspeak).
  * **F9 Push-to-Talk (PTT)**: Configurable via `listener.ptt_key`, supporting push-to-talk loop execution alongside continuous hands-free VAD mode.
  * **Non-Blocking Acoustic Feedback**: `play_beep(freq, duration_ms)` launches background threads calling `winsound.Beep` on Windows:
    * `1200 Hz / 40 ms`: Speech detected / recording triggered.
    * `800 Hz / 40 ms`: Silence threshold reached / speech finalized.
    * `500 Hz / 70 ms`: Copilot muted.
    * `1200 Hz ➔ 1500 Hz`: Copilot unmuted.

---

### 2. Real-Time Vision & High-Fidelity Capture

Zero-latency screen acquisition that avoids hooking game binaries or triggering anti-cheat software (BattlEye, Easy Anti-Cheat, ACE).

* **Direct Desktop Capture Pipeline**:
  * Implemented in `src/abi_coach/infrastructure/adapters/vision/capture.py` and `windows_capture_adapter.py`.
  * **Priority 1 — Windows Graphics Capture (WGC / D3D11)**: Modern Windows 10/11 GPU capture pipeline via `windows-capture`. Intercepts GPU frame buffers directly, impervious to Discord/OBS streaming lockouts, and fully compatible with exclusive fullscreen and borderless window modes.
  * **Priority 2 — MSS**: High-performance multi-monitor GDI desktop capture.
  * **Priority 3 — PIL ImageGrab**: Native OS fallback.
* **Lanczos High-Fidelity Downscaler**:
  * Native 1440p (2560x1440) or 4K gaming frames are downscaled to 720p (1280x720) or 1080p using high-order `Image.Resampling.LANCZOS` filtering.
  * Reduces image payload size from ~10 MB raw RGB to ~120 KB JPEG (`jpeg_quality: 75`), decreasing multimodal LLM network transfer latency by over 80% while preserving optical legibility of fine UI text, crosshairs, and ammunition counters.
* **Native-Resolution Region of Interest (ROI) Cropping**:
  * Configurable in `config.yaml` under `capture.regions`.
  * Crops critical interface sections (stash, ammunition stats, flea market prices) from the unscaled 1440p frame *prior* to downscaling, passing loss-free crops directly to the multimodal model.
* **OS Error Avoidance**:
  * Runs screen grabs inside a dedicated single-threaded executor (`_CAPTURE_EXECUTOR = ThreadPoolExecutor(max_workers=1)`), preventing Windows GDI desktop lock collisions (`ERROR_BUSY` 170).

---

### 3. Fast-Path Deterministic RAG (Zero-LLM Sub-3ms Latency)

Immediate factual stat lookups that bypass generative cloud LLMs completely, guaranteeing 0 token cost and sub-3ms voice replies.

* **Zero-LLM Fast-Path Routing**:
  * Implemented in `src/abi_coach/application/services/context_factual_resolver.py` and `advisor_orchestrator.py`.
  * Intercepts incoming queries matching `STAT_TRIGGERS` (e.g., *"qué penetración"*, *"cuánto daño"*, *"qué tier"*, *"cuánto vale"*, *"precio de"*).
  * Evaluates query keywords without invoking any external API. Returns structured factual answers in ~1.5ms.
* **SQLite FTS5 BM25 Knowledge Retrieval**:
  * Implemented in `src/abi_coach/application/slices/tactical_rag/rag.py`.
  * Uses SQLite Full-Text Search 5 (`game_knowledge_fts`) with prefix tokens (`"token"*`) and BM25 ranking (`ORDER BY rank`).
  * Normalizes games across aliases (`abi`, `arena_breakout`, `once_human`, `generic`).
* **L1 In-Memory LRU Cache (`MindCacheLRU`)**:
  * Implemented in `src/abi_coach/infrastructure/adapters/storage/cache.py`.
  * In-memory cache holding up to 128 items with configurable TTL (default 300s).
  * Direct entity lookup by primary key (`get_entity`) completes in `<0.05ms`.
* **Hybrid Multimodal Augmentation**:
  * When an image is attached or a prompt requires broad tactical reasoning, `format_context_for_prompt()` retrieves verified factual records and injects them as canonical ground truth (`[BASE DE DATOS TÁCTICA VERIFICADA DEL JUEGO]`) directly into the LLM system prompt.

---

### 4. Resilient Multimodal LLM & Dynamic Preflight

Fault-tolerant cloud orchestration across multiple AI providers with automatic health inspection, circuit breakers, and quota failover.

* **Multi-Provider Architecture**:
  * Implemented in `src/abi_coach/infrastructure/adapters/llm/`.
  * **Google Gemini Adapter (`gemini_adapter.py`)**: Google GenAI SDK (`gemini-3.5-flash`, `gemini-3.1-flash-lite`, `gemini-2.5-flash`). Features native multimodal vision, zero thinking budget option (`thinking_budget: 0`) for conversational speed, and adjustable `media_resolution` (medium/low).
  * **Moonshot AI / Kimi Adapter (`moonshot_adapter.py`)**: OpenAI-compatible REST adapter for Moonshot's `kimi-k2.6` model. Supports both international (`https://api.moonshot.ai/v1`) and regional fallback (`https://api.moonshot.cn/v1`) endpoints.
  * **NVIDIA NIM Adapter (`nvidia_adapter.py`)**: OpenAI-compatible vision client integrating NVIDIA API catalog models (such as `meta/llama-3.2-11b-vision-instruct`).
* **Circuit Breaker Pattern (Michael Nygard / Release It!)**:
  * Implemented in `src/abi_coach/infrastructure/adapters/llm/circuit_breaker.py`.
  * Maintains thread-safe three-state machines per provider: `CLOSED` ➔ `OPEN` ➔ `HALF_OPEN`.
  * If a provider exceeds `failure_threshold: 2` consecutive errors, its circuit trips to `OPEN`, immediately failing fast without incurring network latency.
  * After `recovery_timeout_sec: 30.0` seconds, the circuit transitions to `HALF_OPEN` to probe provider health with a trial request.
* **Resilient Hot Failover Cascade**:
  * Implemented in `src/abi_coach/infrastructure/adapters/llm/resilient_orchestrator.py`.
  * Sequentially executes primary provider ➔ fallback providers (e.g., `gemini-3.5-flash` ➔ `gemini-lite` ➔ `moonshot` ➔ `nvidia`).
  * Emits runtime failover events (`on_failover`) with spoken acoustic warnings to the gamer.
* **Dedicated Quota Error Handling (HTTP 429)**:
  * In `MoonshotAdapter`, detects `exceeded_current_quota_error`, `insufficient_balance`, and quota strings, categorizing them into `MOONSHOT_QUOTA_ERROR`.
  * Marks the error as non-retryable for the current provider and immediately trips failover to the next candidate without crashing.
* **Dynamic Model Discovery Service**:
  * Implemented in `src/abi_coach/application/services/model_discovery.py`.
  * `ModelDiscoveryService`:
    * Inspects API credentials in environment (`GEMINI_API_KEY`, `MOONSHOT_API_KEY`, `NVIDIA_API_KEY`).
    * Queries `genai.Client.models.list()` filtering for active models with `generateContent` support.
    * Verifies Moonshot connectivity against `/v1/models` across international and regional URLs.
    * Returns a `DiscoveredModelsReport` and dynamically builds the optimal fallback cascade.

---

### 5. Conversational Meta-Tuning & Self-Calibration

In-game conversational configuration and rule management allowing players to tune the advisor mid-game using natural speech.

* **Intent Parsing & Classification**:
  * Implemented in `src/abi_coach/application/slices/metatuning/intent_parser.py`.
  * Analyzes verbal commands for four core intents (`MetaTuningIntent`):
    * `CONFIG`: Micro adjustments, volume, TTS voice changes, monitor selection.
    * `RULE`: Tactical behavior rules (e.g., *"prioriza daño contra blindajes"*).
    * `PROMPT`: Custom system instruction adjustments.
    * `RAG`: In-game manual factual additions.
  * Categorizes operational domains: `loot`, `combat`, `voice`, and `general`.
* **Clarification Finite State Machine (FSM)**:
  * Implemented in `src/abi_coach/application/slices/metatuning/clarification_fsm.py`.
  * When a player gives a vague instruction (e.g., *"cambia mi modo de combate"*), the FSM triggers a clarification state (`ClarificationState`) with a **60-second TTL** (`CLARIFICATION_TTL_SEC = 60.0`).
  * The advisor asks a structured multiple-choice follow-up question.
  * If the player answers within 60s, `resolve()` pairs the resolution rule and saves it. If the player says *"cancela"*, *"olvídalo"*, or *"déjalo"*, `is_cancellation()` resets the state.
* **Atomic Runtime Configuration Mutation**:
  * Implemented in `src/abi_coach/application/services/config_mutator.py`.
  * `ConfigMutator.mutate(key_path, value)`:
    * Updates in-memory attributes of `AppConfig` immediately.
    * Atomically patches `config.yaml` on disk using a temporary file (`.tmp_<PID>`) followed by `replace()` to prevent file corruption during sudden system shutdowns.
* **Persistent Engram Memory Observations**:
  * Saves learned rules into persistent SQLite storage as `EngramObservation` records (`scope="project"`, `pinned=True`, `observation_type="rule"`).
  * Automatically injects these calibrated rules into subsequent conversation turns.

---

### 6. Zero-Seeder Dynamic Archetypes

Game-agnostic architecture enabling immediate, zero-code onboarding of any game title through dynamic domain scaffolding.

* **Autonomous Archetype Detection**:
  * Implemented in `src/abi_coach/application/slices/archetypes/scaffolder.py`.
  * Inspects game title and contextual hints to classify the game into domain archetypes:
    * `rpg_mmo`: Fantasy/MMO signals (Elden Ring, WoW, Diablo — stats, affixes, mana, leveling).
    * `extraction_shooter`: Tactical shooter signals (Arena Breakout, Escape from Tarkov, Hunt: Showdown — ammo tiers, loot value, extraction).
    * `survival_craft`: Base building and crafting signals (Once Human, Rust, ARK, Palworld — calibrations, blueprints, durability).
    * `general_companion`: Universal fallback for any other genre.
* **Dynamic Topic Scaffolding (`bootstrap_context`)**:
  * Provisions a new game context (`TopicContext`) in SQLite without writing Python code or restarting the app.
  * Automatically creates foundational Engram memory entries:
    * `{context_id}/player/profile`: Tracks player preferences and loadout tendencies.
    * `{context_id}/rules/tactical`: Embeds the archetype's default prompt template and tactical rules.
* **On-the-Fly Entity Ingestion (`auto_ingest_fact`)**:
  * Discovers new game entities via OCR/vision or conversational dialogue and indexes them immediately as `DynamicEntity` items in SQLite.
* **Dynamic Prompt Formatting**:
  * Implemented in `src/abi_coach/application/slices/archetypes/prompt_formatter.py`.
  * `ArchetypePromptFormatter`:
    * Formats active Engram observations (`[MEMORIA PERSISTENTE ENGRAM - CONTEXTO: {ID}]`).
    * Formats dynamic context entities with confidence ratings and facet JSON (`[ENTIDADES DINÁMICAS DEL CONTEXTO]`).

---

### 7. Win32 Tactical Dashboards & Focus-Safe Multi-Display

Interactive, real-time secondary-screen visualization providing tactical depth without compromising in-game keyboard or mouse control.

* **Multi-Monitor Secondary Display Detection**:
  * Implemented in `src/abi_coach/infrastructure/adapters/platform/win32_window_manager.py`.
  * Uses `user32.EnumDisplayMonitors` and `GetMonitorInfoW` via `ctypes` to locate non-primary working area bounds (`(x, y, width, height)`).
* **Focus-Safe Window Positioning (`SWP_NOACTIVATE`)**:
  * When opening or refreshing the tactical dashboard, the window manager restores and positions the browser on `DISPLAY2`.
  * Crucially, when `focus_browser: false`, it applies `SetWindowPos` with flags:
    ```c
    SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW | SWP_NOACTIVATE
    ```
  * **Result**: The browser unminimizes and maximizes on the secondary monitor *without stealing input focus*. The player maintains uninterrupted aim, movement, and shooting control in the game.
* **Cross-Browser Binary Discovery**:
  * Implemented in `src/abi_coach/infrastructure/adapters/platform/browser_launcher.py`.
  * Automatically probes Windows registry keys (`SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths`) and standard 64-bit/32-bit install paths for Mozilla Firefox, Google Chrome, and Microsoft Edge.
* **Interactive HTML5 / Chart.js Presenter**:
  * Implemented in `src/abi_coach/infrastructure/presentation/dashboard_presenter.py` and `src/abi_coach/infrastructure/resources/templates/tactical_report.html`.
  * Renders ballistic comparisons, tier badges (Tier 1–6 color codes), damage/penetration bar charts via Chart.js, and active Engram memory cards.
  * Enforces strict `Content-Security-Policy` (`default-src 'none'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net`).

---

## Static Seeding vs. Dynamic Scaffolding

The platform supports two complementary knowledge ingestion workflows:

| Dimension | Static Seeding (`KnowledgeRAG`) | Dynamic Scaffolding (`ArchetypeScaffolder`) |
| :--- | :--- | :--- |
| **Primary Target** | Curated official titles (e.g., Arena Breakout) | Any new or unlisted game title (e.g., Once Human, Rust) |
| **Data Source** | Static JSON file (`abi_knowledge.json`) | Runtime OCR, vision capture, and conversational dialogue |
| **Startup Behavior** | Automatic batch insert on empty table (`_ensure_seed_loaded`) | On-demand context provisioning via `bootstrap_context()` |
| **Code Requirement** | Pre-authored JSON schema | **Zero code**: dynamic entity schema generation |
| **Storage Engine** | SQLite `game_knowledge` table + FTS5 full-text index | SQLite `archetype_contexts` + `archetype_entities` + Engram |
| **Domain Categorization** | Fixed manual tags (`ammo`, `weapon`, `armor`) | Heuristic archetype classification (`rpg_mmo`, `survival_craft`, etc.) |
| **Cache Invalidation** | Invalidates L1 LRU memory cache on upsert | Direct insertion into context-aware dynamic registry |

---

## Full Configuration Reference

The application reads configuration hierarchically: **CLI Arguments ➔ Environment Variables (`.env`, `keys.env`) ➔ YAML Configuration (`config.yaml`) ➔ Hardcoded Domain Defaults**.

### 1. `config.yaml` Schema

```yaml
# ==========================================
# ABI Coach - Archivo de Configuración
# ==========================================

# Active primary LLM provider: "gemini" or "nvidia"
llm:
  provider: "gemini"

# Resilient Orchestrator (Circuit Breaker & Hot Failover)
resilience:
  enabled: true                 # Enable fallback cascade
  failure_threshold: 2          # Consecutive errors to trip circuit to OPEN
  recovery_timeout_sec: 30.0    # Cool-off period before testing recovery (HALF_OPEN)
  fallback_cascade:             # Ordered contingency cascade
    - "gemini-lite"
    - "moonshot"
    - "nvidia"

gemini:
  model: "gemini-3.5-flash"     # Optimal speed and multimodal accuracy
  media_resolution: "medium"    # Image resolution: high, medium, low
  thinking_budget: 0            # 0 = disabled for minimal voice latency
  max_output_tokens: 250        # Output token limit for spoken brevity
  game: "once_human"            # Active game context ID
  temperature: 0.2              # Temperature for factual determinism

moonshot:
  model: "kimi-k2.6"            # Kimi model
  base_url: "https://api.moonshot.ai/v1" # International API endpoint
  api_key_env: "MOONSHOT_API_KEY"
  temperature: 0.3
  max_tokens: 250
  timeout_sec: 6.0

nvidia:
  model: "meta/llama-3.2-11b-vision-instruct"
  base_url: "https://integrate.api.nvidia.com/v1"
  api_key_env: "NVIDIA_API_KEY"
  temperature: 0.2
  max_tokens: 500

capture:
  monitor_index: 1              # 1 = Primary gaming display
  downscale_width: 1280         # Target downscale width
  downscale_height: 720         # Target downscale height (1440p -> 720p)
  jpeg_quality: 75              # JPEG compression quality
  save_captures: false          # Debug save to disk
  capture_dir: "captures"
  regions: {}                   # Optional ROI crops (e.g., stash, flea market)

listener:
  mode: "continuous"            # "continuous" (VAD hands-free) or "ptt"
  ptt_key: "f9"                 # Push-To-Talk key
  mute_key: "f10"               # Global VoIP mute toggle
  sample_rate: 16000            # Standard 16kHz audio
  vad_threshold: 0.020          # Silero VAD / RMS sensitivity
  silence_duration_sec: 1.6     # Silence window before speech finalization
  min_duration_sec: 0.4         # Minimum speech length (filters coughs/clicks)
  wake_word: null               # Optional wake word (e.g., "coach")
  whisper_model: "large-v3-turbo" # faster-whisper model
  whisper_device: "cuda"        # "cuda" (GPU) or "cpu"
  whisper_compute_type: "float16" # "float16" for GPU, "int8" for CPU
  whisper_beam_size: 1          # 1 = ultra-fast greedy decoding
  language: "es"                # Transcription language

speaker:
  engine: "edge-tts"            # Speech synthesis engine
  voice: "es-CO-SalomeNeural"   # Recommended natural female voice
  rate: "+0%"                   # Speed adjustment
  volume: "+0%"                 # Volume adjustment
  pitch: "+0Hz"                 # Pitch adjustment

reports:
  output_dir: "reports"         # HTML report output directory
  auto_open_browser: true       # Auto-open dashboard upon generation
  focus_browser: false          # FALSE: positions on DISPLAY2 without stealing focus
  preferred_browser: "firefox"  # "firefox", "edge", or "chrome"

history:
  max_turns: 5                  # Conversation history turns retained in context
```

### 2. Environment Variables (`.env`, `keys.env`, `keys.yaml`)

The application searches for credentials in `keys.env`, `.env`, and `keys.yaml` in both the executable root and current working directory:

| Environment Variable | Target Provider | Description |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini | API key obtained from [Google AI Studio](https://aistudio.google.com/). Required for default multimodal reasoning. |
| `MOONSHOT_API_KEY` | Moonshot AI (Kimi) | API key from [Moonshot Platform](https://platform.moonshot.cn/). Used for resilient text/multimodal failover. |
| `NVIDIA_API_KEY` | NVIDIA NIM | API key from [NVIDIA Build](https://build.nvidia.com/). Required when utilizing NVIDIA cloud vision endpoints. |

### 3. Command Line Interface (CLI) Flags

Executed via `uv run python -m abi_coach [FLAGS]` or standalone binary:

| Flag | Argument | Description |
| :--- | :--- | :--- |
| *(None)* | — | Starts the live hands-free interactive voice loop (`run_interactive_loop`). |
| `--ask` | `"<PROMPT>"` | Sends a one-off multimodal query with live screen capture without activating the microphone. |
| `--game` | `"<ID>"` | Overrides the active game preset (e.g., `abi`, `once_human`, `generic`). |
| `--config` | `"<PATH>"` | Specifies a custom YAML configuration file path. |
| `--test-capture` | — | Executes an immediate screen capture and displays latency and compression metrics. |
| `--test-mic` | — | Records 3 seconds from the configured microphone and prints Whisper transcription. |
| `--test-tts` | `"<TEXT>"` | Tests neural audio synthesis with the supplied test sentence. |
| `--voice` | `"<ID>"` | Temporarily overrides the speaker voice for `--test-tts`. |
| `--list-models` | — | Connects to Google AI Studio and lists models authorized for the active key. |
| `--list-voices` | — | Displays the curated catalog of natural female TTS voices (Salomé, Elvira, Ximena, Camila, Paloma). |
| `--check-updates` | — | Checks GitHub releases for available software updates. |

---

## Verification & Architecture Compliance

* **Clean Architecture Invariants**:
  * `Domain`: Holds pure business entities, value objects (`Result`, `TokenUsage`), and ports. Contains zero platform or I/O imports.
  * `Application`: Orchestrates use cases, FSMs, pipelines, and slice managers. Strictly decoupled from Windows `ctypes` and raw HTTP.
  * `Infrastructure`: Encapsulates all Win32 APIs, DirectX/WGC screen capture, sound drivers, SQLite storage, and cloud LLM adapters.
* **Testing & Linting Commands**:
  ```bash
  # Execute full test suite
  uv run pytest -q

  # Verify architectural layer boundaries and forbid circular dependencies
  uv run lint-imports

  # Run static code analysis and linting
  uv run ruff check src tests
  ```
