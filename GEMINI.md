# Reglas de Espacio de Trabajo — Flujo de Integración Git

## 1. Invariante de Protección de Rama
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

