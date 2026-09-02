"""Semantic search over source-verified, published assembly statements."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from langchain_core.documents import Document

from assembly_record_store import canonical_dataset_hash
from assembly_records import load_dataset


DEFAULT_EMBEDDING_MODEL = "models/gemini-embedding-001"
DEFAULT_LIMIT = 8
MAX_LIMIT = 20


class SemanticSearchConfigurationError(RuntimeError):
    """Raised when the vector-search provider is not configured."""


@dataclass(frozen=True)
class _CachedStore:
    dataset_version: str
    store: Any


_cache_lock = threading.Lock()
_cached_store: Optional[_CachedStore] = None


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def build_search_documents(dataset: Dict[str, Any]) -> List[Document]:
    """Create one searchable document per published statement with stable IDs."""
    documents: List[Document] = []
    for assembly_id, assembly in dataset.get("assemblies", {}).items():
        assembly_name = _clean_text(assembly.get("assembly_name"))
        for record in assembly.get("records", []):
            if record.get("publication_status") != "published":
                continue
            issue_id = _clean_text(record.get("discussion_id"))
            source_url = _clean_text(record.get("source_url"))
            if not issue_id or not source_url:
                continue
            for statement in record.get("statements", []):
                statement_id = _clean_text(statement.get("statement_id"))
                if not statement_id:
                    continue
                summary = _clean_text(statement.get("summary_quote"))
                full_summary = _clean_text(statement.get("full_summary"))
                source_excerpt = _clean_text(statement.get("source_excerpt"))
                searchable_parts = [
                    _clean_text(record.get("topic")),
                    _clean_text(record.get("what_changes")),
                    summary,
                    full_summary,
                    source_excerpt,
                ]
                page_content = "\n".join(part for part in searchable_parts if part)
                if not page_content:
                    continue
                documents.append(Document(
                    page_content=page_content,
                    metadata={
                        "document_id": f"{issue_id}:{statement_id}",
                        "issue_id": issue_id,
                        "statement_id": statement_id,
                        "assembly_id": str(assembly_id),
                        "assembly_name": assembly_name,
                        "title": _clean_text(record.get("topic")),
                        "meeting_name": _clean_text(record.get("meeting_name")),
                        "meeting_date": _clean_text(record.get("meeting_date")),
                        "speaker_name": _clean_text(statement.get("speaker_name")),
                        "speaker_role": _clean_text(statement.get("speaker_role")),
                        "summary": summary or full_summary or source_excerpt,
                        "source_excerpt": source_excerpt,
                        "source_url": source_url,
                    },
                ))
    return documents


def _embedding_api_key() -> str:
    return (
        os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_API_KEY", "").strip()
    )


def _create_vector_store(documents: Sequence[Document], dataset_version: str) -> Any:
    api_key = _embedding_api_key()
    if not api_key:
        raise SemanticSearchConfigurationError(
            "GEMINI_API_KEY or GOOGLE_API_KEY is required for semantic search"
        )

    # Imported lazily so the rest of the API can boot even when the optional
    # vector-search runtime is unavailable or still being provisioned.
    from langchain_community.vectorstores import Chroma
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    embeddings = GoogleGenerativeAIEmbeddings(
        model=os.getenv("SEMANTIC_SEARCH_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
        google_api_key=api_key,
    )
    persist_directory = os.getenv("CHROMA_PERSIST_DIRECTORY", "").strip() or None
    store = Chroma(
        collection_name=f"gijiraku_{dataset_version[:20]}",
        embedding_function=embeddings,
        persist_directory=persist_directory,
        collection_metadata={"hnsw:space": "cosine"},
    )
    if documents:
        store.add_documents(
            documents=list(documents),
            ids=[str(document.metadata["document_id"]) for document in documents],
        )
    return store


def _get_vector_store(dataset: Dict[str, Any]) -> Any:
    global _cached_store
    dataset_version = canonical_dataset_hash(dataset)
    with _cache_lock:
        if _cached_store and _cached_store.dataset_version == dataset_version:
            return _cached_store.store
        documents = build_search_documents(dataset)
        store = _create_vector_store(documents, dataset_version)
        _cached_store = _CachedStore(dataset_version=dataset_version, store=store)
        return store


def clear_semantic_search_cache() -> None:
    global _cached_store
    with _cache_lock:
        _cached_store = None


def semantic_search(
    query: str,
    *,
    assembly_id: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
    dataset: Optional[Dict[str, Any]] = None,
    vector_store: Any = None,
) -> Dict[str, Any]:
    normalized_query = _clean_text(query)
    if len(normalized_query) < 2:
        raise ValueError("query must contain at least 2 characters")
    if len(normalized_query) > 200:
        raise ValueError("query must contain at most 200 characters")
    if limit < 1 or limit > MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")

    active_dataset = dataset or load_dataset()
    store = vector_store or _get_vector_store(active_dataset)
    search_filter = {"assembly_id": assembly_id} if assembly_id else None
    matches = store.similarity_search_with_relevance_scores(
        normalized_query,
        k=limit,
        filter=search_filter,
    )

    results = []
    seen_document_ids = set()
    for document, raw_score in matches:
        metadata = document.metadata
        document_id = str(metadata.get("document_id", ""))
        if not document_id or document_id in seen_document_ids:
            continue
        seen_document_ids.add(document_id)
        score = max(0.0, min(1.0, float(raw_score)))
        results.append({
            "issue_id": str(metadata.get("issue_id", "")),
            "statement_id": str(metadata.get("statement_id", "")),
            "assembly_id": str(metadata.get("assembly_id", "")),
            "assembly_name": str(metadata.get("assembly_name", "")),
            "title": str(metadata.get("title", "")),
            "meeting_name": str(metadata.get("meeting_name", "")),
            "meeting_date": str(metadata.get("meeting_date", "")),
            "speaker_name": str(metadata.get("speaker_name", "")),
            "speaker_role": str(metadata.get("speaker_role", "")),
            "summary": str(metadata.get("summary", "")),
            "source_excerpt": str(metadata.get("source_excerpt", "")),
            "source_url": str(metadata.get("source_url", "")),
            "relevance_score": round(score, 4),
        })

    return {
        "query": normalized_query,
        "assembly_id": assembly_id,
        "result_count": len(results),
        "results": results,
    }
