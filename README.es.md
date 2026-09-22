# FIA Core

[![CI](https://github.com/mcpedrogm-art/fia-core/actions/workflows/ci.yml/badge.svg)](https://github.com/mcpedrogm-art/fia-core/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/fia-core-full)](https://pypi.org/project/fia-core-full/)
[![Versiones de Python](https://img.shields.io/pypi/pyversions/fia-core-full)](https://pypi.org/project/fia-core-full/)
[![Licencia: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/mcpedrogm-art/fia-core/blob/main/LICENSE)

**Verificación local y mínima para trabajo de agentes.**

`PROJECT → (SPEC) → TASK → TEST → VERIFY → STATUS`

FIA Core no pretende ser un sistema de documentación ni un gestor de proyectos.
Hace que unas pocas condiciones de trabajo sean comprobables mecánicamente: una
tarea marcada `done` debe tener un test que pasa, ejecutado con el comando exacto
que declara la tarea, contra el contenido actual del archivo de tarea.

**[English](https://github.com/mcpedrogm-art/fia-core/blob/main/README.md)** ·
[Arquitectura](https://github.com/mcpedrogm-art/fia-core/blob/main/docs/ARCHITECTURE.md) ·
[Changelog](https://github.com/mcpedrogm-art/fia-core/blob/main/CHANGELOG.md)

## Instalación

```bash
pip install fia-core-full
```

La distribución en PyPI se llama `fia-core-full`; instala el comando `fia` y el
paquete Python `fia_core`. Python 3.8+ · sin dependencias.

Desde el código fuente:

```bash
git clone https://github.com/mcpedrogm-art/fia-core
cd fia-core
pip install .
```

## Iniciar un proyecto

```bash
cd mi-proyecto
fia init
```

Crea `PROJECT.md`, `TASK.md` y `.fia/`. Nunca sobrescribe archivos existentes.
`fia init` pregunta qué módulos opcionales quieres (Enter = solo Core).

En scripts:

```bash
fia init --modules ui,security
fia module list          # los 13 packs
fia module enable rag    # añadir uno después
```

## El flujo de trabajo

### 1. Describe el proyecto

Completa `PROJECT.md`: nombre y propósito. Opcionalmente crea `SPEC.md` con
`fia init --with-spec`; si existe, debe tener contenido real.

### 2. Escribe la tarea

`TASK.md` tiene un estado y cuatro secciones obligatorias:

```markdown
Status: done

## Objective

Añadir el formulario de login.

## Scope

- src/login.py
- tests/test_login.py

## Done when

- `python -m unittest` pasa

## Test command

python -m unittest
```

`Test command` debe contener exactamente una línea de comando.

### 3. Ejecuta el test

```bash
fia test -- python -m unittest
```

`fia test` ejecuta el comando y guarda un registro TEST en `.fia/tests/` con
hashes SHA-256 de la salida y del `TASK.md` actual.

### 4. Verifica

```bash
fia verify
```

`PASS` exige contenido real en proyecto y tarea, registros TEST intactos y — si
la tarea está `done` — un TEST exitoso cuyo comando coincida con el
`Test command` declarado y cuyo hash de `TASK.md` siga siendo el actual.

### 5. Consulta el estado

```bash
fia status
```

> **Una regla para recordar:** si editas `TASK.md` después de `fia test`, vuelve
> a ejecutar `fia test`. El gate de `done` está atado al contenido actual de
> `TASK.md`.

## Comandos

| Comando | Para qué sirve |
|---|---|
| `fia init [-d DIR] [--modules LISTA] [--assets URL]` | Crea los archivos del proyecto |
| `fia test [-d DIR] [--timeout SEGUNDOS] -- COMANDO` | Ejecuta y registra un test |
| `fia verify [-d DIR]` | Comprueba el gate (PASS/FAIL) |
| `fia status [-d DIR]` | Resumen de tarea y verificación |
| `fia module list\|enable\|disable\|info NOMBRE` | Packs de capacidad opcionales |
| `fia ui setup\|status` | Pack UI/UX (descarga opt-in, verificada por SHA-256) |
| `fia assets fetch\|manifest` | Packs de assets verificados |

## Núcleo y módulos opcionales

El núcleo de enforcement son unas 600 líneas de Python sin dependencias más 30
tests; es lo único que ejecuta `fia verify`.

Alrededor vienen trece packs de capacidad, desactivados por defecto. Activar uno
copia su documentación a `docs/fia/<name>/` y nunca cambia lo que comprueba
`fia verify`. El pack UI/UX es intencionadamente completo (Design DNA, cuatro
direcciones divergentes, recetas de sección, movimiento, accesibilidad, flujo de
assets). `ui` y `assets` son los únicos packs con código (~200 líneas): comandos
explícitos, opt-in y verificados por SHA-256.

## Confianza y procedencia

- La distribución en PyPI es `fia-core-full` (el nombre `fia-core` no está
  disponible en PyPI); instala el comando `fia` y el paquete `fia_core`.
- Las releases se publican desde este repositorio con trusted publishing de PyPI
  (OIDC): solo `.github/workflows/publish.yml` de `mcpedrogm-art/fia-core` puede
  subir a <https://pypi.org/project/fia-core-full/>. No se guarda ningún token.
- Cada release la construye GitHub Actions desde un commit etiquetado, y el CI
  ejecuta la suite completa en Python 3.9, 3.11 y 3.13.

## Documentación

- [Arquitectura](https://github.com/mcpedrogm-art/fia-core/blob/main/docs/ARCHITECTURE.md)
- [Auditoría de la extracción](https://github.com/mcpedrogm-art/fia-core/blob/main/docs/AUDIT.md)
- [Changelog](https://github.com/mcpedrogm-art/fia-core/blob/main/CHANGELOG.md)
- [Publicación](https://github.com/mcpedrogm-art/fia-core/blob/main/docs/PUBLISHING.md)

## Licencia

MIT
