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
