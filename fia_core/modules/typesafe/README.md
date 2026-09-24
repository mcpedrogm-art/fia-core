# TypeSafe / Jev module

Makes FIA Core able to **understand and evaluate** work that uses
[TypeSafe](https://docs.typesafe.ai) (the **Jev** / System One model), and to
**run** its typed questions.

Jev is not a chat or code-completion model. It takes a `state` and a map of
typed `questions` (`choice`, `score`, `noul`) and returns structured answers your
code can branch on. That is why it fits the FIA philosophy: code owns the
workflow, the model supplies a small, checkable judgment.

This pack adds three things:

1. **Reference** — [`JEV_REFERENCE.md`](JEV_REFERENCE.md) distills the official
   documentation so any agent working under FIA knows how to build with Jev.
2. **Evaluation** — `fia typesafe review` checks a machine-readable
   [spec](JEV_SPEC.md) and the project source against the design rules
   (atomic questions, well-defined criteria, planned confidence, safe keys). With
   `--live` it also asks Jev itself to evaluate the integration (dogfooding).
3. **Execution** — `fia typesafe eval` runs the spec's questions against the
   spec's state and prints the typed answers.

## Commands

```bash
fia module enable typesafe          # copies this pack to docs/fia/typesafe/
fia typesafe review                 # static evaluation of spec + sources
fia typesafe review --live          # + Jev meta-evaluation (needs TYPESAFE_API_KEY)
fia typesafe review --json          # machine-readable report
fia typesafe eval --spec JEV.json   # run the questions, print answers
fia typesafe eval --spec JEV.json --state ticket.json --json
```

The network commands read `TYPESAFE_API_KEY` from the environment. They are
opt-in and never run automatically.

## Scope

Enabling this module **never changes what `fia verify` checks**. `typesafe.py` is
opt-in tooling like `ui.py` and `assets.py`; it has no dependency (stdlib only)
and the Core gate still reads only `PROJECT.md`, `TASK.md`, `SPEC.md` and
`.fia/tests/`.

## Spec

Write a [JEV spec](JEV_SPEC.md) (`.fia/typesafe.json`, `JEV.json`, or
`typesafe.json`) describing the integration: a `state`, the `questions`, and
optional `thresholds`. `fia typesafe review` validates it; `fia typesafe eval`
runs it.

Full reference: <https://docs.typesafe.ai>.
