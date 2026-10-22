"""Local, persistent semantic retrieval of historical emails, without generation."""

import hashlib
import json
from datetime import date
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_ollama import OllamaEmbeddings


DEFAULT_INDEX_DIR = Path(__file__).resolve().parent / "chroma_db"
DEFAULT_MODEL = "nomic-embed-text"
EMAIL_FIELDS = ("id", "thread_id", "sender", "recipient", "subject", "body", "date")


def check_embedding_model(model: str, base_url: str) -> str:
    """Return the installed model digest; never download a missing model."""
    try:
        with urlopen(base_url.rstrip("/") + "/api/tags", timeout=5) as response:
            models = json.load(response)["models"]
    except (URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
        raise RuntimeError(f"Cannot check Ollama at {base_url}. Start Ollama first.") from exc
    accepted = {model, model + ":latest"} if ":" not in model else {model}
    for installed in models:
        if installed.get("name") in accepted or installed.get("model") in accepted:
            digest = installed.get("digest")
            if not digest:
                raise RuntimeError("Ollama did not return an embedding model digest.")
            return digest
    raise RuntimeError(
        f"Embedding model {model!r} is not installed. Run: ollama pull {model}. "
        "No model was downloaded automatically."
    )


class EmailRetriever:
    def __init__(
        self,
        persist_directory: str | Path = DEFAULT_INDEX_DIR,
        model_name: str = DEFAULT_MODEL,
        base_url: str = "http://localhost:11434",
        collection_name: str = "historical_emails",
        *,
        embeddings: Embeddings | None = None,
    ):
        """Open a persistent collection, checking its embedding identity.

        The optional embeddings argument is an offline-test hook. Normal use
        always uses the installed Ollama model for both indexing and queries.
        """
        if embeddings is None:
            identity = check_embedding_model(model_name, base_url)
            embeddings = OllamaEmbeddings(model=model_name, base_url=base_url)
        else:
            identity = f"injected:{type(embeddings).__module__}.{type(embeddings).__qualname__}"
        self.embeddings = embeddings
        self.persist_directory = Path(persist_directory)
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False),
        )
        signature = {
            "embedding_model": model_name,
            "embedding_identity": identity,
            "text_format_version": 1,
            "distance_metric": "cosine",
        }
        existing_names = [collection.name for collection in self.client.list_collections()]
        if collection_name in existing_names:
            stored = self.client.get_collection(collection_name, embedding_function=None).metadata or {}
            if any(stored.get(key) != value for key, value in signature.items()):
                self.client.close()
                raise ValueError(
                    "Index embedding model/weights or text format differs. "
                    "Use a new --persist-dir to build a separate compatible index."
                )
        self.vector_store = Chroma(
            client=self.client,
            collection_name=collection_name,
            embedding_function=self.embeddings,
            collection_metadata=signature,
            collection_configuration={"hnsw": {"space": "cosine"}},
        )

    @staticmethod
    def to_documents(emails: list[dict]) -> list[Document]:
        """One whole short email per Document; all required fields are preserved."""
        documents = []
        seen = set()
        for email in emails:
            if any(not isinstance(email.get(field), str) or not email[field].strip()
                   for field in EMAIL_FIELDS):
                raise ValueError("Historical emails need nonempty string fields: " + ", ".join(EMAIL_FIELDS))
            if email["id"] in seen:
                raise ValueError(f"Duplicate historical email ID: {email['id']}")
            seen.add(email["id"])
            date.fromisoformat(email["date"])
            content = (
                f"Subject: {email['subject']}\n"
                f"From: {email['sender']}\nTo: {email['recipient']}\n"
                f"Date: {email['date']}\n\n{email['body']}"
            )
            metadata = {field: email[field] for field in EMAIL_FIELDS if field != "body"}
            fingerprint = json.dumps(email, sort_keys=True, ensure_ascii=False)
            metadata["content_sha256"] = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
            documents.append(Document(id=email["id"], page_content=content, metadata=metadata))
        return documents

    def index(self, emails: list[dict]) -> dict[str, int]:
        """Synchronize this collection to the complete supplied history snapshot.

        Embed only new/changed records; stable IDs upsert instead of duplicating.
        Records absent from the supplied snapshot are removed after successful
        upsert, so callers must supply the full desired history, not a partial batch.
        """
        documents = self.to_documents(emails)
        stored = self.vector_store.get(include=["metadatas"])
        hashes = {
            email_id: metadata.get("content_sha256")
            for email_id, metadata in zip(stored["ids"], stored["metadatas"])
        }
        changed = [doc for doc in documents
                   if hashes.get(doc.id) != doc.metadata["content_sha256"]]
        if changed:
            self.vector_store.add_documents(changed, ids=[doc.id for doc in changed])
        wanted = {doc.id for doc in documents}
        removed = set(hashes) - wanted
        if removed:
            self.vector_store.delete(ids=sorted(removed))
        return {
            "embedded": len(changed),
            "skipped": len(documents) - len(changed),
            "removed": len(removed),
            "total": len(documents),
        }

    def search(
        self, query: str, k: int = 3, metadata_filter: dict | None = None
    ) -> list[tuple[Document, float]]:
        """Return top-k (Document, cosine distance) pairs; LOWER is closer.

        Optional filters use Chroma's native where syntax, e.g.
        {"thread_id": "aster-intern-2026"} or {"date": "2026-09-18"}.
        Date metadata remains an ISO string; numeric range operators are not
        a date-range API. No filtering, extraction, or reindexing is automatic.
        """
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Search query must be a nonempty string.")
        if type(k) is not int or k < 1:
            raise ValueError("k must be a positive integer.")
        count = len(self.vector_store.get(include=[])["ids"])
        if count == 0:
            raise ValueError("Index is empty. Build it with --build first.")
        if metadata_filter is None:
            return self.vector_store.similarity_search_with_score(query, k=min(k, count))
        return self.vector_store.similarity_search_with_score(
            query, k=min(k, count), filter=metadata_filter
        )

    def search_email(
        self, subject: str, body: str, k: int = 3, metadata_filter: dict | None = None
    ) -> list[tuple[Document, float]]:
        """Retrieve history from a new email's subject and body, without classifying it."""
        if not subject.strip() or not body.strip():
            raise ValueError("New email subject/body must not be empty.")
        return self.search(f"Subject: {subject}\n\n{body}", k=k, metadata_filter=metadata_filter)

    def close(self) -> None:
        """Release local database handles (especially useful on Windows)."""
        self.client.close()
