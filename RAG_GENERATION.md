# Suggested reply generation MVP

This is independent of email classification. It drafts replies for human review;
it never sends email, calls Gmail, or changes the historical index.

## Run from the project root (PowerShell)

The existing dependencies in requirements.txt are sufficient. Ollama must serve
qwen3:8b. RAG additionally requires nomic-embed-text and the existing Chroma index.
No model is automatically downloaded and no index is automatically rebuilt.

```powershell
# Same input, prompt and generation settings; only history differs:
.\.venv\Scripts\python.exe generate_reply.py --email-file examples/incoming_trip.json --mode both --output results/generation_mvp/comparison.json

# Individual paths:
.\.venv\Scripts\python.exe generate_reply.py --email-file examples/incoming_trip.json --mode no-rag
.\.venv\Scripts\python.exe generate_reply.py --email-file examples/incoming_trip.json --mode rag

# Offline tests (no real Ollama generation):
.\.venv\Scripts\python.exe -B -m unittest test_reply_generator test_retriever_unit test_evaluation -v
```

Input JSON contains nonblank string fields subject, sender and body; metadata is
an optional object. The example is a synthetic historical scenario, not a live
family appointment or an additional evaluation benchmark.

An explicitly supplied metadata.thread_id must already be known from the
incoming transport and match the index's thread namespace. It is not extracted
from text. Otherwise retrieval is unfiltered. A caller can override it with a
native Chroma filter using --metadata-filter or the Python API. PowerShell example:

```powershell
.\.venv\Scripts\python.exe generate_reply.py --email-file examples/incoming_trip.json --mode rag --metadata-filter '{ "sender": "eli@family.example" }'
```

## Execution flow

1. Validate IncomingEmail before making any model calls.
2. In no-rag mode skip retrieval entirely and supply [] as history.
3. In rag mode call the unchanged EmailRetriever.search_email with top-k=3.
4. Build ranked JSON context containing source IDs, cosine distances, selected
   metadata and the actual email text. Lower distance means greater similarity.
5. Limit history to 6000 serialized characters and each source text to 1800
   characters. Truncation is flagged; source IDs distinguish retrieved from
   actually included emails. These are character limits, not exact token counts.
6. Insert incoming email JSON and history JSON into separate labeled sections of
   the human message. Keep the generation system instructions identical for both
   modes. Transport metadata controls retrieval and is not generation instructions.
7. Call ChatOllama(model=qwen3:8b, temperature=0, reasoning=False, num_predict=512).
   These settings belong only to generation; classification is untouched.
8. Print source records, exact supplied history context and suggested reply.
   --output saves the comparison to UTF-8 JSON. No automatic persistence otherwise.

## Limitations

- Prompt rules discourage unsupported facts and treat email text as untrusted
  reference data. They are not a guarantee against hallucination or prompt injection.
- Empty filtered results produce empty context; they do not silently remove the
  requested filter. Retrieval errors are surfaced instead of silently hidden.
- Existing semantic search can return irrelevant history; there is no new
  threshold, reranker, thread inference, metadata extraction or freshness logic.
- A history date is not evidence that an old arrangement is still current.
- Finite context and output limits may omit useful information; the CLI surfaces
  empty/incomplete generation as errors. Human review remains necessary.
- A single paired example demonstrates the end-to-end path, not a measured
  improvement in overall generation quality. Next evaluation should include
  unrelated history, empty results, conflicting dates, unanswered decisions and
  adversarial text, with human judgments of factual support and appropriateness.
