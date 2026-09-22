"""Assisted UI/UX pack: `fia ui setup` and `fia ui status`.

`fia ui setup` downloads the official pack (or the one given with `--url` /
`FIA_UI_PACK_URL`) reusing the verified download from `assets` (SHA-256,
idempotent, atomic) and saves the used manifest in the project's
`UI_ASSETS.json` so `fia ui status` works offline.

The protocol (`UI_UX_EXCLUSIVA.md` §8, Step 0) requires human confirmation
before installing: nothing is downloaded automatically.
"""

import json
import os
from pathlib import Path

from . import assets

# Official pack maintained by PGMIA (self-hosted Supabase). Override: --url or env.
UI_PACK_URL = "https://supabase.pgmia.es/storage/v1/object/public/fia-assets/UI_ASSETS.json"
RECIPES_PREFIX = "library/"
MANIFEST_NAME = "UI_ASSETS.json"


def pack_url(override=None):
    """Precedence: --url > FIA_UI_PACK_URL > official pack."""
    return override or os.environ.get("FIA_UI_PACK_URL") or UI_PACK_URL


def cmd_ui_setup(project_dir, recipes_only=False, url=None):
    """Install the UI/UX environment (or recipes only) with verification."""
    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    ref = pack_url(url)
    manifest = assets.load_manifest(ref)
    entries = manifest["assets"]
    if recipes_only:
        entries = [entry for entry in entries
                   if str(entry.get("path", "")).startswith(RECIPES_PREFIX)]
        if not entries:
            raise assets.AssetError(f"El manifiesto no contiene recetas ({RECIPES_PREFIX}*): {ref}")
    manifest = dict(manifest, assets=entries)
    manifest_path = project_dir / MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    mode = "solo recetas" if recipes_only else "entorno completo"
    print(f"-> Entorno UI/UX ({mode}): {len(entries)} asset(s) desde {ref}")
    print(f"   Manifiesto guardado en {MANIFEST_NAME} (permite `fia ui status` sin red)")
    return assets.fetch_manifest(project_dir, str(manifest_path))


def cmd_ui_status(project_dir):
    """Local UI/UX environment state (no network)."""
    project_dir = Path(project_dir)
    manifest_path = project_dir / MANIFEST_NAME
    if not manifest_path.exists():
        print("UI/UX avanzado: ausente (no hay UI_ASSETS.json en el proyecto)")
        return 0
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise assets.AssetError(f"{MANIFEST_NAME} no es JSON válido: {error}") from error
    if not manifest.get("assets"):
        print("UI/UX avanzado: ausente (UI_ASSETS.json vacío; usa `fia ui setup`)")
        return 0
    state = assets.check_manifest(project_dir, manifest)
    if state["ok"] == state["total"]:
        print(f"UI/UX avanzado: completo ({state['ok']}/{state['total']} assets verificados)")
        return 0
    print(f"UI/UX avanzado: parcial ({state['ok']}/{state['total']} ok - "
          f"{len(state['missing'])} ausentes - {len(state['modified'])} modificados)")
    for path in state["missing"][:5]:
        print(f"   falta: {path}")
    for path in state["modified"][:5]:
        print(f"   modificado: {path}")
    print("   Repara con: fia ui setup")
    return 0
