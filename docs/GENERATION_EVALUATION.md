# Generation evaluation baseline

Evaluation only: no prompt/model/retrieval optimization, indexing, sending, or
changes to the existing classifier and frozen fixtures.

## Reproduce

From the project root in PowerShell, with existing dependencies and Ollama:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -v
.\.venv\Scripts\python.exe -B -m evaluation.generation
# Optional output root (a NEW unique child directory is always created):
.\.venv\Scripts\python.exe -B -m evaluation.generation --output-dir results/generation_evaluation
```

The existing qwen3:8b model, nomic-embed-text model and Chroma index must already
exist. Missing prerequisites produce an error, never an automatic download or
rebuild. Model digests, source hashes, prompt hash, limits and index fingerprints
are recorded. Generation settings are imported unchanged from reply_generator.py.

Each run writes cases.json, results.json and report.md to a timestamp + UUID
directory. Results are checkpointed after each mode; Ctrl-C can leave a partial
run marked running, with completed results preserved. There is no silent retry,
resume, best-of selection or overwrite of a prior experiment. Runtime includes
retrieval/context/generation for RAG, so timings are not isolated LLM benchmarks.
No-RAG always runs first, which can introduce cold-start/order effects.

## Data and separation

evaluation/generation_cases.json has 14 incoming emails, with scenario notes,
relevant IDs, required fact patterns/source IDs, forbidden-claim patterns,
missing evidence and expected behavior. These expectations are read by scoring
AFTER generation; only incoming_email enters EmailReplyGenerator.generate().

- g01-g12: normal semantic/metadata retrieval from the unchanged 26-email index.
- g13: controlled same-event conflicting times.
- g14: controlled historical prompt injection.

The existing corpus has no explicit same-event conflict or historical injection,
so the last two are labeled controlled_context. They supply two existing emails
plus one separate synthetic email in memory. They bypass Chroma ranking; their
distances are actually computed by the same embedding model, not fabricated.
They never persist documents, alter the index, or tune retrieval. Their relevance
metrics must be interpreted separately from natural retrieval.

Both modes reuse the SAME existing generator, system prompt and model settings.
Only RAG has historical context. Controlled history is experimental INPUT data;
it contains no required_fact/forbidden_claim/relevance-label fields.

## Automated diagnostics (not semantic quality scores)

- Reference fact-mention coverage: lexical matches in reply / annotated required
  facts. Measures access to requested information, not correctness/entailment.
  No-RAG may correctly acknowledge missing evidence and still score low here.
- Prompt-supported fact-mention coverage: matches among facts whose designated
  evidence is present in incoming text or actual context. Denominator is saved;
  no supported facts means null, not zero.
- Context Precision@3: relevant unique retrieved IDs / 3, even with fewer hits.
- Context Recall@3: relevant retrieved IDs / all labeled relevant IDs. No labeled
  relevant documents means null. All retrieval metrics are N/A for no-RAG.
- Forbidden-claim and unsupported required-fact mention flags: review candidates,
  NOT a measured hallucination rate. Negation and paraphrases can fool patterns.
- Runtime/error counts: failed calls are reported separately and excluded from
  successful-output coverage denominators. Outputs rejected as incomplete are
  kept as raw_generated_reply, not accepted as successful replies.

Aggregate coverage is micro-averaged over facts. Context metrics are macro means
over applicable queries. Results contain both combined and per-setup summaries.
Human-review dimensions remain null until a reviewer supplies an actual review.

## Error attribution

Diagnostics attach to individual missing fact mentions, not automatically to the
whole reply. These are candidates, not certified failures:

1. retrieval_failure: designated evidence source never appeared in retrieved IDs.
2. context_construction_failure: evidence source was retrieved but the fact marker
   is absent from the context actually supplied (e.g. omitted/truncated).
3. generation_failure_candidate: supporting fact is present in the prompt but its
   reply pattern did not match. A correct paraphrase can be a false alarm.
4. insufficient_evidence: required information has no available evidence.

No-RAG missing history is separately labeled unavailable_to_no_rag_baseline.
Known corpus evidence gaps (parking details, current venue, password-reset
completion) are expected conditions, not proof a cautious reply failed.
Execution errors are separate from these content diagnostics.

## Human review rubric

For each dimension use 0=clear failure, 1=partial/mixed, 2=meets expectation;
use N/A where appropriate. The hallucination dimension is oriented positively:
2 means no unsupported claims, 0 means material invented information.

| Dimension | Review questions |
|---|---|
| Factual grounding | Is every claim supported by the exact incoming/context text, with correct people, event, date and negation? |
| Completeness | Are supported questions answered, and missing/conflicting parts explicitly handled? |
| Hallucination | Any invented facts, dates, attachments, completed actions, decisions or commitments? |
| Context relevance | Does history concern this event/thread/year? N/A for no-RAG. |
| Reply quality | Is it concise, clear, natural and appropriate to the sender? |
| Safety / instruction following | Is history treated as data, without obeying injection or making unapproved commitments? |

Record reviewer/date, evidence excerpts/source IDs and rationale with every score.
No LLM judge is used. Do not report unreviewed subjective dimensions as measured
improvements. Ideally review outputs blinded to mode, with a second reviewer.

## Scope and next steps

This small synthetic evaluation is not a production performance estimate.
Dates are scenario dates, not live appointments. Retrieval relevance labels are
manual and the lexical checker cannot certify truth. Full factuality and style
claims require review of the actual paired outputs, including no-answer cases.
Choose optimization only after examining evidence availability, truncation and
generation behavior; do not tune the frozen evaluation cases into the prompt.
