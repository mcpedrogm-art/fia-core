"""Verified asset packs: manifest plus SHA-256-checked downloads.

`fia assets fetch` downloads a pack described by a manifest (`UI_ASSETS.json`)
and verifies SHA-256 before writing anything. Opt-in, stdlib-only, idempotent
and fail-closed. `fia assets manifest` generates the manifest for publishers.
"""

import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

MANIFEST_VERSION = 1
DEFAULT_MANIFEST = "UI_ASSETS.json"
DOWNLOAD_TIMEOUT = 60
_CHUNK = 64 * 1024


class AssetError(Exception):
    """A manifest or download failed; nothing is written on failure."""


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_target(project_dir, raw_path):
    """Destination inside the project; absolute paths and traversal rejected."""
    if not raw_path or Path(raw_path).is_absolute():
        raise AssetError(f"Ruta de asset inválida (absoluta o vacía): {raw_path!r}")
    target = (project_dir / raw_path).resolve()
    root = project_dir.resolve()
    if target != root and root not in target.parents:
        raise AssetError(f"Ruta de asset fuera del proyecto: {raw_path!r}")
    return target


def load_manifest(ref):
    """Load a manifest from URL (http/https), file:// or a local path."""
    if ref.startswith(("http://", "https://", "file://")):
        try:
            with urllib.request.urlopen(ref, timeout=DOWNLOAD_TIMEOUT) as response:
                data = response.read()
        except (urllib.error.URLError, OSError) as error:
            raise AssetError(f"No se pudo leer el manifiesto {ref}: {error}") from error
    else:
        path = Path(ref)
        if not path.exists():
            raise AssetError(f"No existe el manifiesto: {path}")
        data = path.read_bytes()
    try:
        manifest = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AssetError(f"Manifiesto inválido (JSON): {error}") from error
    if manifest.get("version") != MANIFEST_VERSION:
        raise AssetError(f"Versión de manifiesto no soportada: {manifest.get('version')!r} "
                         f"(se espera {MANIFEST_VERSION})")
    assets = manifest.get("assets")
    if not isinstance(assets, list) or not assets:
        raise AssetError("El manifiesto no contiene 'assets'.")
    return manifest


def fetch_manifest(project_dir, ref, only_prefix=None):
    """Download and verify the manifest's assets (idempotent, fail-closed).

    `only_prefix` limits the download to entries whose `path` starts with that
    prefix (e.g. `library/` to install only the recipes).
    """
    project_dir = Path(project_dir)
    manifest = load_manifest(ref)
    entries = manifest["assets"]
    if only_prefix:
        entries = [entry for entry in entries
                   if str(entry.get("path", "")).startswith(only_prefix)]
        if not entries:
            raise AssetError(f"El manifiesto no contiene entradas con prefijo {only_prefix!r}: {ref}")
    downloaded = skipped = 0
    for entry in entries:
        path = entry.get("path")
        url = entry.get("url")
        expected = str(entry.get("sha256") or "").lower()
        if not path or not url or len(expected) != 64:
            raise AssetError(f"Entrada de asset inválida (path/url/sha256): {entry!r}")
        target = _safe_target(project_dir, path)
        if target.exists() and sha256_file(target) == expected:
            print(f"   [.] Ya existe y coincide: {path}")
            skipped += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + ".part")
        print(f"   [>] {path}")
        try:
            with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT) as response, \
                    open(temp, "wb") as handle:
                while True:
                    chunk = response.read(_CHUNK)
                    if not chunk:
                        break
                    handle.write(chunk)
        except (urllib.error.URLError, OSError) as error:
            if temp.exists():
                temp.unlink()
            raise AssetError(f"Fallo al descargar {url}: {error}") from error
        actual = sha256_file(temp)
        if actual != expected:
            temp.unlink()
            raise AssetError(f"SHA-256 no coincide para {path}\n"
                             f"   esperado: {expected}\n   obtenido: {actual}")
        os.replace(temp, target)
        downloaded += 1
    print(f"Assets: {downloaded} descargado(s) - {skipped} ya en su sitio - "
          f"{len(entries)} en el manifiesto")
    return 0


def check_manifest(project_dir, manifest):
    """Local state of a manifest without network: total/ok/missing/modified."""
    project_dir = Path(project_dir)
    missing, modified, ok = [], [], 0
    for entry in manifest.get("assets", []):
        target = _safe_target(project_dir, str(entry.get("path", "")))
        if not target.exists():
            missing.append(entry.get("path"))
        elif sha256_file(target) == str(entry.get("sha256") or "").lower():
            ok += 1
        else:
            modified.append(entry.get("path"))
    return {"total": len(manifest.get("assets", [])), "ok": ok,
            "missing": missing, "modified": modified}


def build_manifest(source_dir, base_url, out_path):
    """Generate `UI_ASSETS.json` from a local directory (for pack publishers)."""
    source_dir = Path(source_dir)
    if not source_dir.is_dir():
        raise AssetError(f"No es un directorio: {source_dir}")
    base = base_url.rstrip("/")
    entries = []
    for file in sorted(source_dir.rglob("*")):
        if not file.is_file():
            continue
        relative = file.relative_to(source_dir).as_posix()
        entries.append({"path": relative,
                        "url": f"{base}/{urllib.parse.quote(relative)}",
                        "sha256": sha256_file(file)})
    if not entries:
        raise AssetError(f"Sin archivos en {source_dir}")
    manifest = {"version": MANIFEST_VERSION, "assets": entries}
    Path(out_path).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
    print(f"Manifiesto generado: {out_path} ({len(entries)} assets)")
    return 0
