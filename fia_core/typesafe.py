"""TypeSafe/Jev pack: understand and evaluate a Jev integration.

`fia typesafe review` checks a machine-readable Jev specification (a JSON file
with `state`, `questions` and optional `thresholds`) against the design rules
from the TypeSafe documentation: atomic questions, well-defined criteria,
planned confidence handling, and safe API-key handling. It also scans the
project for common integration mistakes. `fia typesafe eval` sends the
specification to the System One endpoint and prints the typed answers.

Like `fia ui` and `fia assets`, this pack is opt-in and stdlib-only, and it never
changes what `fia verify` checks. The network commands (`eval` and
`review --live`) read `TYPESAFE_API_KEY` from the environment.

Spec format and the full rule list: `modules/typesafe/` (installed to
`docs/fia/typesafe/`). Reference: https://docs.typesafe.ai
"""

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
ENV_KEY = "TYPESAFE_API_KEY"
DEFAULT_MODEL = "jev-latest"
TIMEOUT = 60
RETRYABLE_STATUS = (429, 529)
MAX_RETRIES = 2
RETRY_AFTER_CAP = 20

SPEC_NAMES = (".fia/typesafe.json", "JEV.json", "typesafe.json")
QUESTION_TYPES = ("choice", "score", "noul")
SCORE_MIN_LEVELS = 2
SCORE_MAX_LEVELS = 10
CHOICE_MAX_OPTIONS = 255
SCORE_MIN_DESCRIPTION = 8

SOURCE_SUFFIXES = (".py", ".js", ".ts", ".tsx", ".jsx", ".json")
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "build", "dist",
             "__pycache__", ".fia", ".mypy_cache", ".pytest_cache"}
USAGE_MARKERS = ("system_one", "typesafe_sdk", "@typesafe-ai/sdk",
                 "TYPESAFE_API_KEY", "api.typesafe.ai", "jev-latest")

CATCH_ALL_RE = re.compile(r"\b(other|others|none|unknown|misc|ninguna?|otro|otra|desconocid[oa])\b",
                          re.IGNORECASE)
NUMERIC_LEVEL_RE = re.compile(r"^\s*-?\d+(\.\d+)?\s*$")
MULTI_CONDITION_RE = re.compile(r"\band\b.*\band\b|\by\b.*\by\b", re.IGNORECASE)
HARDCODED_KEY_RE = re.compile(
    r"(?:TYPESAFE_API_KEY|api[_-]?key)\s*[:=]\s*[\"']([^\"']{12,})[\"']", re.IGNORECASE)
BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9_\-.]{20,}")
PLACEHOLDER_RE = re.compile(
    r"(\$|process\.env|os\.environ|getenv|<|>|your|tu_|xxx|\.\.\.|placeholder)", re.IGNORECASE)


class TypeSafeError(Exception):
    """A specification, request, or API failure; nothing is sent on failure."""


def _finding(severity, code, message, question=None):
    item = {"severity": severity, "code": code, "message": message}
    if question is not None:
        item["question"] = question
    return item


def _nonempty(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (dict, list)):
        return len(value) > 0
    return True


def api_key():
    return os.environ.get(ENV_KEY, "").strip()


def discover_spec(root):
    """First matching spec in `.fia/typesafe.json`, `JEV.json`, `typesafe.json`."""
    root = Path(root)
    for name in SPEC_NAMES:
        candidate = root / name
        if candidate.exists():
            return candidate
    return None


def load_spec(path):
    """Load a Jev specification and require a single JSON object at the top."""
    path = Path(path)
    if not path.exists():
        raise TypeSafeError(f"No existe el spec: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TypeSafeError(f"El spec no es JSON válido: {error}") from error
    if not isinstance(data, dict):
        raise TypeSafeError("El spec debe ser un objeto JSON con 'state' y 'questions'.")
    return data


def validate_spec(spec):
    """Static evaluation of a Jev specification. Returns a list of findings."""
    findings = []
    if not isinstance(spec, dict):
        return [_finding("error", "spec.type", "El spec debe ser un objeto JSON.")]

    if not _nonempty(spec.get("state")):
        findings.append(_finding(
            "warn", "spec.state",
            "El spec no define 'state'; añádelo aquí o pásalo con `eval --state`."))

    questions = spec.get("questions")
    if not isinstance(questions, dict) or not questions:
        findings.append(_finding("error", "questions.missing",
                                 "El spec necesita un mapa 'questions' no vacío."))
        return findings

    for qid, question in questions.items():
        _validate_question(qid, question, findings)

    if len(questions) == 1:
        findings.append(_finding(
            "warn", "questions.batch",
            "Solo hay una pregunta; las preguntas independientes se evalúan en "
            "paralelo y cuestan poco, así que agrúpalas en una sola llamada."))

    _validate_thresholds(spec.get("thresholds"), findings)
    return findings


def _validate_question(qid, question, findings):
    if not isinstance(qid, str) or not qid.strip() or qid != qid.strip() or " " in qid:
        findings.append(_finding("warn", "questions.id",
                                 f"El id {qid!r} no es un identificador estable; usa snake_case sin espacios."))
    if not isinstance(question, dict):
        findings.append(_finding("error", "question.type",
                                 f"La pregunta {qid!r} debe ser un objeto.", question=qid))
        return
    qtype = question.get("type")
    if qtype not in QUESTION_TYPES:
        findings.append(_finding(
            "error", "question.type",
            f"La pregunta {qid!r} tiene type={qtype!r}; usa choice, score o noul.", question=qid))

    instructions = question.get("instructions")
    if not _nonempty(instructions):
        findings.append(_finding("error", "question.instructions",
                                 f"La pregunta {qid!r} no tiene 'instructions'.", question=qid))
    elif isinstance(instructions, str):
        if len(instructions) > 400:
            findings.append(_finding(
                "warn", "question.instructions.long",
                f"Las instrucciones de {qid!r} son largas; considera estructurarlas "
                "(question + datos) o dividirlas.", question=qid))
        if len(instructions) > 100 and MULTI_CONDITION_RE.search(instructions):
            findings.append(_finding(
                "warn", "question.atomic",
                f"{qid!r} parece combinar varias condiciones; divide en preguntas atómicas "
                "y compón en código.", question=qid))

    if qtype == "choice":
        _validate_choice(qid, question.get("criteria"), findings)
    elif qtype == "score":
        _validate_score(qid, question.get("criteria"), findings)
    elif qtype == "noul":
        _validate_noul(qid, question.get("criteria"), findings)


def _validate_choice(qid, criteria, findings):
    if not isinstance(criteria, dict) or not criteria:
        findings.append(_finding("error", "choice.criteria",
                                 f"La Choice {qid!r} necesita 'criteria' como mapa de opciones.",
                                 question=qid))
        return
    if len(criteria) < 2:
        findings.append(_finding("error", "choice.criteria.min",
                                 f"La Choice {qid!r} necesita al menos dos opciones.", question=qid))
    if len(criteria) > CHOICE_MAX_OPTIONS:
        findings.append(_finding("error", "choice.criteria.max",
                                 f"La Choice {qid!r} supera el máximo de {CHOICE_MAX_OPTIONS} opciones.",
                                 question=qid))
    if not any(CATCH_ALL_RE.search(str(option)) for option in criteria):
        findings.append(_finding(
            "warn", "choice.catch_all",
            f"La Choice {qid!r} no incluye una opción de cierre (other/none/unknown); "
            "añádela si la lista puede no cubrir todas las entradas.", question=qid))


def _validate_score(qid, criteria, findings):
    if not isinstance(criteria, list) or not criteria:
        findings.append(_finding("error", "score.criteria",
                                 f"La Score {qid!r} necesita 'criteria' como lista ordenada de niveles.",
                                 question=qid))
        return
    if len(criteria) < SCORE_MIN_LEVELS:
        findings.append(_finding("error", "score.criteria.min",
                                 f"La Score {qid!r} necesita al menos {SCORE_MIN_LEVELS} niveles.",
                                 question=qid))
    if len(criteria) > SCORE_MAX_LEVELS:
        findings.append(_finding("error", "score.criteria.max",
                                 f"La Score {qid!r} supera el máximo de {SCORE_MAX_LEVELS} niveles.",
                                 question=qid))
    for level in criteria:
        if isinstance(level, str):
            text = level.strip()
            if NUMERIC_LEVEL_RE.match(text) or len(text) < SCORE_MIN_DESCRIPTION:
                findings.append(_finding(
                    "warn", "score.level.descriptive",
                    f"La Score {qid!r} tiene el nivel {level!r}; describe situaciones "
                    "concretas, no grados ni números.", question=qid))
                break
        elif isinstance(level, (int, float)) and not isinstance(level, bool):
            findings.append(_finding(
                "warn", "score.level.descriptive",
                f"La Score {qid!r} usa el número {level!r} como nivel; usa descripciones.",
                question=qid))
            break


def _validate_noul(qid, criteria, findings):
    if criteria is None:
        return
    if not isinstance(criteria, dict) or "true" not in criteria or "false" not in criteria:
        findings.append(_finding(
            "error", "noul.criteria",
            f"El 'criteria' de la Noul {qid!r} debe describir 'true' y 'false'.",
            question=qid))


def _validate_thresholds(thresholds, findings):
    if thresholds is None:
        return
    if not isinstance(thresholds, dict):
        findings.append(_finding("error", "thresholds.type",
                                 "'thresholds' debe ser un objeto JSON."))
        return
    for key, value in thresholds.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
            findings.append(_finding("error", "thresholds.range",
                                     f"thresholds.{key}={value!r} debe ser un número entre 0 y 1."))
    no = thresholds.get("noul_no")
    yes = thresholds.get("noul_yes")
    if isinstance(no, (int, float)) and isinstance(yes, (int, float)) and no >= yes:
        findings.append(_finding(
            "warn", "thresholds.order",
            f"thresholds.noul_no ({no}) debería ser menor que thresholds.noul_yes ({yes})."))


def scan_sources(root):
    """Best-effort scan of project files for TypeSafe usage and key leaks."""
    root = Path(root)
    findings = []
    used = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts[:-1]):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if not any(marker in text for marker in USAGE_MARKERS):
            continue
        relative = path.relative_to(root).as_posix()
        used.append(relative)
        _scan_key_leaks(relative, text, findings)
        _scan_confidence(relative, text, findings)
    return used, findings


def _scan_key_leaks(relative, text, findings):
    for match in HARDCODED_KEY_RE.finditer(text):
        value = match.group(1)
        if PLACEHOLDER_RE.search(value):
            continue
        findings.append(_finding(
            "error", "security.hardcoded_key",
            f"{relative} parece incluir una API key literal; usa la variable de "
            "entorno TYPESAFE_API_KEY."))
        break
    if BEARER_RE.search(text) and not PLACEHOLDER_RE.search(BEARER_RE.search(text).group(0)):
        findings.append(_finding(
            "error", "security.hardcoded_bearer",
            f"{relative} incluye un token Bearer literal; no lo escribas en el código."))


def _scan_confidence(relative, text, findings):
    reads_answer = any(token in text for token in (".choice", ".score", ".noul"))
    if reads_answer and "confidence" not in text:
        findings.append(_finding(
            "info", "confidence.unused",
            f"{relative} lee respuestas pero no menciona 'confidence'; valora "
            "condicionar las acciones según la incertidumbre."))


def _build_meta_questions():
    """Questions that make Jev evaluate a Jev integration (dogfooding)."""
    return {
        "questions_are_atomic": {
            "type": "noul",
            "instructions": "Does each question in `catalog.questions` ask exactly one narrow, well-scoped judgment, instead of combining several independent factors into one?",
        },
        "questions_are_independent": {
            "type": "noul",
            "instructions": "Can every question in `catalog.questions` be answered from the state alone, without needing another question's answer in the same request?",
        },
        "options_are_distinct": {
            "type": "score",
            "instructions": "How well-defined and mutually distinct are the Choice options and Score levels in `catalog.questions`?",
            "criteria": [
                "Options or levels overlap, are ambiguous, or are only numbers",
                "Mostly distinct, but some options blur together",
                "Clearly distinct and self-contained descriptions",
            ],
        },
        "context_is_sufficient": {
            "type": "score",
            "instructions": "Do the instructions and criteria give the model enough context to answer reliably?",
            "criteria": [
                "The questions lack the context or the state they refer to",
                "Some context is present but incomplete",
                "The state and questions give the model everything it needs",
            ],
        },
        "confidence_is_planned": {
            "type": "noul",
            "instructions": "Does `catalog.thresholds` define how to act on uncertain answers (confidence or noul cut-offs) instead of acting on every answer unconditionally?",
        },
        "primary_use": {
            "type": "choice",
            "instructions": "What is the primary use of this integration?",
            "criteria": {
                "routing": "Send a request to a destination",
                "classification": "Assign one of a fixed set of labels",
                "scoring": "Rank or grade on a rubric",
                "extraction": "Select or recover a value from the state",
                "guardrail": "Screen, verify, or moderate",
                "other": "None of the above",
            },
        },
    }


def _meta_verdict(answers):
    """Turn the meta answers into a short heuristic verdict."""
    notes = []
    atomic = answers.get("questions_are_atomic", {}).get("noul")
    if isinstance(atomic, (int, float)) and atomic < 0.5:
        notes.append("las preguntas no parecen atómicas: descompón juicios compuestos")
    independent = answers.get("questions_are_independent", {}).get("noul")
    if isinstance(independent, (int, float)) and independent < 0.5:
        notes.append("algunas preguntas parecen depender de otras: usa una segunda llamada solo si de verdad lo requiere")
    distinct = answers.get("options_are_distinct", {}).get("score")
    if isinstance(distinct, (int, float)) and distinct < 1.0:
        notes.append("las opciones o niveles se solapan: sepáralos con descripciones contrastivas")
    context = answers.get("context_is_sufficient", {}).get("score")
    if isinstance(context, (int, float)) and context < 1.0:
        notes.append("falta contexto: enriquece el state o las instructions")
    planned = answers.get("confidence_is_planned", {}).get("noul")
    if isinstance(planned, (int, float)) and planned < 0.5:
        notes.append("no hay umbrales de confianza: define cómo actuar con respuestas inciertas")
    return notes


def post_systemone(payload, key, endpoint=ENDPOINT, timeout=TIMEOUT, retries=MAX_RETRIES):
    """POST to the System One endpoint; retries 429/529 with backoff."""
    body = json.dumps(payload).encode("utf-8")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    attempt = 0
    while True:
        request = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code in RETRYABLE_STATUS and attempt < retries:
                attempt += 1
                time.sleep(_retry_delay(error))
                continue
            detail = error.read().decode("utf-8", "replace")[:500]
            raise TypeSafeError(f"La API respondió {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise TypeSafeError(f"No se pudo contactar la API: {error.reason}") from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise TypeSafeError(f"La respuesta no es JSON válido: {error}") from error


def _retry_delay(error):
    try:
        return min(float(error.headers.get("retry-after", 1)), RETRY_AFTER_CAP)
    except (TypeError, ValueError):
        return 1.0


def _print_findings(findings):
    order = {"error": 0, "warn": 1, "info": 2}
    label = {"error": "ERROR", "warn": "WARN ", "info": "INFO "}
    for finding in sorted(findings, key=lambda item: order.get(item["severity"], 3)):
        prefix = f"[{label[finding['severity']]}]"
        suffix = f" ({finding['question']})" if finding.get("question") else ""
        print(f"{prefix} {finding['message']}{suffix}")


def _summary(findings):
    errors = sum(1 for f in findings if f["severity"] == "error")
    warns = sum(1 for f in findings if f["severity"] == "warn")
    return errors, warns


def cmd_typesafe_review(root, spec_path=None, live=False, as_json=False):
    """Evaluate the Jev integration: static rules, plus optional live meta review."""
    root = Path(root)
    findings = []
    spec = None
    spec_ref = Path(spec_path) if spec_path else discover_spec(root)

    if spec_ref is not None:
        spec = load_spec(spec_ref)
        findings.extend(validate_spec(spec))
    else:
        findings.append(_finding(
            "info", "spec.absent",
            "No hay spec (.fia/typesafe.json). Créalo para una evaluación completa."))

    used, source_findings = scan_sources(root)
    findings.extend(source_findings)
    if used:
        findings.append(_finding("info", "sources.found",
                                 "Uso de TypeSafe detectado en: " + ", ".join(used)))
    elif spec is None:
        findings.append(_finding("info", "sources.none",
                                 "No se detectó uso de TypeSafe en el proyecto."))

    meta = None
    if live:
        if spec is None:
            raise TypeSafeError("`review --live` necesita un spec para evaluar el diseño.")
        key = api_key()
        if not key:
            raise TypeSafeError(f"Falta {ENV_KEY} en el entorno para `review --live`.")
        catalog = {"questions": spec.get("questions"),
                   "thresholds": spec.get("thresholds")}
        payload = {"state": {"catalog": catalog},
                   "model": spec.get("model", DEFAULT_MODEL),
                   "questions": _build_meta_questions()}
        response = post_systemone(payload, key)
        meta = response.get("answers", {})
        for note in _meta_verdict(meta):
            findings.append(_finding("warn", "meta.weakness", note))

    errors, warns = _summary(findings)
    if as_json:
        print(json.dumps({"spec": str(spec_ref) if spec_ref else None,
                          "errors": errors, "warnings": warns,
                          "findings": findings, "meta": meta},
                         ensure_ascii=False, indent=2))
    else:
        if spec_ref is not None:
            print(f"TypeSafe review — spec: {spec_ref}")
        else:
            print("TypeSafe review — sin spec")
        _print_findings(findings)
        if meta is not None:
            print("\nEvaluación con Jev (meta):")
            _print_answers(meta)
        print(f"\n{errors} error(es), {warns} aviso(s).")
    return 1 if errors else 0


def cmd_typesafe_eval(spec_path, state_path=None, model=None, endpoint=None,
                      as_json=False):
    """Run the spec's questions against its state and print the typed answers."""
    spec = load_spec(spec_path)
    key = api_key()
    if not key:
        raise TypeSafeError(f"Falta {ENV_KEY} en el entorno para `eval`.")

    state = spec.get("state")
    if state_path:
        state = _read_state(Path(state_path))
    if not _nonempty(state):
        raise TypeSafeError("El spec no define 'state'; añádelo o usa `eval --state FILE`.")

    questions = spec.get("questions")
    if not isinstance(questions, dict) or not questions:
        raise TypeSafeError("El spec necesita un mapa 'questions' no vacío.")

    payload = {"state": state,
               "model": model or spec.get("model") or DEFAULT_MODEL,
               "questions": questions}
    response = post_systemone(payload, key, endpoint=endpoint or ENDPOINT)
    if as_json:
        print(json.dumps(response, ensure_ascii=False, indent=2))
    else:
        print(f"TypeSafe eval — model: {response.get('model', payload['model'])}")
        _print_answers(response.get("answers", {}))
        usage = response.get("usage") or {}
        if usage:
            print(f"\nTokens: entrada={usage.get('input_tokens')} salida={usage.get('output_tokens')}")
    return 0


def _read_state(path):
    if not path.exists():
        raise TypeSafeError(f"No existe el state: {path}")
    text = path.read_text(encoding="utf-8-sig")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _print_answers(answers):
    for qid, answer in answers.items():
        kind = answer.get("type")
        if kind == "choice":
            print(f"  {qid}: choice={answer.get('choice')} "
                  f"confidence={answer.get('confidence')} probabilities={answer.get('probabilities')}")
        elif kind == "score":
            print(f"  {qid}: score={answer.get('score')} "
                  f"confidence={answer.get('confidence')} probabilities={answer.get('probabilities')}")
        elif kind == "noul":
            print(f"  {qid}: noul={answer.get('noul')}")
        else:
            print(f"  {qid}: {answer}")
