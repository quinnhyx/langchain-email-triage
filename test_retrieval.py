"""Build/query the independent historical index and report labeled retrieval metrics."""

import argparse
import json
from pathlib import Path

from rag.email_retriever import DEFAULT_INDEX_DIR, DEFAULT_MODEL, EmailRetriever
from rag.historical_emails import historical_emails, retrieval_queries


# Evaluation-only privileged knowledge. NEVER used by realistic_metadata_filter.
# These thread labels deliberately define an oracle candidate set, not a
# deployable strategy or an assumption about incoming email headers.
ORACLE_FILTERS = {
    "q1": {"thread_id": "aster-intern-2026"},
    "q2": {"thread_id": "beacon-data-2026"},
    "q3": {"thread_id": "capstone-ethics"},
    "q4": {"thread_id": "family-lake-trip"},
    "q5": {"thread_id": "birch-chair-return"},
    "q6": {"thread_id": "university-recovery"},
    "q7": {"thread_id": "accessibility-session-oct"},
    "q8": {"thread_id": "aster-intern-2025"},
}


def realistic_metadata_filter(incoming_metadata=None):
    """Use only explicit, trusted incoming envelope metadata supplied by caller.

    A transport-provided thread_id must use the historical index's namespace.
    Otherwise a sender restricts historical conversation participants (sender OR
    recipient), preserving both directions of a conversation. Never look up a
    fixture/query/history to guess a thread. Incoming date is not a safe cutoff.
    The frozen query-only fixtures provide no envelope, so all eight fall back.
    """
    if not incoming_metadata:
        return None
    thread_id = incoming_metadata.get("thread_id")
    if isinstance(thread_id, str) and thread_id.strip():
        return {"thread_id": thread_id}
    sender = incoming_metadata.get("sender")
    if isinstance(sender, str) and sender.strip():
        return {"$or": [{"sender": sender}, {"recipient": sender}]}
    return None


def retrieval_metrics(retrieved_ids, relevant_ids, k=3):
    """Precision@k uses relevant unique hits / k, even with fewer than k hits.

    Unfilled slots count as nonrelevant. Recall uses all relevant IDs as its
    denominator. Reciprocal rank rewards only the first relevant rank.
    """
    if type(k) is not int or k < 1:
        raise ValueError("k must be a positive integer.")
    relevant = set(relevant_ids)
    if not relevant:
        raise ValueError("A retrieval fixture must have at least one relevant ID.")
    top_k = list(retrieved_ids)[:k]
    relevant_count = len(set(top_k) & relevant)
    recall = relevant_count / len(relevant)
    reciprocal_rank = next(
        (1 / rank for rank, email_id in enumerate(top_k, 1) if email_id in relevant), 0.0
    )
    return {"precision": relevant_count / k, "recall": recall, "reciprocal_rank": reciprocal_rank}


def print_hits(hits):
    for rank, (document, distance) in enumerate(hits, 1):
        metadata = document.metadata
        print(
            f"{rank}. ID={metadata['id']} | Subject={metadata['subject']} | "
            f"Sender={metadata['sender']} | Date={metadata['date']} | "
            f"Thread={metadata['thread_id']} | cosine distance={distance:.6f}"
        )


def evaluate_retrieval(
    retriever, fixtures=retrieval_queries, k=3, mode="baseline", incoming_metadata_by_query=None
):
    """Evaluate one mode; labels are consulted only for scoring, never realistic filters."""
    if mode not in ("baseline", "oracle", "realistic"):
        raise ValueError(f"Unknown retrieval mode: {mode}")
    print(f"\nMODE: {mode}" + (" (ORACLE: privileged metadata, not realistic performance)" if mode == "oracle" else ""))
    print(f"Precision@{k} convention: relevant unique hits / {k}; missing slots count as nonrelevant.")
    reports = []
    for fixture in fixtures:
        if mode == "oracle":
            if fixture["id"] not in ORACLE_FILTERS:
                raise ValueError(f"No oracle filter defined for {fixture['id']}")
            metadata_filter = ORACLE_FILTERS[fixture["id"]]
            filter_source = "privileged oracle thread label"
        elif mode == "realistic":
            incoming = (incoming_metadata_by_query or {}).get(fixture["id"])
            metadata_filter = realistic_metadata_filter(incoming)
            filter_source = "explicit incoming envelope" if metadata_filter else "fallback: no reliable incoming metadata"
        else:
            metadata_filter = None
            filter_source = "unfiltered semantic search"
        print(f"\n{fixture['id']} | Mode: {mode}: {fixture['query']}")
        print(f"Applied filter: {json.dumps(metadata_filter, sort_keys=True) if metadata_filter is not None else 'none'} | {filter_source}")
        # Preserve the original call exactly for unfiltered baseline/fallback.
        hits = (retriever.search(fixture["query"], k=k) if metadata_filter is None else
                retriever.search(fixture["query"], k=k, metadata_filter=metadata_filter))
        print_hits(hits)
        ids = [document.metadata["id"] for document, _ in hits]
        metrics = retrieval_metrics(ids, fixture["relevant_ids"], k)
        missing = sorted(set(fixture["relevant_ids"]) - set(ids))
        irrelevant = [email_id for email_id in ids if email_id not in fixture["relevant_ids"]]
        hard_negatives = sorted(set(ids) & set(fixture["hard_negative_ids"]))
        excluded = []
        if metadata_filter is not None:
            eligible = set(retriever.vector_store.get(where=metadata_filter, include=[])["ids"])
            excluded = sorted(set(fixture["relevant_ids"]) - eligible)
        print(f"Relevant: {fixture['relevant_ids']} | Missing: {missing}")
        print(f"Irrelevant hits: {irrelevant} | Hard-negative hits: {hard_negatives}")
        print(f"Filter-excluded relevant IDs (false negatives): {excluded}")
        print(f"Precision@{k}: {metrics['precision']:.3f} | Recall@{k}: {metrics['recall']:.3f} | RR@{k}: {metrics['reciprocal_rank']:.3f}")
        reports.append({
            "query_id": fixture["id"], "mode": mode, "applied_filter": metadata_filter,
            "filter_source": filter_source, "retrieved_ids": ids,
            "distances": [float(distance) for _, distance in hits],
            "missed_relevant_ids": missing, "hard_negative_ids": hard_negatives,
            "filter_excluded_relevant_ids": excluded, **metrics,
        })
    if not reports:
        raise ValueError("No retrieval evaluation fixtures.")
    summary = {
        f"Precision@{k}": sum(row["precision"] for row in reports) / len(reports),
        f"Recall@{k}": sum(row["recall"] for row in reports) / len(reports),
        f"MRR@{k}": sum(row["reciprocal_rank"] for row in reports) / len(reports),
        "queries": reports,
    }
    print(f"\nAggregate mode: {mode}")
    print(f"Mean Precision@{k}: {summary[f'Precision@{k}']:.3f}")
    print(f"Mean Recall@{k}: {summary[f'Recall@{k}']:.3f}")
    print(f"MRR@{k}: {summary[f'MRR@{k}']:.3f}")
    return summary


def compare_retrieval_modes(retriever, fixtures=retrieval_queries, k=3, incoming_metadata_by_query=None):
    """Run identical queries/index under all three policies and print per-query deltas."""
    summaries = {
        mode: evaluate_retrieval(retriever, fixtures, k, mode, incoming_metadata_by_query)
        for mode in ("baseline", "oracle", "realistic")
    }
    print("\nCOMPARISON (same queries, embeddings and persistent index)")
    for mode, summary in summaries.items():
        print(f"{mode}: Precision@{k}={summary[f'Precision@{k}']:.3f} | "
              f"Recall@{k}={summary[f'Recall@{k}']:.3f} | MRR@{k}={summary[f'MRR@{k}']:.3f}")
    for index, baseline in enumerate(summaries["baseline"]["queries"]):
        for mode in ("oracle", "realistic"):
            row = summaries[mode]["queries"][index]
            recovered = sorted(set(baseline["missed_relevant_ids"]) - set(row["missed_relevant_ids"]))
            newly_missed = sorted(set(row["missed_relevant_ids"]) - set(baseline["missed_relevant_ids"]))
            print(f"{row['query_id']} {mode} vs baseline: "
                  f"delta P={row['precision'] - baseline['precision']:+.3f}, "
                  f"delta R={row['recall'] - baseline['recall']:+.3f}, "
                  f"delta RR={row['reciprocal_rank'] - baseline['reciprocal_rank']:+.3f}; "
                  f"recovered={recovered}; newly missed={newly_missed}; "
                  f"filter excluded={row['filter_excluded_relevant_ids']}")
    return summaries


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="Index/synchronize the full synthetic history.")
    parser.add_argument("--query", help="Retrieve top-3 emails for this query.")
    parser.add_argument("--evaluate", action="store_true", help="Run all eight labeled queries.")
    parser.add_argument("--mode", choices=("baseline", "oracle", "realistic", "all"), default="baseline",
                        help="Evaluation mode; default preserves the original unfiltered baseline.")
    parser.add_argument("--incoming-metadata-file", type=Path,
                        help="Optional JSON mapping query IDs to actual trusted incoming envelope metadata.")
    parser.add_argument("--persist-dir", default=str(DEFAULT_INDEX_DIR))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default="http://localhost:11434")
    args = parser.parse_args(argv)
    if not (args.build or args.query or args.evaluate):
        args.query = "Following up on our previous internship interview"
    try:
        retriever = EmailRetriever(args.persist_dir, args.model, args.base_url)
        try:
            if args.build:
                print("Index:", retriever.index(historical_emails))
            if args.query:
                print_hits(retriever.search(args.query, k=3))
            if args.evaluate:
                incoming = None
                if args.incoming_metadata_file:
                    incoming = json.loads(args.incoming_metadata_file.read_text(encoding="utf-8"))
                    if not isinstance(incoming, dict) or any(not isinstance(value, dict) for value in incoming.values()):
                        raise ValueError("Incoming metadata JSON must map query IDs to metadata objects.")
                if args.mode == "all":
                    compare_retrieval_modes(retriever, incoming_metadata_by_query=incoming)
                else:
                    evaluate_retrieval(retriever, mode=args.mode, incoming_metadata_by_query=incoming)
        finally:
            retriever.close()
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(1, f"Retrieval failed: {exc}\n")


if __name__ == "__main__":
    main()
