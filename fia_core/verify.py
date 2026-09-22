"""The core merge gate: check only conditions that produce actionable confidence."""

from pathlib import Path

from . import store
from .model import command_candidates, file_sha256, meaningful, parse_task, read, task_errors


def verify(root):
    root = Path(root).resolve()
    errors = []
    checks = []
    project_path, task_path, spec_path = (root / name for name in ("PROJECT.md", "TASK.md", "SPEC.md"))
    project = read(project_path)
    task = read(task_path)
    checks.append(("PROJECT", "PASS" if meaningful(project) else "FAIL"))
    if not meaningful(project):
        errors.append("PROJECT.md falta o sigue siendo una plantilla")
    checks.append(("TASK", "PASS" if not task_errors(task) else "FAIL"))
    errors.extend(task_errors(task))
    parsed = parse_task(task)
    if spec_path.exists():
        checks.append(("SPEC", "PASS" if meaningful(read(spec_path)) else "FAIL"))
        if not meaningful(read(spec_path)):
            errors.append("SPEC.md existe pero está vacío o sin completar")
    else:
        checks.append(("SPEC", "SKIP"))

    all_records = store.records(root)
    record_errors = []
    for record in all_records:
        record_errors.extend(store.validate(root, record))
    checks.append(("TEST", "PASS" if not record_errors else "FAIL"))
    errors.extend(record_errors)

    if parsed["status"] == "done":
        current_hash = file_sha256(task_path) if task_path.exists() else None
        expected = command_candidates(task)
        passing = [r for r in all_records if not r.get("invalid")
                   and r.get("exit_code") == 0
                   and r.get("task_sha256") == current_hash
                   and r.get("command") in expected
                   and not store.validate(root, r)]
        if not expected:
            errors.append("TASK.md no declara un 'Test command' ejecutable")
        elif not passing:
            errors.append("TASK está done pero no tiene un TEST válido, exitoso y coincidente "
                           "con el 'Test command' declarado, para el contenido actual de TASK.md")
    checks.append(("VERIFY", "PASS" if not errors else "FAIL"))
    return {"status": "PASS" if not errors else "FAIL", "checks": checks,
            "errors": errors, "task": parsed, "tests": all_records}


def status(root):
    root = Path(root).resolve()
    task = parse_task(read(root / "TASK.md"))
    report = verify(root)
    return {"status": task["status"], "verification": report["status"],
            "tests": len(report["tests"]), "spec": (root / "SPEC.md").exists()}
