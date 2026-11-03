"""Compare no-RAG and RAG suggested replies. Nothing is sent or indexed."""

import argparse
import json
from pathlib import Path

from httpx import HTTPError
from ollama import ResponseError

from rag.reply_generator import EmailReplyGenerator, GENERATION_SETTINGS, IncomingEmail


def print_result(result):
    print(f"\n=== {result['mode']} | suggested draft, NOT sent ===")
    print("Filter:", json.dumps(result["applied_filter"]), "|", result["filter_source"])
    print("Retrieved emails (cosine distance: LOWER is closer):")
    for rank, source in enumerate(result["retrieved_emails"], 1):
        print(f"{rank}. {source['id']} | distance={source['cosine_distance']:.6f} | "
              f"in context={source['included_in_context']} | "
              f"metadata={json.dumps(source['metadata'], ensure_ascii=False)}")
    if not result["retrieved_emails"]:
        print("(none)")
    print(f"Exact historical context supplied to Qwen ({result['context_chars']} chars):")
    print(result["context"])
    print("\nSuggested reply:")
    print(result["suggested_reply"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email-file", type=Path, required=True,
                        help="UTF-8 JSON: subject, sender, body, optional metadata.")
    parser.add_argument("--mode", choices=("no-rag", "rag", "both"), default="both")
    parser.add_argument("--metadata-filter", help="Optional native Chroma filter as a JSON object.")
    parser.add_argument("--persist-dir", type=Path, default=Path(__file__).resolve().parents[1] / "rag/chroma_db")
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--output", type=Path, help="Optional JSON file containing settings, context, sources and drafts.")
    args = parser.parse_args(argv)
    if args.mode == "no-rag" and args.metadata_filter is not None:
        parser.error("--metadata-filter requires rag or both mode.")
    retriever = None
    try:
        email = IncomingEmail.model_validate(json.loads(args.email_file.read_text(encoding="utf-8-sig")))
        metadata_filter = json.loads(args.metadata_filter) if args.metadata_filter is not None else None
        if metadata_filter is not None and not isinstance(metadata_filter, dict):
            raise ValueError("--metadata-filter must decode to a JSON object.")
        generator = EmailReplyGenerator(base_url=args.base_url)
        results = []
        print("Incoming email:", email.model_dump_json(), flush=True)
        print("Generation settings:", GENERATION_SETTINGS, flush=True)
        modes = ("no-rag", "rag") if args.mode == "both" else (args.mode,)
        for mode in modes:
            if mode == "rag":
                # Do not silently create a new/empty index when the path is wrong.
                if not (args.persist_dir / "chroma.sqlite3").is_file():
                    raise ValueError("Existing Chroma index not found. Build history separately with python -m evaluation.retrieval --build.")
                from rag.email_retriever import EmailRetriever

                retriever = EmailRetriever(persist_directory=args.persist_dir, base_url=args.base_url)
                generator.retriever = retriever
            print(f"\nGenerating {mode} draft...", flush=True)
            result = generator.generate(email, use_retrieval=mode == "rag", metadata_filter=metadata_filter)
            results.append(result)
            print_result(result)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps({
                "generation_settings": GENERATION_SETTINGS, "results": results,
            }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print("Saved:", args.output)
    except (ValueError, RuntimeError, OSError, HTTPError, ResponseError) as exc:
        parser.exit(1, f"Reply generation failed: {exc}\n")
    finally:
        if retriever is not None:
            retriever.close()


if __name__ == "__main__":
    main()
