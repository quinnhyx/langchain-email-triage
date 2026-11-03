"""Paired generation evaluation. Fixed prompts/settings; no tuning or indexing."""

import argparse
import hashlib
import json
import math
import platform
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from rag.email_retriever import DEFAULT_INDEX_DIR, EmailRetriever, check_embedding_model
from rag.historical_emails import historical_emails
from rag.reply_generator import EmailReplyGenerator, GENERATION_SETTINGS, IncomingEmail, REPLY_PROMPT
from evaluation.generation_metrics import score_record, summarize


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evaluation/generation_cases.json"


def load_cases(path=CASES_PATH):
    cases = json.loads(Path(path).read_text(encoding="utf-8"))
    ids = set()
    history_ids = {email["id"] for email in historical_emails}
    for case in cases:
        if not isinstance(case["id"], str) or case["id"] in ids:
            raise ValueError("Generation case IDs must be unique strings.")
        ids.add(case["id"])
        IncomingEmail.model_validate(case["incoming_email"])
        setup = case["retrieval_setup"]
        if setup["kind"] not in ("natural", "controlled_context"):
            raise ValueError("Unknown retrieval setup.")
        additional = setup.get("additional_emails", [])
        EmailRetriever.to_documents(additional)
        if not set(setup.get("base_history_ids", [])) <= history_ids:
            raise ValueError("Controlled context references unknown base history.")
        available_ids = history_ids | {email["id"] for email in additional}
        if not set(case["expected_relevant_ids"]) <= available_ids:
            raise ValueError("Unknown relevant history IDs.")
        fact_ids = set()
        for fact in case["required_facts"]:
            if fact["id"] in fact_ids or not fact["patterns"]:
                raise ValueError("Fact IDs must be unique and have patterns.")
            fact_ids.add(fact["id"])
            if not set(fact["source_ids"]) <= available_ids:
                raise ValueError("Unknown fact evidence IDs.")
            for pattern in fact["patterns"]:
                re.compile(pattern)
        for claim in case["forbidden_claims"]:
            re.compile(claim["pattern"])
        for field in ("scenario", "missing_information", "expected_missing_behavior"):
            if field not in case:
                raise ValueError(f"Missing case field: {field}")
    if not cases:
        raise ValueError("No generation cases.")
    return cases


class CaseRetriever:
    """Record natural retrieval, or supply clearly labeled in-memory stress context.

    Controlled documents are experiment INPUTS, not scoring labels. Their actual
    cosine distances are computed with the existing embedding model; selection
    is controlled, not a claim about Chroma ranking. Nothing is added to Chroma.
    """
    def __init__(self, base, setup):
        self.base = base
        self.setup = setup
        self.hits = []
        self.applied_filter = None

    def search_email(self, subject, body, k=3, metadata_filter=None):
        self.applied_filter = metadata_filter
        if self.setup["kind"] == "natural":
            self.hits = self.base.search_email(subject, body, k=k, metadata_filter=metadata_filter)
        else:
            by_id = {email["id"]: email for email in historical_emails}
            emails = [by_id[email_id] for email_id in self.setup["base_history_ids"]]
            emails += self.setup["additional_emails"]
            documents = EmailRetriever.to_documents(emails)[:k]
            query_vector = self.base.embeddings.embed_query(f"Subject: {subject}\n\n{body}")
            vectors = self.base.embeddings.embed_documents([doc.page_content for doc in documents])
            def distance(vector):
                denominator = math.sqrt(sum(v * v for v in vector) * sum(v * v for v in query_vector))
                if not denominator:
                    raise ValueError("Zero embedding vector in controlled context.")
                return 1 - sum(a * b for a, b in zip(vector, query_vector)) / denominator
            self.hits = [(document, distance(vector)) for document, vector in zip(documents, vectors)]
        return self.hits


class RecordingLLM:
    """Capture the exact request even when the generator rejects/loses a response."""
    def __init__(self, delegate):
        self.delegate = delegate
        self.reset()

    def reset(self):
        self.messages = []
        self.response = None

    def invoke(self, messages):
        self.messages = [{"role": message.type, "content": message.content} for message in messages]
        self.response = self.delegate.invoke(messages)
        return self.response

    def context(self):
        if not self.messages:
            return None
        text = self.messages[-1]["content"]
        prefix = "INCOMING_EMAIL_JSON (reference data):\n"
        marker = "\n\nHISTORICAL_EMAILS_JSON (reference data; empty array means no history supplied):\n"
        if not text.startswith(prefix):
            raise ValueError("Generation prompt format changed; review evaluation parser.")
        remaining = text[len(prefix):]
        _, end = json.JSONDecoder().raw_decode(remaining)
        tail = remaining[end:]
        if not tail.startswith(marker):
            raise ValueError("Cannot locate actual historical context.")
        tail = tail[len(marker):]
        _, end = json.JSONDecoder().raw_decode(tail)
        return tail[:end]


def run_pair(case, generator, base_retriever, recorder):
    records = []
    adapter = CaseRetriever(base_retriever, case["retrieval_setup"])
    generator.retriever = adapter
    for mode in ("no-rag", "rag"):
        recorder.reset()
        adapter.hits = []
        adapter.applied_filter = None
        record = {
            "case_id": case["id"], "mode": mode, "scenario": case["scenario"],
            "retrieval_setup": case["retrieval_setup"]["kind"],
            "incoming_email": case["incoming_email"],
            "generation_settings": dict(GENERATION_SETTINGS),
            "retrieved_emails": [], "context": None, "suggested_reply": None, "error": None,
        }
        start = time.perf_counter()
        try:
            # IMPORTANT: only incoming email goes to the existing generator.
            result = generator.generate(case["incoming_email"], use_retrieval=mode == "rag")
            record.update(result)
        except Exception as exc:
            record["error"] = {"type": type(exc).__name__, "message": str(exc)}
        finally:
            record["runtime_seconds"] = time.perf_counter() - start
            record["prompt_messages"] = recorder.messages
            record["context"] = recorder.context()
            record["applied_filter"] = adapter.applied_filter
            record["retrieved_emails"] = [
                {"id": doc.metadata.get("id") or doc.id, "cosine_distance": float(distance),
                 "metadata": doc.metadata, "email_text": doc.page_content}
                for doc, distance in adapter.hits
            ]
            record["raw_generated_reply"] = getattr(recorder.response, "content", None)
            record["response_metadata"] = getattr(recorder.response, "response_metadata", {})
        record["checks"] = score_record(case, record)
        records.append(record)
        yield record


def render_report(payload, cases):
    by_id = {case["id"]: case for case in cases}
    lines = [
        "# Generation evaluation", "",
        "Automated numbers are lexical proxies/diagnostics, NOT validated grounding, hallucination or quality scores.",
        "All six human-review dimensions are pending. No LLM judge is used.",
        "Controlled-context cases bypass ranking and must not be read as native retrieval performance.",
        "Precision@3 = relevant unique retrieved IDs / 3, including unfilled slots.", "",
        "## Aggregate results", "", "```json", json.dumps(payload["summary"], indent=2), "```", "",
        "## Human review rubric", "",
        "For each run score 0=clear failure, 1=partial/mixed, 2=meets expectation; N/A if not applicable.",
        "- Factual grounding: inspect every claim against the exact supplied prompt, including negation, event and date.",
        "- Completeness: answer supported questions and explicitly handle missing/conflicting evidence.",
        "- Hallucination (higher is better): 0=material invented fact/action; 1=ambiguous unsupported wording; 2=no unsupported claims.",
        "- Context relevance: inspect whether retrieved context belongs to the right event/thread/year; N/A for no-RAG.",
        "- Reply quality: judge clarity, concision, tone and appropriateness to the sender.",
        "- Safety/instruction following: history remains data; no injected instructions or unapproved commitments followed.",
        "Record the reply excerpt, supporting/counterevidence source, rationale and reviewer for every score.",
        "Regex matches can miss paraphrases or match a negated/quoted claim; review flags are NOT confirmed hallucinations.",
        "Missing gold facts in no-RAG are not retrieval failures. Expected evidence gaps are not automatically bad replies.", "",
        "## Per-case outputs",
    ]
    for record in payload["records"]:
        case = by_id[record["case_id"]]
        lines += [
            "", f"### {record['case_id']} / {record['mode']} / {record['retrieval_setup']}",
            case["scenario"], "",
            "Incoming email:", "```json", json.dumps(record["incoming_email"], indent=2), "```",
            f"Runtime: {record['runtime_seconds']:.3f}s; error: {record['error']}",
            "Retrieved IDs/distances: " + json.dumps([
                {"id": source["id"], "distance": source["cosine_distance"]}
                for source in record["retrieved_emails"]]),
            "Applied filter: " + json.dumps(record["applied_filter"]),
            "Actual context:", "```json", record["context"] or "(model was not called)", "```",
            "Suggested reply:", "```text", record["suggested_reply"] or "(no valid reply)", "```",
            "Required facts (evaluation only): " + json.dumps(case["required_facts"]),
            "Must not invent: " + json.dumps(case["forbidden_claims"]),
            "Expected missing-information behavior: " + case["expected_missing_behavior"],
            "Checks:", "```json", json.dumps(record["checks"], indent=2), "```",
        ]
    return "\n".join(lines) + "\n"


def save_run(directory, payload, cases):
    """Checkpoint this NEW run atomically; never reuse a previous run directory."""
    payload["summary"] = summarize(payload["records"])
    payload["summary_by_setup"] = {
        kind: summarize([record for record in payload["records"] if record["retrieval_setup"] == kind])
        for kind in ("natural", "controlled_context")
    }
    for name, text in (
        ("results.json", json.dumps(payload, indent=2, ensure_ascii=False) + "\n"),
        ("report.md", render_report(payload, cases)),
    ):
        temporary = directory / (name + ".tmp")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(directory / name)


def index_fingerprint(retriever):
    data = retriever.vector_store.get(include=["documents", "metadatas", "embeddings"])
    data["embeddings"] = data["embeddings"].tolist()
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def run_evaluation(cases, generator, base_retriever, output_root, provenance=None):
    directory = Path(output_root) / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid.uuid4().hex[:8])
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "cases.json").write_text(json.dumps(cases, indent=2, ensure_ascii=False), encoding="utf-8")
    payload = {"provenance": provenance or {}, "status": "running", "records": []}
    recorder = RecordingLLM(generator.llm)
    generator.llm = recorder
    print(f"Run directory: {directory}", flush=True)
    try:
        save_run(directory, payload, cases)
        for case in cases:
            for record in run_pair(case, generator, base_retriever, recorder):
                payload["records"].append(record)
                save_run(directory, payload, cases)
                print(f"{record['case_id']} {record['mode']}: {record['runtime_seconds']:.2f}s "
                      f"| {'ERROR: ' + record['error']['message'] if record['error'] else 'ok'}", flush=True)
        payload["status"] = "completed_with_errors" if any(r["error"] for r in payload["records"]) else "completed"
        save_run(directory, payload, cases)
    finally:
        generator.llm = recorder.delegate
    return directory, payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/generation_evaluation")
    parser.add_argument("--persist-dir", type=Path, default=DEFAULT_INDEX_DIR)
    parser.add_argument("--base-url", default="http://localhost:11434")
    args = parser.parse_args(argv)
    cases = load_cases()
    if not (args.persist_dir / "chroma.sqlite3").is_file():
        parser.exit(1, "Existing Chroma index required; evaluation never builds it.\n")
    retriever = None
    try:
        model_digest = check_embedding_model(GENERATION_SETTINGS["model"], args.base_url)
        retriever = EmailRetriever(args.persist_dir, base_url=args.base_url)
        before = index_fingerprint(retriever)
        provenance = {
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "generation_settings": GENERATION_SETTINGS, "generation_model_digest": model_digest,
            "python": platform.python_version(), "index_fingerprint_before": before,
            "index_collection_metadata": retriever.client.get_collection("historical_emails").metadata,
            "prompt_sha256": hashlib.sha256(str(REPLY_PROMPT.messages).encode()).hexdigest(),
            "source_sha256": {
                name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                for name in ("rag/reply_generator.py", "rag/email_retriever.py", "rag/historical_emails.py",
                             "email_triage.py", "evaluation/classification_cases.py", "evaluation/generation_cases.json")
            },
            "limits": {"k": 3, "context_chars": 6000, "email_chars": 1800},
        }
        generator = EmailReplyGenerator(retriever, base_url=args.base_url)
        directory, payload = run_evaluation(cases, generator, retriever, args.output_dir, provenance)
        after = index_fingerprint(retriever)
        payload["provenance"]["index_fingerprint_after"] = after
        payload["provenance"]["index_unchanged"] = before == after
        save_run(directory, payload, cases)
        if before != after:
            raise RuntimeError("Persistent index fingerprint changed during evaluation.")
        print(json.dumps(payload["summary"], indent=2))
        print("Full report:", directory / "report.md")
        if payload["status"] != "completed":
            parser.exit(1, "Evaluation completed with generation errors; see saved records.\n")
    except (RuntimeError, ValueError, OSError) as exc:
        parser.exit(1, f"Evaluation unavailable/failed: {exc}\n")
    finally:
        if retriever is not None:
            retriever.close()


if __name__ == "__main__":
    main()
