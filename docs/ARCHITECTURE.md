# FIA Core architecture

## Core data model

```text
PROJECT.md  ─────────────┐
SPEC.md (optional)       ├─> VERIFY ──> PASS / FAIL
TASK.md ──> TEST record ─┘
             └─ .fia/tests/TEST-NNN.{json,stdout.txt,stderr.txt}
STATUS is a read-only summary of TASK and VERIFY.
```

Optional capability packs ship inside the installed package, so `fia module
enable <name>` works the same from the source repo and from a real install
(`pip install fia-core`):

```text
fia-core
└── fia_core/
    ├── cli.py, model.py, store.py, verify.py, modules.py   required verification loop
    ├── assets.py, ui.py                                    opt-in pack tooling (never part of the gate)
    └── modules/                                             optional packs (packaged, see pyproject package-data)
        ├── security/       light security checklist
        ├── evidence/       human-readable evidence index beyond TEST records
        ├── provenance/     CI-origin and artifact trust metadata
        ├── policy/         optional project-specific rules
        ├── scope/          optional Git/change-scope checks
        ├── ui/             complete visual identity, recipes, divergence, assets workflow
        ├── rag/            retrieval and vector-search planning checklist
        ├── seo/            discoverability / answer-engine requirements
        ├── mcp/            tool/server selection and safety checklist
        ├── multiagent/     roles, handoffs and shared context
        ├── assets/         verified asset manifests and downloads
        ├── prd/            optional brief parsing and field suggestions
        └── governance/     advanced receipts, seals, approvals and reproduction
```

`fia module list|enable|disable|info <name>` records a project preference in
`.fia/modules.json` and copies the pack's docs into `docs/fia/<name>/`. That
state is descriptive only: enabling a module never silently changes the Core
gate — `verify()` only reads PROJECT.md, TASK.md, SPEC.md and `.fia/tests/`. A
module may add its own explicit command or check in a later version, but it
must do so opt-in, never by being merely enabled.

The `ui` and `assets` packs are the first to use that allowance: `fia ui setup`
and `fia assets fetch` download SHA-256-verified packs only when a human runs
them, `fia ui status` works offline, and none of it adds checks to `verify()`.

On the first interactive `fia init`, the same selection is offered as a numbered
menu. In scripts and CI, use `fia init --modules ui,security`; omitting the option
means Core only.

The model intentionally has one active `TASK.md`, not a phase graph. A task has
four machine-visible sections: Objective, Scope, Done when and Test command. The
task status may be `pending`, `in_progress`, `blocked` or `done`.

## Enforcement

`fia verify` checks:

1. PROJECT and TASK exist and are not unresolved templates.
2. TASK has valid status and meaningful required sections.
3. Every stored TEST record has its output files and matching SHA-256 hashes.
4. A `done` task has at least one successful, untampered TEST recorded against
   the exact current hash of TASK.md **and whose executed command matches,
   argument for argument, the `Test command` section declared in TASK.md**.
   This closes the gap where a task could be marked `done` on the back of an
   unrelated, trivially-passing command instead of the test the task actually
   promises.

`fia test` acquires a lock over `.fia/tests/` for the duration of the run, so
two concurrent `fia test` invocations (e.g. two agents on the same project)
cannot compute the same `TEST-NNN` id and overwrite each other's record.
`fia test --timeout <seconds>` kills a hung command and still records a
`timed_out` TEST (which can never satisfy the done-gate), instead of blocking
forever with no trace.

This gives the core an actual merge/build gate without requiring approvals,
receipts or a second state database.

## Deliberate boundaries

The core does not infer product domains, select Lite/Full modes, parse arbitrary
PRDs, inspect git scope, seal documents, reproduce old commands or download assets.
Those are either policy decisions or domain modules. The current module packs give
the agent a simple starting point without forcing every project to carry their
complexity. A future module must expose a small adapter and must not add mandatory
files or gates to this core by default.
