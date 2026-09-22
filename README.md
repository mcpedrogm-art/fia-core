# FIA Core

**Minimal, local verification for agent work.**

`PROJECT → (SPEC) → TASK → TEST → VERIFY → STATUS`

FIA Core does not try to be a documentation system or a project manager. It
makes a small set of work conditions mechanically checkable: a task marked
`done` must have a passing test, run with the exact command the task declares,
against the exact current contents of the task file.

**[Español](README.es.md)** · [Architecture](docs/ARCHITECTURE.md) · [Changelog](CHANGELOG.md)

## Install

```bash
pip install fia-core-full
```

The PyPI distribution is `fia-core-full`; it installs the `fia` command and the
`fia_core` Python package. Python 3.8+ · no dependencies.

From source instead:

```bash
git clone https://github.com/mcpedrogm-art/fia-core
cd fia-core
pip install .
```

## Start a project

```bash
cd my-project
fia init
```

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

## Optional modules

Thirteen capability packs, off by default. Enabling one copies its docs to
`docs/fia/<name>/` and never changes what `fia verify` checks. The UI/UX pack is
intentionally complete (Design DNA, four divergent directions, section recipes,
motion, accessibility, assets workflow); `ui` and `assets` also expose explicit
SHA-256-verified download commands.

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [Audit of the extraction](docs/AUDIT.md)
- [Changelog](CHANGELOG.md)
- [Publishing](docs/PUBLISHING.md)

## License

MIT
