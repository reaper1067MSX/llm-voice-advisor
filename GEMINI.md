# Reglas de Espacio de Trabajo — Flujo de Integración Git

## 1. Invariante de Protección de Rama y Gobernanza

### 1.1. Dueño y Aprobador Único del Repositorio (AP Gate)
* **Aprobador Exclusivo**: El único usuario facultado para autorizar la integración de cambios en el repositorio es `reaper1067MSX` (Santiago Argüello).
* **Prohibición de Auto-Merge**: Ningún agente de IA o subagente tiene permitido ejecutar `gh pr merge`, push a ramas protegidas ni dar por concluido un PR sin la confirmación explícita de aprobación (`AP`, "aprobado", "mergea") otorgada por el dueño en la conversación para ese PR puntual.

### 1.2. Protección de Ramas
* **PROHIBIDO hacer push directo a `master` o `main`**: El comando `git push origin master` o `git push origin main` está estrictamente vetado.
* Todo cambio, refactorización, corrección o nueva funcionalidad debe desarrollarse en una rama separada y unirse únicamente mediante un **Pull Request**.

## 2. Flujo de Trabajo Obligatorio para Cambios

### Paso 1: Crear la rama de trabajo
```bash
git checkout -b <tipo>/<nombre-descriptivo>
```
*Ejemplos:* `feat/bulletin-system`, `fix/audio-listener-memory`, `refactor/clean-architecture`.

### Paso 2: Commits por unidad de trabajo (Conventional Commits)
* Seguir estrictamente la convención: `<tipo>(<alcance>): <descripcion>`
* Mantener tests y documentación en el mismo commit que introduce el cambio.
```bash
git commit -m "<tipo>(<alcance>): <descripcion clara del resultado>"
```

### Paso 3: Subir la rama a GitHub
```bash
git push -u origin <tipo>/<nombre-descriptivo>
```

### Paso 4: Crear el Pull Request con GitHub CLI
```bash
gh pr create --title "<tipo>(<alcance>): <titulo del PR>" --body "<resumen conciso de cambios y verificacion>"
```

### Paso 5: Fusionar el Pull Request y limpiar la rama
```bash
gh pr merge --squash --delete-branch
```

### Paso 6: Sincronizar la rama local master
```bash
git checkout master
git pull origin master
```

## 3. Estándar para Planes de Arquitectura Compleja

Cuando una tarea involucre refactorizaciones estructurales, nuevos subsistemas, orquestación de agentes o integraciones de alta complejidad, el artefacto o plan de diseño DEBE cumplir con los siguientes estándares rigurosos antes de la implementación:

1. **Fuentes y Recursos Confiables**:
   * Citar documentación oficial, bibliotecas existentes, RFCs o literatura de ingeniería de software relevante. No inventar mecanismos caseros si existe un estándar probado en la industria (ej. Silero VAD, Blackboard Pattern, Supervisor-Worker).

2. **Diagramas Formales de Arquitectura (Mermaid)**:
   * **Diagrama de Clases (`classDiagram`)**: Entidades, Value Objects, Puertos/Interfaces, Adaptadores y cómo se relacionan (herencia, composición, dependencia).
   * **Diagrama de Secuencia (`sequenceDiagram`)**: Flujo cronológico de mensajes, llamadas síncronas/asíncronas y manejo de estados y excepciones.

3. **Patrones de Diseño Formales**:
   * Identificar y justificar explícitamente los patrones aplicados (ej. State Pattern, Blackboard, Supervisor-Worker, Strategy, Observer, Result Pattern, Middleware Pipeline).

4. **Principios de Ingeniería de Software**:
   * **SOLID**: Demostrar SRP (responsabilidad única), OCP (abierto/cerrado), LSP (sustitución), ISP (segregación de interfaces) y DIP (inversión de dependencias).
   * **KISS & YAGNI**: Mantener la solución lo más simple posible sin sobreingeniería innecesaria.
   * **DRY**: Evitar duplicación de lógica mediante abstracciones limpias.
   * **Clean Architecture**: Regla de dependencia unidireccional (Dominio <- Aplicación <- Infraestructura / Presentación).

5. **Mapeo Explícito en el Árbol de Código**:
   * Listar las rutas exactas de archivos a crear o modificar (`src/...`, `tests/...`, `presets/...`) indicando qué clase o función residirá en cada ubicación.

## 4. Estándar de Evaluación y Adopción de Herramientas y Librerías

Al seleccionar, recomendar o reemplazar cualquier herramienta, librería, API de sistema o modelo de IA, se debe seguir estrictamente este protocolo de evaluación antes de su integración:

### 1. Prioridad: Modernidad y Mantenimiento Activo (Adopt vs. Hold)
* **Herramientas Modernas como Primera Opción (`Adopt`)**: Se debe priorizar siempre la tecnología más actual, respaldada por la arquitectura nativa del sistema operativo objetivo (ej. Windows Graphics Capture / Direct3D11 sobre GDI BitBlt, Silero VAD sobre umbrales de energía simples, modelos con endpoints optimizados).
* **Librerías Legacy solo como Fallback (`Hold`)**: Las herramientas antiguas o monolíticas solo se admiten como mecanismos secundarios de contingencia en caso de que el entorno host carezca del soporte moderno. Nunca serán la ruta de ejecución primaria.
* **Verificación de Mantenimiento**: Comprobar en GitHub/PyPI que la librería tenga commits recientes, soporte para las versiones actuales del lenguaje/SO y resolución activa de issues.

### 2. Ecuación Costo-Beneficio: Compatibilidad y Tiempo de Procesamiento
Toda herramienta debe evaluarse en dos ejes fundamentales:
* **Compatibilidad en Condiciones Reales de Uso**: Evaluar cómo interactúa la herramienta con el stack completo del usuario (ej. streaming en Discord/OBS, aceleración por hardware GPU, overlays de juegos, drivers de audio). Si una herramienta falla en presencia de software de streaming o DirectX, queda descalificada como opción primaria.
* **Tiempo de Procesamiento (Latencia)**: Medir el costo en milisegundos de la operación. En flujos de interacción en tiempo real o voz, cualquier herramienta o modelo cuya latencia supere los requerimientos de respuesta (<2-3s) debe ser sustituida o desacoplada a procesamiento asíncrono.

### 3. Investigación Exhaustiva Previa
Antes de proponer una nueva dependencia o arquitectura:
* Investigar a fondo en **Stack Overflow, Google, documentación oficial y GitHub Issues** los problemas conocidos, colisiones con software de terceros (ej. Discord hooks, antivirus, DirectX swapchains) y alternativas modernas recomendadas por la comunidad técnica.
* Contrastar con paradigmas de ingeniería de software (ATAM, ThoughtWorks Tech Radar) para justificar técnicamente el tradeoff adoptado.

### 4. Validación Empírica Mediante Spike
* No asumir que una librería funcionará basándose solo en su documentación. Ejecutar una prueba técnica directa (spike) que mida latencia y valide compatibilidad con el entorno real antes de dar por cerrada la solución.

## 5. Estándar de Detección de Code Smells y Erradicación de Antipatrones de Arquitectura

Para garantizar legibilidad, bajo costo cognitivo, facilidad de navegación en IDEs y mantenibilidad a largo plazo, todo desarrollo en este repositorio debe respetar estrictamente los siguientes guardrails de diseño:

### 1. Guardrail de Tamaño y Cohesión (Anti-God Object)
* **Límite de Tamaño de Archivo**: Ningún archivo en las capas `domain/` o `application/` debe exceder **250 líneas de código**. Si un archivo supera este umbral, es una alerta automática de mezcla de responsabilidades.
* **Principio de Responsabilidad Única (SRP)**: Cada clase o archivo debe tener una única razón para cambiar. Los casos de uso (`UseCases`) representan la orquestación de un proceso de negocio atómico (ej. `TacticalQueryOrchestrator`, `GameContextSwitchUseCase`), no silos multifunción ni fragmentaciones artificiales por tecnología de persistencia o tiempo de respuesta.
* **Descomposición con Fachada Delgada (Thin Facade)**: Cuando se refactorice un componente histórico grande, la clase original debe mantenerse temporal o permanentemente como una fachada delegadora delgada (<150 líneas), garantizando 100% de retrocompatibilidad con las capas de presentación (`loop.py`, `cli.py`) y tests existentes.

### 2. Guardrail de Aislamiento de Capas (Anti-Leaky Abstraction)
* **Prohibición de Infraestructura en Aplicación/Dominio**: Queda terminantemente prohibido importar librerías de infraestructura de bajo nivel (ej. `ctypes`, APIs Win32 `user32`/`gdi32`, clientes HTTP directos o drivers de hardware) dentro de `src/abi_coach/application/` o `src/abi_coach/domain/`.
* **Inversión de Dependencias (DIP)**: La capa de Aplicación solo define e interactúa con Puertos (`Protocol`). Todo acceso a hardware, sistema operativo o red debe residir en adaptadores dentro de `src/abi_coach/infrastructure/adapters/`.

### 3. Tipado Robusto y Erradicación de Obsesión Primitiva
* Prohibido propagar diccionarios crudos `Dict[str, Any]` para datos de dominio o comunicación entre capas.
* Toda transferencia de información entre puertos y adaptadores debe modelarse mediante **Value Objects** o **DTOs inmutables** (`@dataclass(frozen=True)`).
* Toda operación propensa a fallas de red, parsing o infraestructura debe retornar el **Result Pattern** (`Result[Success[T], Failure[DomainError]]`), erradicando excepciones no controladas o bloques genéricos `except Exception: pass`.

### 4. Protocolo de Refactorización Segura (Safety Net)
* Antes de modificar o extraer código de una clase con alta carga histórica, se debe verificar que la suite de pruebas automatizadas (`uv run pytest`) esté al 100% en verde.
* Cada nuevo Caso de Uso o Servicio de Dominio extraído debe acompañarse de sus pruebas unitarias aisladas en `tests/`.

### 5. Orquestación Genérica de Procesos y Segregación de Contextos (Orchestrator & Strategy Pattern)
* **Tríada de Consulta: Query, Contexto y Orquestador**:
  1. **Query Genérica (Agnóstica de Información)**: La consulta (`TacticalQuery`) es un contrato o DTO puro que encapsula la entrada del usuario (texto, audio, imagen) sin conocer reglas específicas, tablas de base de datos ni lógica cableada de ningún juego.
  2. **Contexto Autónomo (Funcionalidad y Conocimiento Propio)**: Cada contexto de juego (`GameContext`, ej. ABI, Once Human) encapsula su propia funcionalidad: sus reglas factuales deterministas, perfiles arquetípicos y repositorio de conocimiento RAG. El contexto es el dueño de la información de su dominio.
  3. **Orquestador General de Procesos**: Existe un único proceso orquestador (`TacticalQueryOrchestrator`) que unifica la resolución: consulta al contexto activo si puede resolver deterministamente (sub-2ms), y si no, orquesta el enriquecimiento contextual y la inferencia generativa multimodal con el LLM.
* **Prohibición de Fragmentación de Casos de Uso por Capa de Ejecución**: Queda prohibido crear casos de uso separados para "Fast Path" y "LLM Advice". La decisión de resolver por caché/reglas locales o por modelo generativo es una estrategia interna del orquestador, transparente para quien consume la API.

### 6. Estándar de Cohesión e Higiene en Pruebas Unitarias (Clean Tests)
* **Principio de Responsabilidad Única en Tests**: Cada archivo de prueba en `tests/` debe validar un único componente, servicio o caso de uso. Prohibido acumular pruebas heterogéneas en archivos monolíticos.
* **Erradicación del Import Clumping**: Los tests deben importar sus dependencias directamente desde el módulo origen de verdad, nunca a través de fachadas delegadoras ni re-exportaciones convenientes.
* **Enfoque en Comportamiento Observable**: Eliminar pruebas triviales que solo verifiquen asignaciones de atributos en constructores o llamadas a mocks sin valor semántico. Las pruebas deben validar contratos, transiciones de estado y respuestas ante fallos.

### 7. Dominio Puro y Segregación de Constantes, Enums y Records
* **Prohibido el Amontonamiento de Constantes**: Queda terminantemente prohibido definir tuplas, listas de palabras clave, diccionarios de configuración o constantes de negocio dentro de clases de lógica o archivos de aplicación.
* **Tipado Estricto con Enums y Records**:
  - Todo conjunto discreto de intenciones, categorías, estados, eventos o modos debe modelarse como un **Enum** (`StrEnum` / `Enum`) en `src/abi_coach/domain/enums/`.
  - Toda estructura de datos de intercambio, resolución o parsing debe modelarse como un **Record inmutable** (`@dataclass(frozen=True)`) en `src/abi_coach/domain/entities/`.
* **Cero Duplicación de Reglas de Negocio**: Constantes globales (ej. frases de cancelación, tablas de resolución de clarificaciones, mapeo de voces) deben residir en un único archivo de verdad en `domain/` y ser consumidas por inyección o importación directa.

### 8. Erradicación de Superclases, Fuga de UI y Compresión Artificial de Código
* **Prohibición de Superclases Multipropósito**: Una clase jamás debe acumular lógica de parsing, persistencia, manejo de concurrencia y formateo. Si una clase requiere más de una responsabilidad, debe dividirse en servicios atómicos colaborativos.
* **Prohibición de Compresión de Código (*Code Packing*)**:
  - Queda estrictamente prohibido usar punto y coma (`;`) para encadenar sentencias o atributos en una sola línea, o comprimir bloques `if`/`with` en la misma línea para burlar los guardrails de LOC.
  - La reducción de líneas se logra **extrayendo legítimamente clases, registros y funciones a sus propios archivos**, respetando el espaciado limpio y las convenciones de PEP 8.
* **Aislamiento de Presentación y UI**: Ningún archivo en `application/` debe concatenar ni interpolar cadenas HTML o CSS directamente. El renderizado visual es responsabilidad exclusiva de plantillas externas (`resources/templates/`) o presentadores dedicados en la capa de infraestructura/presentación.



