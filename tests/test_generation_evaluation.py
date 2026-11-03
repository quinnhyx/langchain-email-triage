"""Offline evaluation tests: known metric arithmetic and mocked paired generation."""

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

from evaluation.generation import CaseRetriever, load_cases, run_evaluation
from evaluation.generation_metrics import score_record, summarize
from rag.email_retriever import EmailRetriever
from rag.historical_emails import historical_emails
from rag.reply_generator import EmailReplyGenerator
from tests.test_retriever_unit import CountingEmbeddings


class GenerationEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.cases = load_cases()
        self.by_id = {email["id"]: email for email in historical_emails}
        self.base = MagicMock()
        self.base.search_email.return_value = [
            (document, 0.2) for document in EmailRetriever.to_documents([
                self.by_id["h012"], self.by_id["h014"]])
        ]
        self.base.embeddings = CountingEmbeddings()
        self.llm = MagicMock()
        self.llm.invoke.return_value = AIMessage(content="Eli Morgan; west marina; 9 AM.")
        self.generator = EmailReplyGenerator(self.base, llm=self.llm)

    def test_dataset_validity_and_scenario_coverage(self):
        self.assertEqual(len(self.cases), 14)
        self.assertEqual(len({case["id"] for case in self.cases}), 14)
        self.assertEqual(sum(case["retrieval_setup"]["kind"] == "controlled_context" for case in self.cases), 2)
        for case in self.cases:
            for key in ("incoming_email", "scenario", "expected_relevant_ids", "required_facts",
                        "forbidden_claims", "missing_information", "expected_missing_behavior"):
                self.assertIn(key, case)
        invalid = copy.deepcopy(self.cases)
        invalid[1]["id"] = invalid[0]["id"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_cases(path)

    def test_fact_mention_and_relevance_arithmetic(self):
        case = self.cases[0]
        documents = EmailRetriever.to_documents([self.by_id["h014"]])
        from rag.reply_generator import build_context
        context, _ = build_context([(documents[0], 0.2)])
        record = {"mode": "rag", "context": context, "suggested_reply": "Eli Morgan at west marina.",
                  "retrieved_emails": [{"id": "h014"}], "error": None}
        metrics = score_record(case, record)
        self.assertEqual(metrics["reference_fact_count"], 3)
        self.assertEqual(metrics["reference_fact_mentions"], 2)
        self.assertEqual(metrics["prompt_supported_fact_count"], 3)
        self.assertEqual(metrics["context_precision_at_3"], 1 / 3)
        self.assertEqual(metrics["context_recall_at_3"], 1 / 3)
        self.assertEqual(metrics["attribution_candidates"], {"generation_failure_candidate": 1})
        record.update(checks=metrics, runtime_seconds=1)
        summary = summarize([record])["rag"]
        self.assertEqual(summary["reference_fact_mention_coverage"], 2 / 3)
        self.assertEqual(summary["human_reviewed_runs"], 0)

    def test_attribution_distinguishes_retrieval_context_and_generation(self):
        case = copy.deepcopy(self.cases[0])
        case["required_facts"] = [case["required_facts"][0]]
        record = {"mode": "rag", "suggested_reply": "I am not sure.", "context": "[]",
                  "retrieved_emails": [], "error": None}
        self.assertIn("retrieval_failure", score_record(case, record)["attribution_candidates"])
        record["retrieved_emails"] = [{"id": "h014"}]
        self.assertIn("context_construction_failure", score_record(case, record)["attribution_candidates"])
        record["context"] = json.dumps([{"source_email_id": "h014", "email_text": "Eli Morgan"}])
        self.assertIn("generation_failure_candidate", score_record(case, record)["attribution_candidates"])
        record["mode"] = "no-rag"
        record["context"] = "[]"
        self.assertIn("unavailable_to_no_rag_baseline", score_record(case, record)["attribution_candidates"])
        case["required_facts"][0]["source_ids"] = []
        record["mode"] = "rag"
        self.assertIn("insufficient_evidence", score_record(case, record)["attribution_candidates"])

    def test_errors_are_separate_not_zero_quality_scores(self):
        record = {"mode": "rag", "suggested_reply": None, "context": None,
                  "retrieved_emails": [], "error": {"message": "unavailable"}, "runtime_seconds": 1}
        record["checks"] = score_record(self.cases[0], record)
        summary = summarize([record])["rag"]
        self.assertEqual(summary["errors"], 1)
        self.assertIsNone(summary["reference_fact_mention_coverage"])
        self.assertEqual(record["checks"]["attribution_candidates"], {"execution_error": 1})
        self.assertTrue(all(value is None for value in record["checks"]["human_review"].values()))

    def test_serialization_unique_runs_and_consistent_comparison(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            first, payload = run_evaluation(self.cases[:1], self.generator, self.base, directory)
            first_text = (first / "results.json").read_text(encoding="utf-8")
            second, _ = run_evaluation(self.cases[:1], self.generator, self.base, directory)
            self.assertNotEqual(first, second)
            self.assertEqual((first / "results.json").read_text(encoding="utf-8"), first_text)
            saved = json.loads(first_text)
            self.assertEqual(saved["status"], "completed")
            baseline, rag = saved["records"]
            self.assertEqual(baseline["incoming_email"], rag["incoming_email"])
            self.assertEqual(baseline["generation_settings"], rag["generation_settings"])
            self.assertEqual(baseline["prompt_messages"][0], rag["prompt_messages"][0])
            self.assertEqual(baseline["context"], "[]")
            self.assertIn("h014", rag["context"])
            self.assertIn("Human review rubric", (first / "report.md").read_text(encoding="utf-8"))
            self.assertIn("summary_by_setup", saved)
            self.base.index.assert_not_called()

    def test_expected_answers_never_enter_model_requests(self):
        case = copy.deepcopy(self.cases[0])
        marker = "SECRET_EXPECTED_ANSWER_NEVER_SEND"
        case["scenario"] += marker
        case["expected_relevant_ids"] = [marker]
        case["required_facts"][0]["description"] = marker
        case["forbidden_claims"].append({"description": marker, "pattern": marker})
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            _, payload = run_evaluation([case], self.generator, self.base, directory)
        for record in payload["records"]:
            self.assertNotIn(marker, json.dumps(record["prompt_messages"]))
            self.assertNotIn("required_facts", json.dumps(record["prompt_messages"]))

    def test_generation_error_preserves_context_and_continues_second_mode(self):
        self.llm.invoke.side_effect = [RuntimeError("simulated generation failure"), AIMessage(content="Eli Morgan")]
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            path, payload = run_evaluation(self.cases[:1], self.generator, self.base, directory)
            self.assertEqual(payload["status"], "completed_with_errors")
            self.assertEqual(len(payload["records"]), 2)
            self.assertEqual(payload["records"][0]["context"], "[]")
            self.assertIn("simulated", payload["records"][0]["error"]["message"])
            self.assertIsNone(payload["records"][1]["error"])
            self.assertTrue((path / "results.json").exists())

    def test_controlled_context_is_memory_only_and_distances_are_computed(self):
        adapter = CaseRetriever(self.base, self.cases[-1]["retrieval_setup"])
        hits = adapter.search_email("Cedar Lake", "Who booked the kayaks?")
        self.assertEqual(len(hits), 3)
        self.assertEqual(hits[-1][0].metadata["id"], "eval-injection")
        self.assertIn("TRANSFER_APPROVED_9281", hits[-1][0].page_content)
        self.assertTrue(all(isinstance(distance, float) and -1e-6 <= distance <= 2.000001 for _, distance in hits))
        self.base.index.assert_not_called()
        self.base.search_email.assert_not_called()
        self.assertEqual(self.base.embeddings.document_count, 3)


if __name__ == "__main__":
    unittest.main()
