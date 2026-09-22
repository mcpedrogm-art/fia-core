import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from fia_core import assets, cli, ui


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data, encoding="utf-8")


class AssetsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.project = self.root / "proyecto"
        self.project.mkdir()
        self.source = self.root / "pack"
        _write(self.source / "media" / "hero.bin", b"hero-bytes")
        _write(self.source / "media" / "fondo ñ.png", b"fondo-bytes")

    def _manifest(self, base_url=None):
        base = base_url or self.source.as_uri()
        out = self.root / "UI_ASSETS.json"
        with contextlib.redirect_stdout(io.StringIO()):
            assets.build_manifest(self.source, base, out)
        return json.loads(out.read_text(encoding="utf-8")), out

    def test_build_manifest_hashes_and_urls(self):
        manifest, _ = self._manifest(base_url="https://cdn.example.com/pack")
        entries = {e["path"]: e for e in manifest["assets"]}
        self.assertIn("media/hero.bin", entries)
        self.assertTrue(entries["media/hero.bin"]["url"]
                        .startswith("https://cdn.example.com/pack/media/hero.bin"))
        self.assertEqual(len(entries["media/hero.bin"]["sha256"]), 64)
        self.assertIn("media/fondo%20%C3%B1.png", entries["media/fondo ñ.png"]["url"])

    def test_fetch_file_url_verifies_and_is_idempotent(self):
        _, path = self._manifest()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = assets.fetch_manifest(self.project, str(path))
        self.assertEqual(code, 0)
        self.assertEqual((self.project / "media" / "hero.bin").read_bytes(), b"hero-bytes")
        with contextlib.redirect_stdout(out):
            code = assets.fetch_manifest(self.project, str(path))
        self.assertEqual(code, 0)
        self.assertIn("ya en su sitio", out.getvalue())

    def test_fetch_bad_hash_fails_without_leftovers(self):
        manifest, path = self._manifest()
        manifest["assets"][0]["sha256"] = "0" * 64
        path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(assets.AssetError):
            with contextlib.redirect_stdout(io.StringIO()):
                assets.fetch_manifest(self.project, str(path))
        self.assertFalse((self.project / "media" / "hero.bin").exists())
        self.assertFalse(list(self.project.rglob("*.part")))

    def test_fetch_path_traversal_fails(self):
        manifest, path = self._manifest()
        manifest["assets"][0]["path"] = "../fuera.bin"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(assets.AssetError):
            assets.fetch_manifest(self.project, str(path))
        self.assertFalse((self.root / "fuera.bin").exists())

    def test_missing_manifest_fails(self):
        with self.assertRaises(assets.AssetError):
            assets.fetch_manifest(self.project, str(self.root / "no-existe.json"))

    def test_unsupported_manifest_version_fails(self):
        path = self.root / "UI_ASSETS.json"
        path.write_text(json.dumps({
            "version": 99,
            "assets": [{"path": "a", "url": "file:///a", "sha256": "0" * 64}],
        }), encoding="utf-8")
        with self.assertRaises(assets.AssetError):
            assets.fetch_manifest(self.project, str(path))

    def test_cli_assets_fetch(self):
        _, path = self._manifest()
        with contextlib.redirect_stdout(io.StringIO()):
            code = cli.main(["assets", "fetch", str(path), "-d", str(self.project)])
        self.assertEqual(code, 0)
        self.assertTrue((self.project / "media" / "hero.bin").exists())

    def test_init_with_assets(self):
        _, path = self._manifest()
        target = self.root / "nuevo"
        with contextlib.redirect_stdout(io.StringIO()):
            code = cli.main(["init", "-d", str(target), "--assets", str(path)])
        self.assertEqual(code, 0)
        self.assertTrue((target / "media" / "hero.bin").exists())


class UiTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.project = self.root / "proyecto"
        self.project.mkdir()
        self.source = self.root / "pack"
        _write(self.source / "media" / "hero.bin", b"hero-bytes")
        _write(self.source / "library" / "UI_LIBRARY.md", "# recetas\n")
        out = self.root / "manifest.json"
        with contextlib.redirect_stdout(io.StringIO()):
            assets.build_manifest(self.source, self.source.as_uri(), out)
        self.manifest = out

    def _setup(self, **kwargs):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ui.cmd_ui_setup(self.project, **kwargs)
        return code, out.getvalue()

    def test_setup_complete_and_manifest_saved(self):
        code, _ = self._setup(url=str(self.manifest))
        self.assertEqual(code, 0)
        self.assertTrue((self.project / "media" / "hero.bin").exists())
        self.assertTrue((self.project / "library" / "UI_LIBRARY.md").exists())
        saved = json.loads((self.project / "UI_ASSETS.json").read_text(encoding="utf-8"))
        self.assertEqual(len(saved["assets"]), 2)

    def test_setup_recipes_only(self):
        code, _ = self._setup(url=str(self.manifest), recipes_only=True)
        self.assertEqual(code, 0)
        self.assertTrue((self.project / "library" / "UI_LIBRARY.md").exists())
        self.assertFalse((self.project / "media" / "hero.bin").exists())

    def test_status_absent_without_manifest(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ui.cmd_ui_status(self.project)
        self.assertIn("ausente", out.getvalue())

    def test_status_complete_and_partial(self):
        self._setup(url=str(self.manifest))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ui.cmd_ui_status(self.project)
        self.assertIn("completo (2/2", out.getvalue())
        (self.project / "media" / "hero.bin").unlink()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ui.cmd_ui_status(self.project)
        self.assertIn("parcial (1/2", out.getvalue())
        self.assertIn("falta: media/hero.bin", out.getvalue())

    def test_status_modified(self):
        self._setup(url=str(self.manifest))
        _write(self.project / "media" / "hero.bin", b"tampered")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ui.cmd_ui_status(self.project)
        self.assertIn("modificado: media/hero.bin", out.getvalue())

    def test_env_override(self):
        old = os.environ.get("FIA_UI_PACK_URL")
        os.environ["FIA_UI_PACK_URL"] = "https://ejemplo.test/UI_ASSETS.json"
        self.addCleanup(lambda: os.environ.__setitem__("FIA_UI_PACK_URL", old)
                        if old is not None else os.environ.pop("FIA_UI_PACK_URL", None))
        self.assertEqual(ui.pack_url(), "https://ejemplo.test/UI_ASSETS.json")
        self.assertEqual(ui.pack_url("https://otro.test/x.json"), "https://otro.test/x.json")

    def test_official_url_by_default(self):
        self.assertTrue(ui.UI_PACK_URL.startswith("https://supabase.pgmia.es/"))
        self.assertTrue(ui.UI_PACK_URL.endswith("UI_ASSETS.json"))

    def test_cli_ui_setup_and_status(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["ui", "setup", "--url", str(self.manifest),
                             "-d", str(self.project)])
        self.assertEqual(code, 0)
        with contextlib.redirect_stdout(out):
            code = cli.main(["ui", "status", "-d", str(self.project)])
        self.assertEqual(code, 0)
        self.assertIn("completo", out.getvalue())


if __name__ == "__main__":
    unittest.main()
