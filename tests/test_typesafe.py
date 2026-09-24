import contextlib
import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from fia_core import cli, typesafe


def _clean_spec():
    return {
        "model": "jev-latest",
        "state": {"ticket": "My shoes arrived late and the size is wrong."},
        "thresholds": {"confidence_min": 0.5, "noul_no": 0.2, "noul_yes": 0.8},
        "questions": {
            "topic": {
                "type": "choice",
                "instructions": "Which team should handle `ticket`?",
                "criteria": {
                    "returns": "Exchanges, wrong or damaged items",
                    "billing": "Charges, invoices, payment problems",
                    "other": "Fits none of the above",
                },
            },
            "frustration": {
                "type": "score",
                "instructions": "How frustrated does the customer appear?",
                "criteria": [
                    "Calm and matter-of-fact",
                    "Frustrated but civil",
                    "Very angry or threatening to leave",
                ],
            },
            "wants_refund": {
                "type": "noul",
                "instructions": "Does `ticket` ask for a refund?",
            },
        },
    }


def _codes(findings, severity=None):
    return [f["code"] for f in findings
            if severity is None or f["severity"] == severity]


class ValidateSpecTests(unittest.TestCase):
    def test_clean_spec_has_no_errors(self):
        findings = typesafe.validate_spec(_clean_spec())
        self.assertEqual(_codes(findings, "error"), [])

    def test_missing_questions_is_an_error(self):
        self.assertIn("questions.missing",
                      _codes(typesafe.validate_spec({"state": "x"}), "error"))

    def test_unknown_type_is_an_error(self):
        spec = _clean_spec()
        spec["questions"]["bad"] = {"type": "bool", "instructions": "?"}
        self.assertIn("question.type", _codes(typesafe.validate_spec(spec), "error"))

    def test_single_question_is_a_warning(self):
        spec = _clean_spec()
        spec["questions"] = {"only": spec["questions"]["wants_refund"]}
        self.assertIn("questions.batch", _codes(typesafe.validate_spec(spec), "warn"))

    def test_choice_needs_two_options(self):
        spec = _clean_spec()
        spec["questions"]["topic"]["criteria"] = {"only": "one"}
        self.assertIn("choice.criteria.min", _codes(typesafe.validate_spec(spec), "error"))

    def test_choice_over_max_options_is_an_error(self):
        spec = _clean_spec()
        spec["questions"]["topic"]["criteria"] = {f"opt{i}": "x" for i in range(256)}
        self.assertIn("choice.criteria.max", _codes(typesafe.validate_spec(spec), "error"))

    def test_choice_without_catch_all_warns(self):
        spec = _clean_spec()
        spec["questions"]["topic"]["criteria"] = {"a": "One", "b": "Two"}
        self.assertIn("choice.catch_all", _codes(typesafe.validate_spec(spec), "warn"))

    def test_score_needs_two_levels(self):
        spec = _clean_spec()
        spec["questions"]["frustration"]["criteria"] = ["Only one"]
        self.assertIn("score.criteria.min", _codes(typesafe.validate_spec(spec), "error"))

    def test_score_over_max_levels_is_an_error(self):
        spec = _clean_spec()
        spec["questions"]["frustration"]["criteria"] = [f"Level number {i}" for i in range(11)]
        self.assertIn("score.criteria.max", _codes(typesafe.validate_spec(spec), "error"))

    def test_numeric_score_levels_warn(self):
        spec = _clean_spec()
        spec["questions"]["frustration"]["criteria"] = ["0", "1", "2"]
        self.assertIn("score.level.descriptive",
                      _codes(typesafe.validate_spec(spec), "warn"))

    def test_noul_criteria_needs_true_and_false(self):
        spec = _clean_spec()
        spec["questions"]["wants_refund"]["criteria"] = {"yes": "..."}
        self.assertIn("noul.criteria", _codes(typesafe.validate_spec(spec), "error"))

    def test_thresholds_out_of_range_is_an_error(self):
        spec = _clean_spec()
        spec["thresholds"] = {"confidence_min": 1.5}
        self.assertIn("thresholds.range", _codes(typesafe.validate_spec(spec), "error"))

    def test_thresholds_order_warns(self):
        spec = _clean_spec()
        spec["thresholds"] = {"noul_no": 0.9, "noul_yes": 0.2}
        self.assertIn("thresholds.order", _codes(typesafe.validate_spec(spec), "warn"))

    def test_missing_state_warns(self):
        spec = _clean_spec()
        del spec["state"]
        self.assertIn("spec.state", _codes(typesafe.validate_spec(spec), "warn"))


class LoadSpecTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_invalid_json_raises(self):
        path = self.root / "typesafe.json"
        path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(typesafe.TypeSafeError):
            typesafe.load_spec(path)

    def test_non_object_raises(self):
        path = self.root / "typesafe.json"
        path.write_text("[1, 2]", encoding="utf-8")
        with self.assertRaises(typesafe.TypeSafeError):
            typesafe.load_spec(path)

    def test_discover_prefers_dot_fia(self):
        (self.root / ".fia").mkdir()
        (self.root / ".fia" / "typesafe.json").write_text("{}", encoding="utf-8")
        (self.root / "JEV.json").write_text("{}", encoding="utf-8")
        self.assertEqual(typesafe.discover_spec(self.root),
                         self.root / ".fia" / "typesafe.json")


class ScanSourcesTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_hardcoded_key_is_an_error(self):
        (self.root / "app.py").write_text(
            'TYPESAFE_API_KEY = "abcd1234efgh5678"\n', encoding="utf-8")
        _, findings = typesafe.scan_sources(self.root)
        self.assertIn("security.hardcoded_key", _codes(findings, "error"))

    def test_env_var_key_is_not_flagged(self):
        (self.root / "app.py").write_text(
            "import os\nkey = os.environ['TYPESAFE_API_KEY']\n", encoding="utf-8")
        findings = typesafe.scan_sources(self.root)[1]
        self.assertNotIn("security.hardcoded_key", _codes(findings, "error"))

    def test_confidence_unused_is_reported(self):
        (self.root / "app.py").write_text(
            "r = client.system_one(state='x', questions={})\n"
            "print(r.answers['a'].choice)\n", encoding="utf-8")
        findings = typesafe.scan_sources(self.root)[1]
        self.assertIn("confidence.unused", _codes(findings, "info"))


class ReviewCommandTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def _review(self, **kwargs):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = typesafe.cmd_typesafe_review(self.root, **kwargs)
        return code, out.getvalue()

    def test_clean_spec_passes(self):
        spec = self.root / "JEV.json"
        spec.write_text(json.dumps(_clean_spec()), encoding="utf-8")
        code, text = self._review(spec_path=str(spec))
        self.assertEqual(code, 0)
        self.assertIn("0 error(es)", text)

    def test_error_spec_fails(self):
        spec = self.root / "JEV.json"
        spec.write_text(json.dumps({"state": "x", "questions": {"a": {"type": "bool"}}}),
                        encoding="utf-8")
        code, _ = self._review(spec_path=str(spec))
        self.assertEqual(code, 1)

    def test_json_report_is_parseable(self):
        spec = self.root / "JEV.json"
        spec.write_text(json.dumps(_clean_spec()), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            typesafe.cmd_typesafe_review(self.root, spec_path=str(spec), as_json=True)
        report = json.loads(out.getvalue())
        self.assertEqual(report["errors"], 0)

    def test_live_without_spec_raises(self):
        with self.assertRaises(typesafe.TypeSafeError):
            with contextlib.redirect_stdout(io.StringIO()):
                typesafe.cmd_typesafe_review(self.root, live=True)


class EvalCommandTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.spec = self.root / "JEV.json"
        self.spec.write_text(json.dumps(_clean_spec()), encoding="utf-8")

    def test_eval_without_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(typesafe.TypeSafeError):
                typesafe.cmd_typesafe_eval(self.spec)

    def test_eval_posts_and_prints(self):
        fake = {"model": "jev-1.13.0",
                "answers": {"topic": {"type": "choice", "choice": "returns",
                                      "confidence": 1.0}},
                "usage": {"input_tokens": 10, "output_tokens": 2}}
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "k"}), \
                patch.object(typesafe, "post_systemone", return_value=fake) as post:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = typesafe.cmd_typesafe_eval(self.spec)
        self.assertEqual(code, 0)
        self.assertIn("returns", out.getvalue())
        self.assertEqual(post.call_args.args[0]["model"], "jev-latest")


class PostSystemoneTests(unittest.TestCase):
    def test_parses_response(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"answers": {}}'

        with patch.object(typesafe.urllib.request, "urlopen", return_value=FakeResponse()):
            data = typesafe.post_systemone({"state": "x", "questions": {}}, "key")
        self.assertEqual(data, {"answers": {}})

    def test_401_raises_typesafe_error(self):
        error = urllib.error.HTTPError("http://x", 401, "unauthorized", {},
                                       io.BytesIO(b"bad key"))
        with patch.object(typesafe.urllib.request, "urlopen", side_effect=error):
            with self.assertRaises(typesafe.TypeSafeError):
                typesafe.post_systemone({"state": "x", "questions": {}}, "key")


class MetaTests(unittest.TestCase):
    def test_meta_questions_cover_the_three_types(self):
        kinds = {q["type"] for q in typesafe._build_meta_questions().values()}
        self.assertEqual(kinds, {"choice", "score", "noul"})

    def test_verdict_flags_weak_design(self):
        notes = typesafe._meta_verdict({
            "questions_are_atomic": {"noul": 0.1},
            "questions_are_independent": {"noul": 0.9},
            "options_are_distinct": {"score": 0.0},
            "context_is_sufficient": {"score": 2.0},
            "confidence_is_planned": {"noul": 0.1},
        })
        self.assertEqual(len(notes), 3)


class CliAndModuleTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.spec = self.root / "JEV.json"
        self.spec.write_text(json.dumps(_clean_spec()), encoding="utf-8")

    def test_cli_review(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["typesafe", "review", "-d", str(self.root),
                             "--spec", str(self.spec)])
        self.assertEqual(code, 0)

    def test_module_enable_installs_pack(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["module", "enable", "typesafe", "-d", str(self.root)])
        self.assertEqual(code, 0)
        self.assertTrue((self.root / "docs" / "fia" / "typesafe" / "README.md").exists())
        self.assertTrue((self.root / "docs" / "fia" / "typesafe" / "JEV_REFERENCE.md").exists())


if __name__ == "__main__":
    unittest.main()
