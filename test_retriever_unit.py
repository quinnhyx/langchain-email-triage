"""Offline infrastructure tests using real Chroma and deterministic test vectors."""

import copy
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from langchain_core.embeddings import Embeddings

from rag.email_retriever import EmailRetriever, check_embedding_model
from rag.historical_emails import historical_emails, retrieval_queries
from test_retrieval import evaluate_retrieval, realistic_metadata_filter, retrieval_metrics


class CountingEmbeddings(Embeddings):
    """Test-only token hashes; these are NOT a semantic embedding model."""

    def __init__(self):
        self.document_count = 0
        self.query_count = 0

    @staticmethod
    def vector(text):
        values = [0.0] * 64
        for word in re.findall(r"\w+", text.lower()):
            position = int.from_bytes(hashlib.sha256(word.encode()).digest()[:4], "big") % 64
            values[position] += 1
        return values

    def embed_documents(self, texts):
        self.document_count += len(texts)
        return [self.vector(text) for text in texts]

    def embed_query(self, text):
        self.query_count += 1
        return self.vector(text)


class RetrievalTests(unittest.TestCase):
    def test_fixtures_and_no_classification_leakage(self):
        from test_emails import test_emails

        documents = EmailRetriever.to_documents(historical_emails)
        ids = {doc.id for doc in documents}
        self.assertEqual(len(documents), 26)
        self.assertEqual(len(ids), 26)
        self.assertEqual(len(retrieval_queries), 8)
        self.assertTrue(all(email["body"] not in {case["body"] for case in test_emails}
                            for email in historical_emails))
        for email, doc in zip(historical_emails, documents):
            self.assertIn(email["subject"], doc.page_content)
            self.assertIn(email["body"], doc.page_content)
            for field in ("id", "thread_id", "sender", "recipient", "subject", "date"):
                self.assertEqual(doc.metadata[field], email[field])
        for fixture in retrieval_queries:
            self.assertTrue(set(fixture["relevant_ids"]) <= ids)
            self.assertTrue(set(fixture["hard_negative_ids"]) <= ids)
            self.assertFalse(set(fixture["relevant_ids"]) & set(fixture["hard_negative_ids"]))

    def test_invalid_history(self):
        for field, value in (("sender", ""), ("date", "not-a-date"), ("id", 7)):
            email = {**historical_emails[0], field: value}
            with self.subTest(field=field), self.assertRaises(ValueError):
                EmailRetriever.to_documents([email])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            EmailRetriever.to_documents([historical_emails[0]] * 2)

    def test_real_chroma_incremental_index_distance_and_process_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            embeddings = CountingEmbeddings()
            retriever = EmailRetriever(directory, model_name="offline-test", embeddings=embeddings)
            try:
                self.assertEqual(retriever.index(historical_emails),
                                 {"embedded": 26, "skipped": 0, "removed": 0, "total": 26})
                self.assertEqual(retriever.index(historical_emails)["embedded"], 0)
                self.assertEqual(embeddings.document_count, 26)
                document = EmailRetriever.to_documents(historical_emails)[0]
                hits = retriever.search(document.page_content, k=3)
                self.assertEqual(hits[0][0].metadata["id"], "h001")
                self.assertAlmostEqual(hits[0][1], 0, places=5)
                self.assertEqual([distance for _, distance in hits],
                                 sorted(distance for _, distance in hits))
                self.assertEqual(embeddings.query_count, 1)
                returned = hits[0][0]
                self.assertEqual(returned.page_content, document.page_content)
                self.assertEqual(returned.metadata, document.metadata)
                retriever.search_email("Aster summer placement", "September perception internship", k=3)
                self.assertEqual(embeddings.query_count, 2)
                changed = copy.deepcopy(historical_emails)
                changed[0]["body"] += " Bring a project diagram."
                self.assertEqual(retriever.index(changed)["embedded"], 1)
                self.assertEqual(embeddings.document_count, 27)
                self.assertEqual(len(retriever.vector_store.get()["ids"]), 26)
                self.assertEqual(retriever.index(historical_emails)["embedded"], 1)
            finally:
                retriever.close()

            # Reopen in a fresh process: persistence is not just an in-memory cache.
            script = (
                "import json; from rag.email_retriever import EmailRetriever; "
                "from rag.historical_emails import historical_emails; "
                "from test_retriever_unit import CountingEmbeddings; "
                f"e=CountingEmbeddings(); r=EmailRetriever({directory!r},model_name='offline-test',embeddings=e); "
                "stats=r.index(historical_emails); "
                "print(json.dumps({'stats':stats,'embedded':e.document_count})); r.close()"
            )
            process = subprocess.run([sys.executable, "-B", "-c", script],
                                     cwd=Path(__file__).resolve().parent,
                                     capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(process.returncode, 0, process.stderr)
            payload = json.loads(process.stdout)
            self.assertEqual(payload["stats"]["skipped"], 26)
            self.assertEqual(payload["embedded"], 0)

    def test_snapshot_removal_and_search_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            retriever = EmailRetriever(directory, model_name="offline-test", embeddings=CountingEmbeddings())
            try:
                with self.assertRaisesRegex(ValueError, "empty"):
                    retriever.search("internship")
                retriever.index(historical_emails[:2])
                self.assertEqual(len(retriever.search("internship", k=9)), 2)
                stats = retriever.index(historical_emails[:1])
                self.assertEqual(stats["removed"], 1)
                self.assertEqual(retriever.vector_store.get()["ids"], ["h001"])
                for query, k in (("", 3), ("internship", 0), ("internship", True)):
                    with self.subTest(query=query, k=k), self.assertRaises(ValueError):
                        retriever.search(query, k)
            finally:
                retriever.close()

    def test_embedding_identity_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            retriever = EmailRetriever(directory, model_name="offline-test", embeddings=CountingEmbeddings())
            retriever.index(historical_emails[:1])
            retriever.close()
            with self.assertRaisesRegex(ValueError, "differs"):
                EmailRetriever(directory, model_name="different-model", embeddings=CountingEmbeddings())

    def test_model_check_never_downloads(self):
        response = io.BytesIO(json.dumps({"models": [
            {"name": "nomic-embed-text:latest", "digest": "installed-digest"}
        ]}).encode())
        with patch("rag.email_retriever.urlopen", return_value=response):
            self.assertEqual(check_embedding_model("nomic-embed-text", "http://localhost:11434"),
                             "installed-digest")
        with patch("rag.email_retriever.urlopen", return_value=io.BytesIO(b'{"models": []}')):
            with self.assertRaisesRegex(RuntimeError, "ollama pull"):
                check_embedding_model("nomic-embed-text", "http://localhost:11434")

    def test_metrics_known_ranks_and_truncation(self):
        relevant = retrieval_queries[0]["relevant_ids"]  # h001, h002, h003
        values = retrieval_metrics(["h006", "h003", "h002", "h001"], relevant, k=3)
        self.assertAlmostEqual(values["recall"], 2 / 3)
        self.assertAlmostEqual(values["precision"], 2 / 3)
        self.assertEqual(values["reciprocal_rank"], 1 / 2)
        self.assertEqual(retrieval_metrics(["h006"], relevant)["recall"], 0)
        self.assertEqual(retrieval_metrics(["h006"], relevant)["reciprocal_rank"], 0)
        self.assertEqual(retrieval_metrics(["h001", "h001"], relevant)["recall"], 1 / 3)
        with self.assertRaises(ValueError):
            retrieval_metrics([], [])

    def test_evaluation_macro_means_and_error_output(self):
        fixtures = retrieval_queries[:2]
        documents = {doc.id: doc for doc in EmailRetriever.to_documents(historical_emails)}

        class FixedResults:
            def search(self, query, k):
                # Explicit synthetic rankings to check metric math, NOT model outputs.
                ids = ["h006", "h003", "h002"] if query == fixtures[0]["query"] else ["h006", "h007", "h008"]
                return [(documents[email_id], float(rank)) for rank, email_id in enumerate(ids)]

        output = io.StringIO()
        with redirect_stdout(output):
            report = evaluate_retrieval(FixedResults(), fixtures)
        self.assertAlmostEqual(report["Recall@3"], (2 / 3 + 1) / 2)
        self.assertEqual(report["MRR@3"], (1 / 2 + 1) / 2)
        self.assertIn("Hard-negative hits: ['h006']", output.getvalue())
        self.assertIn("Missing: ['h001']", output.getvalue())

    def test_unfiltered_call_is_exactly_backward_compatible(self):
        retriever = object.__new__(EmailRetriever)
        retriever.vector_store = MagicMock()
        retriever.vector_store.get.return_value = {"ids": ["h001", "h002"]}
        expected = [(EmailRetriever.to_documents(historical_emails[:1])[0], 0.25)]
        retriever.vector_store.similarity_search_with_score.return_value = expected
        self.assertIs(retriever.search("internship", k=3), expected)
        retriever.vector_store.similarity_search_with_score.assert_called_once_with("internship", k=2)
        retriever.vector_store.similarity_search_with_score.reset_mock()
        self.assertIs(retriever.search("internship", k=3, metadata_filter=None), expected)
        retriever.vector_store.similarity_search_with_score.assert_called_once_with("internship", k=2)
        retriever.vector_store.similarity_search_with_score.reset_mock()
        query_filter = {"thread_id": "aster-intern-2026"}
        retriever.search_email("subject", "body", metadata_filter=query_filter)
        retriever.vector_store.similarity_search_with_score.assert_called_once_with(
            "Subject: subject\n\nbody", k=2, filter=query_filter
        )

    def test_native_metadata_filters_zero_matches_and_incorrect_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            embeddings = CountingEmbeddings()
            retriever = EmailRetriever(directory, model_name="offline-test", embeddings=embeddings)
            try:
                retriever.index(historical_emails)
                query = retrieval_queries[0]["query"]
                baseline = retriever.search(query)
                explicit_none = retriever.search(query, metadata_filter=None)
                self.assertEqual([(d.metadata["id"], s) for d, s in baseline],
                                 [(d.metadata["id"], s) for d, s in explicit_none])
                cases = [
                    ({"thread_id": "aster-intern-2026"}, {"h001", "h002", "h003"}),
                    ({"sender": "maya@aster.example"}, {"h001", "h003", "h004", "h005"}),
                    ({"date": "2026-09-18"}, {"h003", "h007"}),
                    ({"$and": [{"thread_id": "aster-intern-2026"},
                               {"sender": "maya@aster.example"}]}, {"h001", "h003"}),
                ]
                for metadata_filter, allowed in cases:
                    with self.subTest(metadata_filter=metadata_filter):
                        hits = retriever.search(query, k=30, metadata_filter=metadata_filter)
                        self.assertEqual({d.metadata["id"] for d, _ in hits}, allowed)
                        self.assertEqual([s for _, s in hits], sorted(s for _, s in hits))
                empty = retriever.search(query, metadata_filter={"thread_id": "does-not-exist"})
                self.assertEqual(empty, [])
                self.assertEqual(retrieval_metrics([], retrieval_queries[0]["relevant_ids"]),
                                 {"precision": 0, "recall": 0, "reciprocal_rank": 0})
                wrong = retriever.search(query, metadata_filter={"thread_id": "aster-intern-2025"})
                ids = [d.metadata["id"] for d, _ in wrong]
                self.assertEqual(set(ids), {"h004", "h005"})
                self.assertEqual(retrieval_metrics(ids, retrieval_queries[0]["relevant_ids"])["recall"], 0)
                # Evaluation explicitly diagnoses relevant IDs eliminated by a bad filter.
                with patch("test_retrieval.ORACLE_FILTERS", {"q1": {"thread_id": "aster-intern-2025"}}), redirect_stdout(io.StringIO()):
                    report = evaluate_retrieval(retriever, retrieval_queries[:1], mode="oracle")
                self.assertEqual(report["queries"][0]["filter_excluded_relevant_ids"],
                                 ["h001", "h002", "h003"])
                self.assertEqual(embeddings.document_count, 26)  # querying never reindexes
            finally:
                retriever.close()

    def test_precision_denominator_is_k_even_for_short_results(self):
        relevant = ["h015", "h016"]
        self.assertEqual(retrieval_metrics(relevant, relevant)["precision"], 2 / 3)
        self.assertEqual(retrieval_metrics(relevant, relevant)["recall"], 1)
        self.assertEqual(retrieval_metrics(["h015"], relevant)["precision"], 1 / 3)
        self.assertEqual(retrieval_metrics(["h015", "h015"], relevant)["precision"], 1 / 3)
        self.assertEqual(retrieval_metrics([], relevant)["precision"], 0)
        self.assertEqual(retrieval_metrics(["x", "y", "z", "h015"], relevant)["precision"], 0)

    def test_realistic_filters_use_only_explicit_envelope(self):
        self.assertIsNone(realistic_metadata_filter())
        self.assertIsNone(realistic_metadata_filter({}))
        self.assertIsNone(realistic_metadata_filter({"date": "2026-10-17"}))
        self.assertIsNone(realistic_metadata_filter({
            "query_id": "q1", "query": "Aster Robotics",
            "relevant_ids": ["h001"], "note": "aster-intern-2026",
        }))
        self.assertEqual(realistic_metadata_filter({"thread_id": "actual-header-thread", "sender": "a@example.test"}),
                         {"thread_id": "actual-header-thread"})
        self.assertEqual(realistic_metadata_filter({"sender": "a@example.test"}),
                         {"$or": [{"sender": "a@example.test"}, {"recipient": "a@example.test"}]})

    def test_realistic_fallback_does_not_consult_oracle_or_labels(self):
        documents = EmailRetriever.to_documents(historical_emails[:3])
        retriever = MagicMock()
        retriever.search.return_value = [(document, 0.1) for document in documents]
        fixtures = retrieval_queries[:1]
        with patch("test_retrieval.ORACLE_FILTERS", {}), redirect_stdout(io.StringIO()):
            baseline = evaluate_retrieval(retriever, fixtures)
            realistic = evaluate_retrieval(retriever, fixtures, mode="realistic")
        for call in retriever.search.call_args_list:
            self.assertEqual(call.kwargs, {"k": 3})
        self.assertEqual(baseline["Recall@3"], realistic["Recall@3"])
        self.assertEqual(realistic["queries"][0]["applied_filter"], None)
        self.assertIn("fallback", realistic["queries"][0]["filter_source"])
        changed = copy.deepcopy(fixtures)
        changed[0]["relevant_ids"] = ["h026"]
        with redirect_stdout(io.StringIO()):
            report = evaluate_retrieval(retriever, changed, mode="realistic")
        self.assertIsNone(report["queries"][0]["applied_filter"])
        retriever.vector_store.get.assert_not_called()

    def test_realistic_sender_filter_keeps_both_directions(self):
        with tempfile.TemporaryDirectory() as directory:
            retriever = EmailRetriever(directory, model_name="offline-test", embeddings=CountingEmbeddings())
            try:
                retriever.index(historical_emails)
                with redirect_stdout(io.StringIO()):
                    report = evaluate_retrieval(
                        retriever, retrieval_queries[:1], k=10, mode="realistic",
                        incoming_metadata_by_query={"q1": {"sender": "maya@aster.example"}},
                    )
                ids = set(report["queries"][0]["retrieved_ids"])
                self.assertEqual(ids, {"h001", "h002", "h003", "h004", "h005"})
                self.assertEqual(report["queries"][0]["filter_excluded_relevant_ids"], [])
                # Sender alone does not invent a specific year/thread.
                self.assertIn("h004", ids)
            finally:
                retriever.close()


if __name__ == "__main__":
    unittest.main()
