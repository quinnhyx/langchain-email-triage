# langchain-email-triage

Local email classification, historical retrieval, suggested-reply generation,
and separate evaluation tools using LangChain, Ollama and Chroma.
Replies are drafts for human review; nothing is automatically sent.

## Project structure

```text
langchain-email-triage/
├── email_triage.py                  # Existing classification API and prompt
├── rag/
│   ├── __init__.py
│   ├── email_retriever.py           # Persistent retrieval and metadata filters
│   ├── reply_generator.py           # Independent RAG/no-RAG reply generation
│   ├── generate_reply.py            # Reply CLI
│   ├── historical_emails.py         # 26 synthetic emails and 8 retrieval queries
│   └── chroma_db/                   # Existing local index; gitignored
├── evaluation/
│   ├── __init__.py
│   ├── classification_cases.py      # Frozen 45-email classification benchmark
│   ├── triage.py                    # Classification evaluation and prediction cache
│   ├── retrieval.py                 # Retrieval CLI, metrics and mode comparison
│   ├── generation.py                # Paired generation evaluation and reporting
│   ├── generation_metrics.py        # Deterministic diagnostics
│   └── generation_cases.json        # 14 generation evaluation cases
├── tests/
│   ├── __init__.py
│   ├── test_evaluation.py
│   ├── test_generation_evaluation.py
│   ├── test_reply_generator.py
│   └── test_retriever_unit.py
├── docs/
│   ├── RAG_GENERATION.md
│   └── GENERATION_EVALUATION.md
├── examples/
│   └── incoming_trip.json
├── results/                        # Local generated outputs; gitignored
├── requirements.txt
└── .gitignore
```

Evaluation datasets are reference fixtures, not executable tests or training
examples. Evaluation expectations never enter the reply-generation prompt.

## Setup

Run all commands from the repository root. No manual PYTHONPATH is needed.
The commands below use PowerShell and the project's virtual environment.
On other platforms, use your environment's Python executable.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama list
# Install only if missing; downloads are explicit:
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

Ollama must be running at http://localhost:11434. Offline tests use mocks and
deterministic vectors, so they do not require the Ollama service or models.

## Classification

The existing Python API is unchanged:

```python
from email_triage import EmailTriage

result = EmailTriage().analyze(
    subject="A time to talk",
    body="Could you send your availability for our internship interview?",
)
print(result.model_dump_json(indent=2))
```

Evaluate the fixed quick subset or the full benchmark:

```powershell
.\.venv\Scripts\python.exe -m evaluation.triage --quick
.\.venv\Scripts\python.exe -m evaluation.triage --full
# Explicit cache reuse: no Ollama inference
.\.venv\Scripts\python.exe -m evaluation.triage --quick --use-cache
```

Without --use-cache, evaluation calls the local model and writes mode-specific
predictions under results/. Full mode is the existing default and can be slow.

## Retrieval

For a fresh checkout only, build the synthetic history index explicitly.
If you already have an index, reuse it; restructuring does not require a rebuild.
`--build` synchronizes the complete supplied history snapshot, including removals.

```powershell
# First-time setup only:
.\.venv\Scripts\python.exe -m evaluation.retrieval --build
# Reuse existing index:
.\.venv\Scripts\python.exe -m evaluation.retrieval --query "Following up on our previous internship interview"
.\.venv\Scripts\python.exe -m evaluation.retrieval --evaluate --mode all
```

Distances are cosine distances: lower means closer. The comparison distinguishes
baseline, oracle filtering, and realistic filtering. Query-only fixtures have no
incoming envelope metadata, so realistic evaluation defaults to unfiltered search.
The existing --mode/--incoming-metadata-file switches apply to evaluation, not
to the standalone --query operation.

## Suggested replies

```powershell
.\.venv\Scripts\python.exe -m rag.generate_reply --email-file examples/incoming_trip.json --mode no-rag
.\.venv\Scripts\python.exe -m rag.generate_reply --email-file examples/incoming_trip.json --mode rag
.\.venv\Scripts\python.exe -m rag.generate_reply --email-file examples/incoming_trip.json --mode both --output results/generation_mvp/comparison.json
```

Both modes use the same generation settings. RAG additionally requires the
existing index and embedding model. See [generation details](docs/RAG_GENERATION.md).

## Generation evaluation

```powershell
.\.venv\Scripts\python.exe -m evaluation.generation
```

This runs 14 cases in both modes, making 28 real generation calls. It creates a
new timestamp/UUID directory under results/generation_evaluation/, preserving
previous runs. It never rebuilds the index. See the
[methodology and human-review rubric](docs/GENERATION_EVALUATION.md).

## Offline tests and CLI help

```powershell
# Standard discovery from the repository root (41 tests):
.\.venv\Scripts\python.exe -B -m unittest discover -v
# Equivalent explicit test directory, keeping package-qualified imports:
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -t . -v
# Non-inference CLI checks:
.\.venv\Scripts\python.exe -m evaluation.triage --help
.\.venv\Scripts\python.exe -m evaluation.retrieval --help
.\.venv\Scripts\python.exe -m rag.generate_reply --help
.\.venv\Scripts\python.exe -m evaluation.generation --help
```

The old root-level evaluation scripts now live in evaluation/; the reply CLI
now lives in rag/. Use these module commands rather than executing nested files
by path. Tests live only in tests/, while benchmark data stays in evaluation/.

Local .env files, virtual environments, Python caches, Chroma storage and results/
remain gitignored. Existing local data and previous experiment reports are retained.
