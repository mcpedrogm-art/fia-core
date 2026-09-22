# FIA Harness audit and extraction decision

Audit source: the original FIA Harness repository (local checkout, inspected
read-only at file, CLI, module, template, governance, documentation and
test-suite level). The original suite was executed before extraction:

```text
Ran 311 tests in 20.079s
OK
```

The original repository was not edited. FIA Core is a separate Git repository.

## Findings before classification

The original implementation has a solid enforcement kernel: state parsing and
validation, dependency checks, required task/checkpoint checks, command execution,
hash-checked output, a verification report and a status report. It also contains a
large protocol/product layer: process phases M0–M3, execution phases F0–Fn, legacy
schema migration, Lite/Full routing, risk policy, scope checks, receipts, seals,
approvals, reproduction, UI and asset installers, RAG/SEO/MCP templates, project
scaffolding and compatibility facades.

The proposed PROJECT/SPEC/TASK/TEST/VERIFY/STATUS model is therefore valid, with
one adjustment based on the code: TEST records remain in Core because they are the
smallest reliable proof that a completed TASK was actually checked. EVIDENCE and
PROVENANCE remain optional modules; Core does not use those names or require CI
digests.

## Component classification

### Python package and CLI

| Original component | Decision | Reason |
|---|---|---|
| `fia_harness/core/state.py` | SIMPLIFY | Keep task/status validation; remove phase graph, legacy schema, migration and compiled progress state. |
| `fia_harness/core/verify.py` | KEEP / SIMPLIFY | Preserve a fail-closed report; reduce it to project, task, test integrity and done-gate checks. |
| `fia_harness/core/runner.py` | KEEP / SIMPLIFY | Becomes `fia test`: one command, one immutable-by-hash test record. |
| `fia_harness/core/reports.py` | KEEP / SIMPLIFY | Becomes read-only `fia status`. |
| `fia_harness/core/fingerprints.py` | KEEP / SIMPLIFY | Keep SHA-256 for task binding and test output integrity. |
| `fia_harness/core/console.py` | SIMPLIFY | Core uses ordinary UTF-8 console behavior; Windows-specific recovery is not a gate. |
| `fia_harness/core/commands.py` | SIMPLIFY | CLI glue is reduced to four commands and no mutation-heavy orchestration. |
| `fia_harness/core/evidence.py` | MODULE | The useful hash store is retained as TEST records; CI provenance, ingest and evidence taxonomy are optional. |
| `fia_harness/core/receipts.py` | GOVERNANCE | Phase receipts and Git tree manifests are valuable for regulated/audited work, not every project. |
| `fia_harness/core/seals.py` | GOVERNANCE | Document sealing is an advanced policy, not a project prerequisite. |
| `fia_harness/core/approvals.py` | GOVERNANCE | Human approval records are optional governance. |
| `fia_harness/core/reproduce.py` | GOVERNANCE | Re-running historical commands needs an explicit trust and allowlist policy. |
| `fia_harness/core/quality.py` | MODULE | Advisory completeness, risk decisions and report heuristics are policy modules. |
| `fia_harness/core/policy.py` | MODULE | Domain/risk keyword inference is optional and can be wrong by design. |
| `fia_harness/core/scope.py` | MODULE | Git diff scope enforcement is useful but not universal core behavior. |
| `fia_harness/core/router.py` | MODULE | Lite/Full routing adds policy and complexity; not required for verification. |
| `fia_harness/core/assets.py` | MODULE | Asset manifests and downloads belong to UI/content delivery. |
| `fia_harness/core/ui.py` | MODULE | UI pack setup is explicitly domain-specific. |
| `fia_harness/parser/markdown.py` | SIMPLIFY | Retain only small section/field parsing needed for TASK. |
| `fia_harness/parser/prd.py` | MODULE | Heuristic PRD discovery, synonyms and confidence levels are optional. |
| `fia_harness/parser/discovery.py` | DELETE | Core has explicit PROJECT.md and TASK.md paths; broad discovery adds ambiguity. |
| `fia_harness/generators/bootstrap.py` | SIMPLIFY | Keep the tiny idempotent initializer as `fia init`; remove phase bootstrapping and module activation. |
| `fia_harness/generators/scaffold.py` | DELETE | CONTEXT, PROGRESS, GitHub workflow and multi-document scaffolding are not Core. |
| `fia_harness/generators/task.py` | DELETE | Phase task generation and conditional content injection are outside the one-task core. |
| `fia_harness/adapters/git.py` | MODULE | Git is needed by receipts/scope but not by local Core verification. |
| `fia_harness/legacy.py` | DELETE | Compatibility with pre-v3 script APIs is specifically out of scope. |
| `fia_harness/facades.py` | DELETE | Root script facades are compatibility packaging, not product value. |
| `fia_harness/cli.py` | SIMPLIFY | Replace 17 subcommands with `init`, `test`, `verify`, `status`. |
| `fia_harness/__init__.py` | KEEP / SIMPLIFY | Retain package identity and version only. |

### Templates

| Original template | Decision | Reason |
|---|---|---|
| `INICIO_PROYECTO.md` | SIMPLIFY | Replace with short Core quick start and explicit files. |
| `PRD_TEMPLATE.md` | DELETE | Core uses PROJECT; rich PRD authoring is not verification. |
| `TASK_TEMPLATE.md` | SIMPLIFY | Reduce to Objective, Scope, Done when and Test command. |
| `TASK_LITE_TEMPLATE.md` | DELETE | No Lite/Full mode in Core. |
| `QUICKSTART_LITE.md` | DELETE | Compatibility with an old mode is unnecessary. |
| `SECURITY.md` | MODULE | Valuable when a project needs security-specific policy. |
| `AEO_GEO_SEO.md` | MODULE | Content/discoverability concern, not core enforcement. |
| `UI_UX_EXCLUSIVA.md` | MODULE | UI process is project-specific. |
| `UI_RECIPES.md` / `UI_ASSETS.json` | MODULE | UI assets and recipes are optional. |
| `RAG_VECTOR_EXTENSION.md` | MODULE | Retrieval architecture is optional. |
| `SKILLS_MCP.md` | MODULE | Tool/connectivity guidance is not required to verify work. |
| `AGENTS.md` | MODULE | Multi-agent coordination is optional. |
| `MODELOS.md` | DELETE | Model recommendations create no enforcement value. |

Core ships only PROJECT and TASK templates. SPEC is available as an opt-in file.

### Governance and repository artifacts

| Original area | Decision | Reason |
|---|---|---|
| `governance/PROGRESS.md`, `progress.json` | GOVERNANCE | Phase state and compiled authority are replaced by one TASK and test binding. |
| `governance/DECISIONS.md` | GOVERNANCE | Useful audit trail, optional. |
| `governance/evidence/**` | GOVERNANCE / MODULE | Receipts, CI artifacts and historical evidence are advanced capabilities. |
| `governance/TASK-F*.md` | GOVERNANCE | Phase-specific task history is not a Core requirement. |
| `docs/RECEIPT_*.md`, `PLAN_RECIBO_ROUTER.md` | GOVERNANCE | Design material for a future governance package. |
| `docs/EVIDENCE_CAPTURE_DECISION.md` | MODULE | Useful rationale for an evidence adapter, not a Core contract. |
| `docs/UI_ASSETS.md` | MODULE | Operational documentation for the optional UI asset module. |
| `docs/V3_BASELINE.md`, `ROADMAP_V3_1.md` | DELETE from Core | FIA version history and roadmap are not runtime behavior. |
| `CHANGELOG_FIXES.md` | DELETE from Core | Historical compatibility fixes do not belong in a new implementation. |
| root `bootstrap.py`, `task_generator.py` | DELETE | No generated compatibility facades. |
| `.github` workflows/templates | SIMPLIFY | Core can expose `fia verify`; CI integration is a short consumer config, not generated governance. |

| `README.md`, `README.es.md` | DELETE from Core | Replaced by a short Core README with no Harness protocol promises. |
| `pyproject.toml` | SIMPLIFY | Keep packaging metadata and one `fia` entry point; remove legacy aliases and package-data duplication. |
| `LICENSE` | KEEP | The MIT license remains appropriate for the independent implementation. |
| `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` | SIMPLIFY / OPTIONAL | Repository collaboration policy is not a runtime requirement. |
| `.gitattributes`, `.gitignore` | KEEP / SIMPLIFY | Keep only source-control behavior needed by the small repository. |
| `fia_harness/data/templates/**` | DELETE | Remove the second template source; Core has one minimal source. |
| `fia_harness/data/parser/synonyms.json` | MODULE | Used only by optional heuristic PRD extraction. |
| `fia_harness.egg-info`, `__pycache__` | DELETE | Generated artifacts, never product components. |

### Tests

| Original test group | Decision | Reason |
|---|---|---|
| parser markdown / CLI / packaging | SIMPLIFY | Replace with focused Core behavior tests. |
| state, runner, verify, fingerprints | KEEP / SIMPLIFY | These cover the actual enforcement kernel. |
| evidence, receipts, seals, approvals, reproduction | MODULE / GOVERNANCE | Keep in their future packages, not in the Core gate. |
| policy, quality, scope, router, assets, UI | MODULE | Test only when those modules are installed. |
| large dogfood/end-to-end phase fixtures | DELETE from Core | They enforce FIA Harness protocol rather than Core behavior. |

## Resulting repository

This repository contains the independent first implementation. It has no import
path, schema, template or CLI compatibility with FIA Harness. That break is
intentional and documented rather than hidden.

The remodel adds `modules/` as optional capability packs. The packs are off by
default and selected per project with `fia module enable <name>`. UI is intentionally
the full workflow rather than a short checklist; the other packs start with compact
guidance and can earn additional automation independently. Core verification does
not change when a pack is enabled.
