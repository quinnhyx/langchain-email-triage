"""Deterministic diagnostics, NOT a semantic judge of reply correctness."""

import json
import re
from collections import Counter


REVIEW_DIMENSIONS = (
    "factual_grounding", "completeness", "hallucination",
    "context_relevance", "reply_quality", "safety_instruction_following",
)


def matches(patterns, text):
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def score_record(case, record):
    """Score lexical fact mentions and trace evidence through retrieval/context.

    Labels enter only here, AFTER generation. Mention is not entailment: negation,
    wrong event, quotations and paraphrases all require human review.
    """
    reply = record.get("suggested_reply") or ""
    incoming = json.dumps(case["incoming_email"], ensure_ascii=False)
    # Do not treat transport metadata as factual evidence supplied to the LLM.
    incoming = json.dumps({k: case["incoming_email"][k] for k in
                           ("subject", "sender", "body")}, ensure_ascii=False)
    retrieved = {source["id"] for source in record.get("retrieved_emails", [])}
    context = json.loads(record.get("context") or "[]")
    facts = []
    attributions = Counter()
    for fact in case["required_facts"]:
        incoming_support = matches(fact["patterns"], incoming)
        matching_sources = [
            source["source_email_id"] for source in context
            if source["source_email_id"] in fact["source_ids"]
            and matches(fact["patterns"], source["email_text"])
        ]
        supported = incoming_support or bool(matching_sources)
        mentioned = matches(fact["patterns"], reply)
        diagnostic = None
        if not mentioned and not record.get("error"):
            if supported:
                diagnostic = "generation_failure_candidate"
            elif record["mode"] == "no-rag":
                diagnostic = "unavailable_to_no_rag_baseline"
            elif retrieved & set(fact["source_ids"]):
                diagnostic = "context_construction_failure"
            elif fact["source_ids"]:
                diagnostic = "retrieval_failure"
            else:
                diagnostic = "insufficient_evidence"
            attributions[diagnostic] += 1
        facts.append({
            "fact_id": fact["id"], "description": fact["description"],
            "mentioned_in_reply": mentioned, "evidence_in_prompt": supported,
            "context_evidence_ids": matching_sources, "diagnostic": diagnostic,
            "unsupported_mention_flag": mentioned and not supported,
        })
    flags = [
        claim["description"] for claim in case["forbidden_claims"]
        if re.search(claim["pattern"], reply, re.IGNORECASE)
    ]
    if record.get("error"):
        attributions["execution_error"] += 1
    relevant = set(case["expected_relevant_ids"])
    found = retrieved & relevant
    is_rag = record["mode"] == "rag"
    return {
        "reference_fact_mentions": sum(f["mentioned_in_reply"] for f in facts),
        "reference_fact_count": len(facts),
        "prompt_supported_fact_count": sum(f["evidence_in_prompt"] for f in facts),
        "prompt_supported_fact_mentions": sum(f["mentioned_in_reply"] and f["evidence_in_prompt"] for f in facts),
        "fact_checks": facts,
        "forbidden_claim_flags": flags,
        "unsupported_fact_mention_flags": [f["fact_id"] for f in facts if f["unsupported_mention_flag"]],
        "attribution_candidates": dict(attributions),
        "expected_evidence_gaps": case["missing_information"],
        "context_precision_at_3": len(found) / 3 if is_rag else None,
        "context_recall_at_3": len(found) / len(relevant) if is_rag and relevant else None,
        "irrelevant_retrieved_ids": sorted(retrieved - relevant) if is_rag else [],
        "missed_relevant_ids": sorted(relevant - retrieved) if is_rag else [],
        "human_review": {dimension: None for dimension in REVIEW_DIMENSIONS},
    }


def summarize(records):
    """Micro fact-mention coverage; average context precision/recall; errors separate."""
    summaries = {}
    for mode in ("no-rag", "rag"):
        rows = [record for record in records if record["mode"] == mode]
        successful = [record for record in rows if not record.get("error")]
        checks = [record["checks"] for record in successful]
        reference_count = sum(c["reference_fact_count"] for c in checks)
        evidence_count = sum(c["prompt_supported_fact_count"] for c in checks)
        attributions = Counter()
        for row in rows:
            attributions.update(row["checks"]["attribution_candidates"])
        precision = [c["context_precision_at_3"] for c in checks if c["context_precision_at_3"] is not None]
        recall = [c["context_recall_at_3"] for c in checks if c["context_recall_at_3"] is not None]
        summaries[mode] = {
            "runs": len(rows), "successful": len(successful), "errors": len(rows) - len(successful),
            "reference_fact_mention_coverage": sum(c["reference_fact_mentions"] for c in checks) / reference_count if reference_count else None,
            "reference_fact_denominator": reference_count,
            "prompt_supported_fact_mention_coverage": sum(c["prompt_supported_fact_mentions"] for c in checks) / evidence_count if evidence_count else None,
            "prompt_supported_fact_denominator": evidence_count,
            "flagged_replies_for_review": sum(bool(c["forbidden_claim_flags"] or c["unsupported_fact_mention_flags"]) for c in checks),
            "mean_context_precision_at_3": sum(precision) / len(precision) if precision else None,
            "mean_context_recall_at_3": sum(recall) / len(recall) if recall else None,
            "runtime_seconds": sum(r["runtime_seconds"] for r in rows),
            "attribution_candidates_fact_level": dict(attributions),
            "human_reviewed_runs": sum(any(value is not None for value in row["checks"]["human_review"].values()) for row in rows),
        }
    return summaries
