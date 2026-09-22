import json
import os
import shlex
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fia_core.cli import init, main
from fia_core.store import run
from fia_core.verify import verify


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        init(self.root, interactive=False)

    def tearDown(self):
        self.tmp.cleanup()

    def test_init_is_minimal_and_non_destructive(self):
        self.assertTrue((self.root / "PROJECT.md").exists())
        self.assertTrue((self.root / "TASK.md").exists())
        self.assertFalse((self.root / "SPEC.md").exists())
        old = (self.root / "TASK.md").read_text(encoding="utf-8")
        init(self.root, interactive=False)
        self.assertEqual(old, (self.root / "TASK.md").read_text(encoding="utf-8"))

    def test_pending_template_is_not_verifiable(self):
        report = verify(self.root)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("PROJECT.md falta", " ".join(report["errors"]))

    def test_done_task_requires_current_passing_test(self):
        (self.root / "PROJECT.md").write_text("# PROJECT\n\nName: Demo\nPurpose: prove work\n", encoding="utf-8")
        cmd = [sys.executable, "-c", "print('ok')"]
        self._write_task("pending", test_command=shlex.join(cmd))
        record = run(self.root, cmd)
        self.assertEqual(record["exit_code"], 0)
        self._write_task("done", test_command=shlex.join(cmd))
        # TASK.md changed (status), so its hash no longer matches the TEST just recorded.
        self.assertEqual(verify(self.root)["status"], "FAIL")
        run(self.root, cmd)
        self.assertEqual(verify(self.root)["status"], "PASS")

    def test_done_task_with_mismatched_command_fails(self):
        """VERIFY must not accept a TEST for a different command than TASK.md declares."""
        (self.root / "PROJECT.md").write_text("# PROJECT\n\nName: Demo\nPurpose: prove work\n", encoding="utf-8")
        declared = [sys.executable, "-m", "unittest"]
        self._write_task("done", test_command=shlex.join(declared))
        # A trivial, unrelated command is recorded instead of the declared one.
        run(self.root, [sys.executable, "-c", "print('ok')"])
        report = verify(self.root)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("no tiene un TEST válido" in e for e in report["errors"]))

    def test_done_task_without_test_command_section_fails(self):
        (self.root / "PROJECT.md").write_text("# PROJECT\n\nName: Demo\nPurpose: prove work\n", encoding="utf-8")
        (self.root / "TASK.md").write_text(
            "# TASK\n\nStatus: done\n\n## Objective\n\nShip.\n\n"
            "## Scope\n\n- app\n\n## Done when\n\n- it works\n\n"
            "## Test command\n\n<pending>\n", encoding="utf-8")
        report = verify(self.root)
        self.assertEqual(report["status"], "FAIL")

    def test_test_command_with_windows_path_is_understood(self):
        """A declared command with Windows paths must match the recorded argv."""
        from fia_core.model import command_candidates
        text = "## Test command\n\nC:\\Python\\python.exe -m unittest\n"
        self.assertIn(["C:\\Python\\python.exe", "-m", "unittest"],
                      command_candidates(text))

    def test_concurrent_test_runs_do_not_collide(self):
        """Two overlapping `fia test` calls must not reuse the same TEST id."""
        import threading
        (self.root / "PROJECT.md").write_text("# PROJECT\n\nName: Demo\nPurpose: prove work\n", encoding="utf-8")
        self._write_task("pending")
        results = []

        def worker():
            results.append(run(self.root, [sys.executable, "-c", "print('ok')"]))

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        ids = [r["id"] for r in results]
        self.assertEqual(len(ids), len(set(ids)), f"IDs de TEST duplicados: {ids}")

    def test_timeout_kills_long_running_command_and_never_counts_as_passing(self):
        (self.root / "PROJECT.md").write_text("# PROJECT\n\nName: Demo\nPurpose: prove work\n", encoding="utf-8")
        cmd = [sys.executable, "-c", "import time; time.sleep(5)"]
        self._write_task("done", test_command=shlex.join(cmd))
        record = run(self.root, cmd, timeout=0.2)
        self.assertTrue(record["timed_out"])
        self.assertIsNone(record["exit_code"])
        self.assertEqual(verify(self.root)["status"], "FAIL")

    def test_test_output_tampering_fails(self):
        (self.root / "PROJECT.md").write_text("# PROJECT\n\nName: Demo\nPurpose: prove work\n", encoding="utf-8")
        self._write_task("pending")
        record = run(self.root, [os.environ.get("PYTHON", "python"), "-c", "print('ok')"])
        path = self.root / ".fia" / "tests" / record["stdout_file"]
        path.write_text("forged\n", encoding="utf-8")
        report = verify(self.root)
        self.assertTrue(any("no coincide con su hash" in error for error in report["errors"]))

    def test_optional_spec_does_not_add_approval_gate(self):
        (self.root / "PROJECT.md").write_text("# PROJECT\n\nName: Demo\nPurpose: prove work\n", encoding="utf-8")
        (self.root / "SPEC.md").write_text("# SPEC\n\nA useful constraint.\n", encoding="utf-8")
        self._write_task("pending")
        self.assertEqual(verify(self.root)["status"], "PASS")

    def test_cli_test_records_a_command(self):
        (self.root / "PROJECT.md").write_text("# PROJECT\n\nName: Demo\nPurpose: prove work\n", encoding="utf-8")
        self._write_task("pending")
        code = main(["test", "-d", str(self.root), "--", sys.executable, "-c", "print('ok')"])
        self.assertEqual(code, 0)
        self.assertEqual(len(list((self.root / ".fia" / "tests").glob("TEST-*.json"))), 1)

    def test_optional_module_activation_does_not_change_core_gate(self):
        self.assertEqual(main(["module", "enable", "ui", "-d", str(self.root)]), 0)
        state = json.loads((self.root / ".fia" / "modules.json").read_text(encoding="utf-8"))
        self.assertEqual(state["enabled"], ["ui"])
        self.assertTrue((self.root / "docs" / "fia" / "ui" / "UI_UX_EXCLUSIVA.md").exists())
        self.assertEqual(verify(self.root)["status"], "FAIL")
        self.assertEqual(main(["module", "disable", "ui", "-d", str(self.root)]), 0)

    def test_init_accepts_modules_in_one_command(self):
        other = Path(self.tmp.name) / "with-modules"
        self.assertEqual(main(["init", "-d", str(other), "--modules", "ui,security"]), 0)
        state = json.loads((other / ".fia" / "modules.json").read_text(encoding="utf-8"))
        self.assertEqual(state["enabled"], ["security", "ui"])
        self.assertTrue((other / "docs" / "fia" / "ui" / "UI_RECIPES.md").exists())
        self.assertTrue((other / "docs" / "fia" / "security" / "README.md").exists())

    def test_interactive_init_lets_user_choose_by_number(self):
        other = Path(self.tmp.name) / "interactive"
        with patch.object(sys.stdin, "isatty", return_value=True), patch("builtins.input", return_value="6"):
            self.assertEqual(main(["init", "-d", str(other)]), 0)
        state = json.loads((other / ".fia" / "modules.json").read_text(encoding="utf-8"))
        self.assertEqual(state["enabled"], ["ui"])

    def _write_task(self, status, test_command="python -m unittest"):
        (self.root / "TASK.md").write_text(
            f"# TASK\n\nStatus: {status}\n\n## Objective\n\nShip one thing.\n\n"
            "## Scope\n\n- app\n\n## Done when\n\n- it works\n\n"
            f"## Test command\n\n{test_command}\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
