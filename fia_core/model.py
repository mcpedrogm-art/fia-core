"""Small, deliberately boring models for PROJECT, TASK and optional SPEC."""

import hashlib
import re
import shlex
from pathlib import Path

STATUS_VALUES = ("pending", "in_progress", "blocked", "done")
TEST_ID_RE = re.compile(r"^TEST-\d{3,}$")
PLACEHOLDER_RE = re.compile(r"<[^>]+>|^\s*<|\bTODO\b", re.IGNORECASE | re.MULTILINE)


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return Path(path).read_text(encoding="utf-8") if Path(path).exists() else ""


def section(text, title):
    """Return the body below a Markdown H2, stopping at the next H2."""
    match = re.search(r"^##\s+" + re.escape(title) + r"\s*$", text,
                      re.IGNORECASE | re.MULTILINE)
    if not match:
        return ""
    body = text[match.end():]
    next_heading = re.search(r"^##\s+", body, re.MULTILINE)
    return body[:next_heading.start()] if next_heading else body


def meaningful(text):
    value = re.sub(r"<!--.*?-->", "", text or "", flags=re.DOTALL).strip()
    return bool(value) and not PLACEHOLDER_RE.search(value)


def parse_task(text):
    status_match = re.search(r"^Status:\s*([a-z_]+)\s*$", text or "",
                             re.IGNORECASE | re.MULTILINE)
    status = status_match.group(1).lower() if status_match else "pending"
    test_refs = re.findall(r"\bTEST-\d{3,}\b", text or "", re.IGNORECASE)
    return {
        "status": status,
        "objective": section(text, "Objective"),
        "scope": section(text, "Scope"),
        "done_when": section(text, "Done when"),
        "test_command": section(text, "Test command"),
        "test_refs": sorted({ref.upper() for ref in test_refs}),
    }


def expected_test_command(text):
    """The single command line declared in TASK.md's 'Test command' section.

    Only the first non-empty, non-comment line is used: TASK.md must declare
    exactly one command so it can be matched against a TEST record.
    """
    raw = section(text, "Test command")
    for line in raw.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return ""


def command_candidates(text):
    """Possible argv readings of the declared 'Test command' line.

    POSIX and Windows quoting disagree on backslashes and quotes, and TASK.md
    is hand-written, so a declared line is accepted if any standard reading
    matches the argv recorded by `fia test`.
    """
    line = expected_test_command(text)
    if not line:
        return []
    candidates = []
    for posix in (True, False):
        try:
            parts = shlex.split(line, posix=posix)
        except ValueError:
            continue
        if not posix:
            parts = [token[1:-1] if len(token) >= 2 and token[0] == token[-1]
                     and token[0] in "\"'" else token for token in parts]
        if parts and parts not in candidates:
            candidates.append(parts)
    return candidates


def task_errors(text):
    parsed = parse_task(text)
    errors = []
    if parsed["status"] not in STATUS_VALUES:
        errors.append("TASK.md tiene un Status inválido")
    for name, label in (("objective", "Objective"), ("scope", "Scope"),
                        ("done_when", "Done when"), ("test_command", "Test command")):
        if not meaningful(parsed[name]):
            errors.append(f"TASK.md necesita contenido verificable en {label}")
    return errors
