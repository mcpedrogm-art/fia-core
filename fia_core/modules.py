"""Optional module registry. Modules never become Core gates by accident."""

import json
import shutil
from pathlib import Path

STATE_PATH = Path(".fia") / "modules.json"
# Packaged inside fia_core/ (see pyproject.toml package-data) so `fia module
# enable <name>` also works from a real install, not only from the source repo.
MODULE_ROOT = Path(__file__).resolve().parent / "modules"

MODULES = {
    "security": {"label": "Security", "level": "light", "purpose": "Security checklist and focused checks."},
    "evidence": {"label": "Evidence", "level": "light", "purpose": "Human-readable evidence index beyond TEST records."},
    "provenance": {"label": "Provenance", "level": "advanced", "purpose": "CI-origin and artifact trust metadata."},
    "policy": {"label": "Policy", "level": "light", "purpose": "Optional project-specific rules."},
    "scope": {"label": "Scope", "level": "light", "purpose": "Optional Git/change-scope checks."},
    "ui": {"label": "UI/UX", "level": "full", "purpose": "Complete visual identity, recipes, divergence and assets workflow."},
    "rag": {"label": "RAG", "level": "light", "purpose": "Retrieval and vector-search planning checklist."},
    "seo": {"label": "SEO/AEO/GEO", "level": "light", "purpose": "Discoverability and answer-engine requirements."},
    "mcp": {"label": "MCP", "level": "light", "purpose": "Tool/server selection and safety checklist."},
    "multiagent": {"label": "Multi-agent", "level": "light", "purpose": "Roles, handoffs and shared context."},
    "assets": {"label": "Assets", "level": "light", "purpose": "Verified asset manifests and downloads."},
    "prd": {"label": "PRD heuristics", "level": "light", "purpose": "Optional brief parsing and field suggestions."},
    "governance": {"label": "Governance", "level": "advanced", "purpose": "Receipts, seals, approvals and reproduction."},
    "typesafe": {"label": "TypeSafe/Jev", "level": "full", "purpose": "Understand and evaluate Jev integrations: spec review, meta-evaluation and typed questions."},
}


def state_path(root):
    return Path(root) / STATE_PATH


def enabled(root):
    path = state_path(root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return [name for name in data.get("enabled", []) if name in MODULES]


def _save(root, names):
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema": 1, "enabled": sorted(names)},
                               ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def set_enabled(root, name, active=True):
    if name not in MODULES:
        raise ValueError(f"Módulo desconocido: {name}")
    names = set(enabled(root))
    if active:
        names.add(name)
    else:
        names.discard(name)
    _save(root, names)
    return sorted(names)


def normalize_names(raw):
    """Normalize a comma-separated module list and reject unknown names."""
    if raw is None:
        return []
    names = [item.strip().lower() for item in raw.split(",") if item.strip()]
    unknown = [name for name in names if name not in MODULES]
    if unknown:
        raise ValueError("Módulos desconocidos: " + ", ".join(unknown))
    return list(dict.fromkeys(names))


def activate(root, names):
    """Enable and install selected packs, preserving existing project files."""
    active = enabled(root)
    created = {}
    for name in names:
        active = set_enabled(root, name, active=True)
        created[name] = install_pack(root, name)
    return active, created


def install_pack(root, name):
    """Copy an optional pack into the project without overwriting user files."""
    source = MODULE_ROOT / name
    if not source.exists():
        return []
    destination = Path(root) / "docs" / "fia" / name
    created = []
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(path, target)
            created.append(str(target.relative_to(Path(root))))
    return created


def rows(root):
    active = set(enabled(root))
    return [{"name": name, **details, "enabled": name in active}
            for name, details in MODULES.items()]
