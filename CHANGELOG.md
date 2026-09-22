# Changelog

## 0.2.0

Restored the UI/UX asset tooling that 0.1.x left as documentation only. The
PROJECT/TASK/TEST/VERIFY model and its gates are unchanged.

- **Feature:** `fia assets fetch [url|manifiesto]` downloads a pack described by
  `UI_ASSETS.json` with SHA-256 verification (atomic `.part` files, idempotent,
  fail-closed, path traversal rejected) and `fia assets manifest` generates a
  manifest from a local directory for publishers. Ported from FIA Harness
  `core/assets.py`.
- **Feature:** `fia ui setup [--recetas] [--url URL]` installs the official
  UI/UX pack (or only the `library/` recipes), saves the used manifest in the
  project for offline `fia ui status`, and honors `FIA_UI_PACK_URL`. Ported from
  FIA Harness `core/ui.py`. Nothing is downloaded unless the command is run.
- **Feature:** `fia init --assets <url|manifiesto>` creates the project files
  and then fetches the asset pack.
- **Docs truth fix:** the `assets` module README claimed SHA-256 checking with
  no mechanism behind it; the commands above now provide it.
- Docs: `UI_UX_EXCLUSIVA.md` §8 references the real commands again; the UI pack
  ships `UI_ASSETS.md` (manifest format, usage, publishing, security).
- Tests: 16 new tests (manifest building, traversal, bad hash, idempotency,
  `ui setup/status`, CLI and `init --assets`).

## 0.1.2

- **Fix (reproducibility):** the test suite no longer depends on stdin not
  being a TTY. `init()` auto-prompts on a terminal, so `python -m unittest`
  run from an interactive console raised `EOFError` (or blocked). Tests now
  call `init(..., interactive=False)` and `fia init` falls back to Core-only
  when stdin closes unexpectedly.
- **Fix (reliability):** the `.fia/tests/` lock now refreshes its mtime while
  a test runs. Previously a test longer than the 120s stale window could be
  mistaken for a crashed holder, letting a second `fia test` steal the lock
  and reuse a TEST id.
- **Fix (Windows):** a `Test command` declared with Windows paths or quotes
  is now matched against the recorded argv with both POSIX and Windows
  quoting rules (`model.command_candidates`) instead of POSIX-only
  `shlex.split`.
- Docs: fixed the stale `modules/README.md` link in `README.md` (the packs
  now live in `fia_core/modules/`).

## 0.1.1

Security/effectiveness audit fixes. No change to the PROJECT/TASK/TEST/VERIFY
model or the CLI surface (`init`, `test`, `verify`, `status`, `module`).

- **Fix (gate bypass, critical):** `fia verify` now requires that a `done`
  task's passing TEST record was executed with the exact command declared in
  TASK.md's `## Test command` section (argv match, not just exit code and task
  hash). Previously any passing command — including a no-op — satisfied the
  done-gate, defeating the purpose of the harness. Added
  `model.expected_test_command()` and regression tests
  (`test_done_task_with_mismatched_command_fails`,
  `test_done_task_without_test_command_section_fails`).
- **Fix (packaging, breaks a documented feature):** `modules/` moved from the
  repo root into `fia_core/modules/` and declared as `package-data` in
  `pyproject.toml`. Previously `fia module enable <name>` silently did nothing
  once the package was installed outside the source repo (`MODULE_ROOT` pointed
  at a directory that only existed in the Git checkout). Verified by installing
  into a clean virtualenv and confirming `modules/` ships with the wheel.
- **Fix (reliability):** `fia test` now takes `--timeout <seconds>`. A hung
  test command is killed instead of blocking forever, and a timed-out run is
  recorded (`timed_out: true`, `exit_code: null`) so it can never satisfy the
  done-gate.
- **Fix (concurrency):** `fia test` now takes a lock on `.fia/tests/` for the
  duration of the run, so two overlapping `fia test` invocations (e.g. two
  agents on the same project) can no longer compute the same `TEST-NNN` id and
  overwrite each other's record. The lock self-recovers from a crashed holder
  after 120s.
- **Housekeeping:** removed the stale `build/lib` duplicate and the empty
  `templates/` directory from the repo (both were already gitignored for
  future builds).
- Docs (`README.md`, `docs/ARCHITECTURE.md`) updated to match the above and to
  list all 13 available modules with the enable/disable workflow.

## 0.1.0

Initial extraction from FIA Harness. See `docs/AUDIT.md`.
