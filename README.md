# FIA Core

[![CI](https://github.com/mcpedrogm-art/fia-core/actions/workflows/ci.yml/badge.svg)](https://github.com/mcpedrogm-art/fia-core/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/fia-core-full)](https://pypi.org/project/fia-core-full/)
[![Python versions](https://img.shields.io/pypi/pyversions/fia-core-full)](https://pypi.org/project/fia-core-full/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/mcpedrogm-art/fia-core/blob/main/LICENSE)

**Minimal, local verification for agent work.**

`PROJECT → (SPEC) → TASK → TEST → VERIFY → STATUS`

FIA Core does not try to be a documentation system or a project manager. It
makes a small set of work conditions mechanically checkable: a task marked
`done` must have a passing test, run with the exact command the task declares,
against the exact current contents of the task file.

**[Español](https://github.com/mcpedrogm-art/fia-core/blob/main/README.es.md)** ·
[Architecture](https://github.com/mcpedrogm-art/fia-core/blob/main/docs/ARCHITECTURE.md) ·
[Changelog](https://github.com/mcpedrogm-art/fia-core/blob/main/CHANGELOG.md)

## Install (per project, nothing global)

FIA Core has no dependencies and installs inside the project's own virtual
environment. Nothing is added to your global Python, to PATH, or to other
projects.

Windows:

```bash
cd my-project
python -m venv .venv
.venv\Scripts\pip install fia-core-full
```

macOS / Linux:

```bash
cd my-project
python -m venv .venv
.venv/bin/pip install fia-core-full
```

Add `.venv/` to the project's `.gitignore`. To uninstall, delete `.venv/`; the
project files stay.

<details>
<summary>From source instead</summary>

```bash
git clone https://github.com/mcpedrogm-art/fia-core
cd my-project
python -m venv .venv
.venv\Scripts\pip install ../fia-core     # macOS / Linux: .venv/bin/pip install ../fia-core
```
</details>

## Start a project

```bash
cd my-project
fia init
```

With a per-project environment, run `.venv\Scripts\fia` (Windows) or
`.venv/bin/fia` (macOS/Linux) instead of `fia`, or activate the environment
first; the examples below use `fia` for brevity. `fia test` runs its command
with the `python` on PATH, so if you do not activate the environment, declare
the test command with the environment's interpreter (for example
`.venv\Scripts\python -m unittest`).

This creates `PROJECT.md`, `TASK.md` and `.fia/`. Existing files are never
overwritten. `fia init` asks which optional modules you want (press Enter for
Core only).

In scripts:

```bash
fia init --modules ui,security
fia module list          # all 13 packs
fia module enable rag    # add one later
```

## The workflow

### 1. Describe the project

Fill in `PROJECT.md`: name and purpose. Optionally create `SPEC.md` with
`fia init --with-spec`; if it exists, it must contain real content.

### 2. Write the task

`TASK.md` has one status and four required sections:

```markdown
Status: done

## Objective

Add the login form.

## Scope

- src/login.py
- tests/test_login.py

## Done when

- `python -m unittest` passes

## Test command

python -m unittest
```

`Test command` must contain exactly one command line.

### 3. Run the test

```bash
fia test -- python -m unittest
```

`fia test` runs the command and stores a TEST record in `.fia/tests/` with
SHA-256 hashes of the output and of the current `TASK.md`.

### 4. Verify

```bash
fia verify
```

`PASS` requires real project and task content, intact TEST records, and — for a
`done` task — a passing TEST whose command matches the declared `Test command`
and whose `TASK.md` hash is still current.

### 5. Check status

```bash
fia status
```

> **One rule to remember:** if you edit `TASK.md` after `fia test`, run
> `fia test` again. The done-gate is bound to the current contents of `TASK.md`.

## Commands

| Command | Purpose |
|---|---|
| `fia init [-d DIR] [--modules LIST] [--assets URL]` | Create the project files |
| `fia test [-d DIR] [--timeout SECONDS] -- COMMAND` | Run and record a test |
| `fia verify [-d DIR]` | Check the gate (PASS/FAIL) |
| `fia status [-d DIR]` | Task and verification summary |
| `fia module list\|enable\|disable\|info NAME` | Optional capability packs |
| `fia ui setup\|status` | UI/UX pack (opt-in download, SHA-256 verified) |
| `fia assets fetch\|manifest` | Verified asset packs |

## Core and optional modules

The enforcement core is about 600 lines of dependency-free Python plus 30
tests; it is the only thing `fia verify` runs.

Thirteen capability packs ship alongside it, off by default. Enabling one copies
its docs to `docs/fia/<name>/` and never changes what `fia verify` checks. The
UI/UX pack is intentionally complete (Design DNA, four divergent directions,
section recipes, motion, accessibility, assets workflow). `ui` and `assets` are
the only packs with code (~200 lines): explicit, opt-in, SHA-256-verified
download commands.

## Trust and provenance

- The package has no dependencies: installing it never pulls or upgrades other
  packages, and it is meant to live in each project's own `.venv`, so it cannot
  interfere with your global Python or with other projects.
- The PyPI distribution is `fia-core-full` (the bare `fia-core` name is not
  available on PyPI); it installs the `fia` command and the `fia_core` package.
- Releases are published from this repository with PyPI trusted publishing
  (OIDC): only `.github/workflows/publish.yml` in `mcpedrogm-art/fia-core` can
  upload to <https://pypi.org/project/fia-core-full/>. No API token is stored.
- Every release is built by GitHub Actions from a tagged commit, and CI runs the
  full test suite on Python 3.9, 3.11 and 3.13.

## Docs

- [Architecture](https://github.com/mcpedrogm-art/fia-core/blob/main/docs/ARCHITECTURE.md)
- [Audit of the extraction](https://github.com/mcpedrogm-art/fia-core/blob/main/docs/AUDIT.md)
- [Changelog](https://github.com/mcpedrogm-art/fia-core/blob/main/CHANGELOG.md)
- [Publishing](https://github.com/mcpedrogm-art/fia-core/blob/main/docs/PUBLISHING.md)

## License

MIT
