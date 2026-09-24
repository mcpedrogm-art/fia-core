# JEV spec: format and rules

A **spec** is one JSON file that describes a Jev integration in a form the
harness can evaluate and run. Put it at `.fia/typesafe.json` (also discovered:
`JEV.json`, `typesafe.json` in the project root).

## Format

```json
{
  "model": "jev-latest",
  "state": {
    "ticket": {
      "message": "Shoes arrived late and in the wrong size. Also two charges of $120.",
      "charges": [120, 120]
    },
    "policy": "Duplicate charges are eligible for a refund."
  },
  "thresholds": {
    "confidence_min": 0.5,
    "noul_no": 0.2,
    "noul_yes": 0.8
  },
  "questions": {
    "department": {
      "type": "choice",
      "instructions": "Which team should handle `ticket.message`?",
      "criteria": {
        "returns": "Exchanges, wrong or damaged items",
        "billing": "Charges, invoices, payment problems",
        "other": "Fits none of the above"
      }
    },
    "refund_requested": {
      "type": "noul",
      "instructions": "Does `ticket.message` request a refund?",
      "criteria": {
        "true": "Directly asks for money back",
        "false": "No refund or credit requested"
      }
    },
    "frustration": {
      "type": "score",
      "instructions": "How frustrated does the customer appear?",
      "criteria": [
        "Calm and matter-of-fact",
        "Frustrated but civil",
        "Very angry or threatening to leave"
      ]
    }
  }
}
```

- **`state`** (required to `eval`): string, object or array — exactly as the API
  expects. `eval --state FILE` overrides it (JSON file, or plain text).
- **`questions`** (required): the same map you would send to the API. Each entry
  has `type` (`choice`/`score`/`noul`), `instructions`, and the `criteria` its
  type requires.
- **`model`** (optional): defaults to `jev-latest`.
- **`thresholds`** (optional, not sent to the API): how your code plans to act on
  uncertainty. Used by the review; `confidence_min`, `noul_no`, `noul_yes` are
  numbers in 0–1.

The spec mirrors the API request, so it is also directly usable with the
[Python](https://docs.typesafe.ai/sdk/python) or
[JavaScript](https://docs.typesafe.ai/sdk/javascript) SDKs.

## Commands

```bash
fia typesafe review                    # static evaluation (no network)
fia typesafe review --live             # + Jev meta-evaluation of the design
fia typesafe review --json             # machine-readable report
fia typesafe review --spec other.json  # explicit spec
fia typesafe eval --spec .fia/typesafe.json
fia typesafe eval --spec JEV.json --state ticket.json --json
```

`review` exits `1` when it finds errors. `eval` and `review --live` need
`TYPESAFE_API_KEY` in the environment.

## What `review` checks

**Errors** (fail the command):

- `questions` missing/empty; a question is not an object.
- `type` is not `choice`, `score` or `noul`.
- `instructions` missing/empty.
- `choice` criteria missing, not a map, fewer than 2 or more than 255 options.
- `score` criteria missing, not an array, fewer than 2 or more than 10 levels.
- `noul` criteria present but without `true` and `false`.
- `thresholds` not an object, or a value outside 0–1.
- **Security:** an API key or Bearer token written literally in source.

**Warnings** (reported, do not fail):

- only one question (batch independent questions in one request).
- a `choice` with no catch-all option (`other`/`none`/`unknown`).
- a `score` level that is a number or too short (describe situations, not grades).
- very long instructions, or instructions that look multi-condition (split them).
- question id with spaces (ids are for code).
- `thresholds.noul_no` not below `thresholds.noul_yes`.
- a source file that reads `.choice`/`.score`/`.noul` but never mentions
  `confidence`.

**Info:** usage detected, absence of a spec, and the `--live` meta-evaluation
verdict.

## `--live`: Jev evaluating Jev

With a spec and an API key, `review --live` sends the integration's question
catalog as `state` and asks Jev six meta-questions about the design:
whether the questions are atomic and independent, whether options/levels are
distinct, whether the context is sufficient, whether uncertainty is planned, and
the primary use. The verdict becomes warnings. This is deliberate dogfooding: the
same calibration you build on is used to evaluate the design itself.
