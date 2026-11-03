"""Offline regression checks for the evaluation infrastructure (no Ollama calls)."""

import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from evaluation import triage as evaluation


def fixture_predictions(cases):
    """Synthetic perfect predictions for infrastructure checks, not model scores."""
    return [
        {
            "id": case["id"],
            "subject": case["subject"],
            **{f"expected_{label}": case[f"expected_{label}"] for label in evaluation.LABELS},
            **{f"predicted_{label}": case[f"expected_{label}"] for label in evaluation.LABELS},
            "reason": "Synthetic test fixture",
            "suggested_reply": "",
        }
        for case in cases
    ]


class EvaluationTests(unittest.TestCase):
    def test_fixed_selection_references_original_cases(self):
        quick = evaluation.select_cases("quick")
        self.assertEqual([case["id"] for case in quick],
                         [1, 3, 6, 7, 8, 11, 16, 18, 29, 30, 35, 39, 44])
        full = evaluation.select_cases("full")
        self.assertEqual([case["id"] for case in full], list(range(1, 46)))
        for case in quick:
            self.assertIs(case, full[case["id"] - 1])

    def test_inference_and_cache_cli_for_both_modes(self):
        class FakeTriage:
            calls = []

            def analyze(self, subject, body):
                self.calls.append((subject, body))
                case = next(case for case in evaluation.test_emails if case["subject"] == subject)
                return SimpleNamespace(
                    **{label: case[f"expected_{label}"] for label in evaluation.LABELS},
                    reason="Synthetic test fixture", suggested_reply="",
                )

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(evaluation, "RESULTS_DIR", Path(directory)):
                for mode in ("quick", "full"):
                    cases = evaluation.select_cases(mode)
                    FakeTriage.calls = []
                    output = io.StringIO()
                    fake_module = SimpleNamespace(EmailTriage=FakeTriage)
                    with patch.dict(sys.modules, {"email_triage": fake_module}), redirect_stdout(output):
                        evaluation.main([f"--{mode}"])
                    self.assertEqual(FakeTriage.calls,
                                     [(case["subject"], case["body"]) for case in cases])
                    path = Path(directory) / f"{mode}_predictions.json"
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    self.assertEqual(payload["metadata"]["evaluated_ids"], [c["id"] for c in cases])
                    self.assertEqual(payload["metadata"]["model_name"], "qwen3:8b")
                    self.assertIn("created_at_utc", payload["metadata"])
                    fresh_report = output.getvalue().split("\nACCURACY", 1)[1]
                    output = io.StringIO()
                    with patch.object(evaluation, "run_inference", side_effect=AssertionError("Inference forbidden")), redirect_stdout(output):
                        evaluation.main([f"--{mode}", "--use-cache"])
                    self.assertEqual(output.getvalue().split("\nACCURACY", 1)[1], fresh_report)

                    # A separate Python process proves the CLI cache branch does
                    # not even import production code, not just that it skips analyze().
                    script = (
                        "import builtins,sys,pathlib; import evaluation.triage as e; "
                        f"e.RESULTS_DIR=pathlib.Path({str(directory)!r}); "
                        "original=builtins.__import__; "
                        "\ndef guarded(name,*args,**kwargs):\n"
                        " if name == 'email_triage': raise AssertionError('Production import forbidden')\n"
                        " return original(name,*args,**kwargs)\n"
                        "builtins.__import__=guarded\n"
                        f"e.main(['--{mode}','--use-cache'])\n"
                    )
                    process = subprocess.run([sys.executable, "-B", "-c", script],
                                             cwd=evaluation.PROJECT_DIR, capture_output=True,
                                             text=True, encoding="utf-8")
                    self.assertEqual(process.returncode, 0, process.stderr)
                    self.assertIn("Exact Match Accuracy: 100.00%", process.stdout)

    def test_metric_arithmetic_errors_and_critical_detection(self):
        rows = fixture_predictions(evaluation.select_cases("full")[:3])
        rows[0]["predicted_action"] = "ignore"
        rows[1]["predicted_category"] = "other"
        rows[1]["predicted_priority"] = "high"
        metrics = evaluation.compute_metrics(rows)
        for label in evaluation.LABELS:
            self.assertAlmostEqual(metrics["accuracy"][label], 2 / 3)
            self.assertEqual(len(metrics["errors"][label]), 1)
        self.assertAlmostEqual(metrics["exact_match_accuracy"], 1 / 3)
        self.assertEqual(metrics["confusion_matrices"]["action"].loc["reply", "ignore"], 1)
        self.assertEqual(metrics["action_error_patterns"].loc[("reply", "ignore")], 1)
        self.assertEqual(metrics["critical_errors"]["id"].tolist(), [1])
        output = io.StringIO()
        with redirect_stdout(output):
            evaluation.print_report(metrics)
        for heading in ("CATEGORY ERRORS", "ACTION ERRORS", "PRIORITY ERRORS",
                        "ACTION ERROR PATTERNS", "CRITICAL ERRORS (reply -> ignore)"):
            self.assertIn(heading, output.getvalue())
        self.assertIn(rows[0]["subject"], output.getvalue())

    def test_stale_metadata_is_rejected(self):
        cases = evaluation.select_cases("quick")
        metadata = evaluation.build_cache_metadata("quick", cases)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quick_predictions.json"
            evaluation.save_predictions(path, metadata, fixture_predictions(cases))
            for key in ("mode", "model_name", "case_count", "evaluated_ids",
                        "inputs_sha256", "classifier_sha256", "cache_version"):
                changed = {**metadata, key: "changed"}
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, "stale"):
                    evaluation.load_predictions(path, changed, cases)
            changed_cases = copy.deepcopy(cases)
            changed_cases[0]["body"] += " Changed input."
            changed = evaluation.build_cache_metadata("quick", changed_cases)
            with self.assertRaisesRegex(ValueError, "inputs_sha256"):
                evaluation.load_predictions(path, changed, changed_cases)

    def test_malformed_prediction_rows_are_rejected(self):
        cases = evaluation.select_cases("quick")
        valid = fixture_predictions(cases)
        invalid = [valid[:-1], list(reversed(valid))]
        for field, value in (("id", True), ("subject", "wrong"),
                             ("expected_action", "ignore"), ("predicted_action", "invalid")):
            rows = copy.deepcopy(valid)
            rows[0][field] = value
            invalid.append(rows)
        for rows in invalid:
            with self.subTest(rows=rows[0]), self.assertRaises(ValueError):
                evaluation.validate_predictions(rows, cases)

    def test_missing_invalid_cache_fails_without_inference(self):
        cases = evaluation.select_cases("quick")
        metadata = evaluation.build_cache_metadata("quick", cases)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quick_predictions.json"
            with patch.object(evaluation, "RESULTS_DIR", Path(directory)), patch.object(
                evaluation, "run_inference", side_effect=AssertionError("Inference forbidden")
            ), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    evaluation.main(["--quick", "--use-cache"])
                self.assertEqual(error.exception.code, 1)
            for text in ("not json", "[]", '{"metadata": {}}'):
                path.write_text(text, encoding="utf-8")
                with self.subTest(text=text), self.assertRaises(ValueError):
                    evaluation.load_predictions(path, metadata, cases)

    def test_default_full_and_mutually_exclusive_modes(self):
        with patch.object(evaluation, "run_inference", return_value=[]), patch.object(
            evaluation, "validate_predictions", side_effect=ValueError("stop before save")
        ), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                evaluation.main([])
            self.assertEqual(len(evaluation.run_inference.call_args.args[0]), 45)
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            evaluation.main(["--quick", "--full"])
        self.assertEqual(error.exception.code, 2)

    def test_failed_inference_preserves_previous_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quick_predictions.json"
            path.write_text("previous cache", encoding="utf-8")
            with patch.object(evaluation, "RESULTS_DIR", Path(directory)), patch.object(
                evaluation, "run_inference", side_effect=RuntimeError("model unavailable")
            ), redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
                evaluation.main(["--quick"])
            self.assertEqual(path.read_text(encoding="utf-8"), "previous cache")


if __name__ == "__main__":
    unittest.main()
