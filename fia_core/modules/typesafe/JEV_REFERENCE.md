# Jev reference (TypeSafe System One)

Distilled from the official documentation at <https://docs.typesafe.ai>. Read the
live docs for anything version-dependent. Jev is TypeSafe's flagship **System
One** model: it returns typed decisions and probabilities, not generated text.

## Mental model

- **Code owns the workflow.** Deterministic rules, calculations, lookups and side
  effects stay in code.
- **The model supplies narrow judgments.** Ask one small, well-scoped question at
  a time (a "gut-check a knowledgeable person could make in seconds").
- **Decompose broad judgments.** Instead of "rate this pitch", ask market size,
  feasibility and differentiation separately, then combine with weights in code.
- **Use probabilities.** `Choice`/`Score` return a full distribution plus a
  `confidence`; `Noul` returns a probability. Threshold them in code and route
  uncertain cases to a person.

## Endpoint

```http
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

```json
{
  "state": "Help! My payouts have been failing for 3 days.",
  "model": "jev-latest",
  "questions": {
    "department": {
      "type": "choice",
      "instructions": "Which team should handle this?",
      "criteria": {
        "billing": "Payments, invoicing, refunds",
        "technical": "Bugs, outages, integrations",
        "sales": "Pricing, upgrades, new accounts"
      }
    },
    "is_urgent": {
      "type": "noul",
      "instructions": "Does this convey urgency?"
    },
    "frustration": {
      "type": "score",
      "instructions": "How frustrated is the customer?",
      "criteria": ["Calm", "Frustrated", "Very angry"]
    }
  }
}
```

Response: one `answers` entry per question id (the ids are for your code and are
**not** sent to the model), plus `usage`. Errors: `401` bad key, `422` invalid
body, `429`/`529` retry with backoff.

## State

The content to evaluate: a `string`, an object, or an array. Use an object when
there are named parts so questions can point at them with backticked
dot-and-index paths, e.g. `` `ticket.messages[0].text` ``. Separate **content**
(state) from **questions** (the judgments). Text only; English is the strongest
language.

## The three primitives

| Type | Answers | Returns |
|---|---|---|
| `choice` | Which of these options? | `choice`, `probabilities`, `confidence` |
| `score` | Which level on a rubric? | `score`, `legend`, `probabilities`, `confidence` |
| `noul` | Is this statement true? | `noul` (0–1, no separate confidence) |

### Choice
- `criteria` is a map of option → description (or `null`). Max 255 options.
- Give the full list, not a shortlist, and add an `other`/`none` option when the
  list might not cover every input.
- When two options are confused, describe each with an object
  (`what` / `not_for` / `examples`).

### Score
- `criteria` is an ordered array of level descriptions, 2–10 levels.
- Levels must describe **situations**, not degrees; the model never sees a
  level's number or its neighbours, so "worse than the previous level" means
  nothing and pure numbers work badly.
- The `score` is a probability-weighted position and can land between levels.
  Read `probabilities` and `confidence` alongside it.
- To combine scores from scales of different lengths, divide each by
  `len(criteria) - 1` to normalize to 0–1, then weight.

### Noul
- `instructions` is a yes/no question or a statement to judge; optional
  `criteria` describes `true`/`false`.
- A value near 0.5 means yes and no are equally likely, **not** a medium amount
  of the thing you asked about. If you want degree, use a Score.
- Threshold the value in code; the right threshold depends on the cost of a
  wrong yes vs. a wrong no.

## Asking multiple questions

Ask every question your code might need — including speculative ones — in **one
request**. They are evaluated in parallel and independently, so adding questions
barely changes latency and only costs a few tokens. Code ignores the answers it
does not use. A second request is only justified when an earlier answer is needed
to fetch evidence or build the next request.

## Confidence

`confidence` (Choice/Score) summarizes how concentrated the distribution is: all
on one outcome ≈ 1.0, spread out ≈ low. A practical split:

- **High** → act automatically.
- **Medium** → confirm, flag for review, or gather more.
- **Low** → do not act; route to a person or fall back.

Thresholds scale with risk: reading a balance and approving a transfer should not
use the same cut-off.

## Models and limits

- `jev-latest` (currently `jev-1.13.0`), alias `jev-preview`. Pin a versioned id
  if you tune thresholds against it.
- 64k tokens per request (state + all questions); 32k for state + longest
  question. Rate limits are dynamic; SDKs retry with backoff.
- Jev is not fine-tuned per account; you shape it with your `state`,
  `instructions` and `criteria`.

## Patterns

- **Speculative fan-out** — many questions in one call; consume only the
  relevant answers.
- **Composite scoring** — independent Scores combined with code-owned weights.
- **Confidence-gated routing** — use confidence as a second axis to decide
  whether to act.
- **Intent routing** — classify then route to code, a specialist model, or a
  human.
- **Extraction cascades / re-ranking / citation checks** — see the cookbooks.

## Design checklist

- [ ] Each question asks exactly one narrow judgment.
- [ ] Questions do not depend on each other's answers in the same request.
- [ ] Choice options and Score levels are distinct and self-contained.
- [ ] Choice lists include a catch-all option when they may not cover every input.
- [ ] The `state` carries the context the questions need.
- [ ] Independent questions are batched in one request.
- [ ] Confidence / noul values are thresholded and uncertain cases escalate.
- [ ] The API key lives server-side in an environment variable, never in code.
