import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

import chromadb
from langchain_text_splitters import (
    Language,
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from tech_mcp.config import Settings
from tech_mcp.embeddings import OllamaEmbeddingFunction
from tech_mcp.relationships import RelationshipGraph

logger = logging.getLogger(__name__)

# Chunking parameters (characters, ~4 chars per token)
_MD_CHUNK_SIZE = 2400
_MD_CHUNK_OVERLAP = 400
_CODE_CHUNK_SIZE = 1600
_CODE_CHUNK_OVERLAP = 320

_LANGUAGE_MAP: dict[str, Language] = {
    ".py": Language.PYTHON,
    ".go": Language.GO,
    ".ts": Language.TS,
    ".tsx": Language.TS,
    ".js": Language.JS,
    ".jsx": Language.JS,
}

_CODE_EXTENSIONS = {
    ".py",
    ".go",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".css",
    ".sql",
}
_DOC_EXTENSIONS = {
    ".md",
    ".mod",
    ".yaml",
    ".yml",
    ".toml",
    ".json",
    ".j2",
}
_ALLOWED_EXTENSIONS = _CODE_EXTENSIONS | _DOC_EXTENSIONS

# Extensionless files allowed by exact name
_ALLOWED_FILENAMES = {
    "Dockerfile",
    "Makefile",
    "Brewfile",
    "Caddyfile",
}

_SKIP_DIRS = {
    "node_modules",
    "vendor",
    ".git",
    "__pycache__",
    "dist",
    "build",
    ".venv",
}

# Markdown header splitter — splits by heading hierarchy
_MD_HEADERS = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
]


def _is_allowed_file(path: Path) -> bool:
    """Check if a file has an allowed extension or filename."""
    return (
        path.suffix.lower() in _ALLOWED_EXTENSIONS
        or path.name in _ALLOWED_FILENAMES
    )


class Ingestion:
    """Handles chunking, embedding, and storage of content."""

    def __init__(
        self,
        settings: Settings,
        graph: RelationshipGraph,
        embedding_fn: OllamaEmbeddingFunction,
    ) -> None:
        self._settings = settings
        self._graph = graph
        self._embedding_fn = embedding_fn
        self._client: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None

    @property
    def client(self) -> chromadb.ClientAPI:
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=self._settings.chroma_persist_dir,
                settings=chromadb.Settings(anonymized_telemetry=False),
            )
        return self._client

    @property
    def collection(self) -> chromadb.Collection:
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name="knowledge_base",
                embedding_function=self._embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def ingest_session(
        self,
        problem: str,
        attempts: list[dict[str, str]],
        root_cause: str,
        solution: str,
        repos: list[str],
        tags: list[str] | None = None,
    ) -> str:
        """Ingest a debugging session. Returns the ingest_session_id."""
        # Validate repos
        for repo in repos:
            self._graph.validate_repo(repo)

        session_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        tag_str = ",".join(tags) if tags else ""
        repo_str = ",".join(repos)
        primary_repo = repos[0]

        # Format into session template
        attempts_text = ""
        for i, attempt in enumerate(attempts, 1):
            action = attempt.get("action", "")
            outcome = attempt.get("outcome", "")
            why_failed = attempt.get("why_failed", "")
            attempts_text += (
                f"{i}. **Action:** {action}\n"
                f"   **Outcome:** {outcome}\n"
                f"   **Why it failed:** {why_failed}\n\n"
            )

        document = (
            f"# Session: {problem}\n\n"
            f"**Repos:** {repo_str}\n"
            f"**Date:** {now[:10]}\n"
            f"**Tags:** {tag_str}\n\n"
            f"## Problem\n\n{problem}\n\n"
            f"## What Was Tried\n\n{attempts_text}"
            f"## Root Cause\n\n{root_cause}\n\n"
            f"## Solution\n\n{solution}\n\n"
            f"## Key Signals\n\n"
            f"What to look for next time this pattern appears.\n"
        )

        # Chunk with markdown splitter
        chunks = self._chunk_markdown(document)
        total = len(chunks)

        # Build metadata and store
        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"session:{session_id}:{i}"
            ids.append(chunk_id)
            documents.append(chunk["text"])
            metadatas.append(
                {
                    "source": "session",
                    "repo": primary_repo,
                    "repo_type": self._graph.get_repo_type(primary_repo),
                    "related_repos": repo_str,
                    "file_path": "",
                    "heading_context": chunk.get("heading_context", ""),
                    "modified_at": now,
                    "ingested_at": now,
                    "ingest_session_id": session_id,
                    "chunk_index": i,
                    "total_chunks": total,
                    "tags": tag_str,
                    "generated": "false",
                    "mcp_server": "",
                }
            )

        self._add_to_collection(ids, documents, metadatas)
        logger.info(
            "Ingested session '%s' → %d chunks (id: %s)",
            problem[:50],
            total,
            session_id,
        )
        return session_id

    def ingest_file(
        self,
        path: str,
        repo_name: str,
        related_repos: list[str] | None = None,
    ) -> tuple[int, str]:
        """Ingest a single file. Returns (chunk_count, ingest_session_id)."""
        self._graph.validate_repo(repo_name)
        file_path = Path(path)

        if not file_path.exists() or not file_path.is_file():
            msg = f"File not found or not readable: {path}"
            raise FileNotFoundError(msg)

        if file_path.stat().st_size == 0:
            msg = f"File is empty: {path}"
            raise ValueError(msg)

        if not _is_allowed_file(file_path):
            suffix = file_path.suffix.lower()
            msg = (
                f"File '{file_path.name}' not allowed "
                f"(extension '{suffix}' not in "
                f"{sorted(_ALLOWED_EXTENSIONS)}, "
                f"name not in {sorted(_ALLOWED_FILENAMES)})"
            )
            raise ValueError(msg)

        if file_path.stat().st_size > 50 * 1024:
            logger.warning(
                "File %s is >50KB (%d bytes) — may chunk poorly",
                path,
                file_path.stat().st_size,
            )

        content = file_path.read_text(errors="replace")
        modified_at = datetime.fromtimestamp(
            file_path.stat().st_mtime, tz=UTC
        ).isoformat()

        return self._ingest_content(
            content=content,
            file_path=str(file_path),
            repo_name=repo_name,
            suffix=file_path.suffix.lower(),
            related_repos=related_repos,
            modified_at=modified_at,
        )

    def _ingest_content(
        self,
        content: str,
        file_path: str,
        repo_name: str,
        suffix: str,
        related_repos: list[str] | None = None,
        modified_at: str | None = None,
    ) -> tuple[int, str]:
        """Shared ingestion logic for file and content-based ingestion."""
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        related_str = ",".join(related_repos) if related_repos else ""
        if modified_at is None:
            modified_at = now

        # Deduplicate: delete existing chunks for this file + repo
        self._delete_file_chunks(file_path, repo_name)

        # Choose chunking strategy
        source_type = "code" if suffix in _CODE_EXTENSIONS else "doc"
        if suffix == ".md":
            chunks = self._chunk_markdown(content)
        elif suffix in _LANGUAGE_MAP:
            chunks = self._chunk_code(content, _LANGUAGE_MAP[suffix])
        elif suffix in _CODE_EXTENSIONS:
            chunks = self._chunk_code(content)
        else:
            chunks = self._chunk_generic(content)

        total = len(chunks)

        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{repo_name}:{file_path}:{i}"
            ids.append(chunk_id)
            documents.append(chunk["text"])
            metadatas.append(
                {
                    "source": source_type,
                    "repo": repo_name,
                    "repo_type": self._graph.get_repo_type(repo_name),
                    "related_repos": related_str,
                    "file_path": file_path,
                    "heading_context": chunk.get("heading_context", ""),
                    "modified_at": modified_at,
                    "ingested_at": now,
                    "ingest_session_id": session_id,
                    "chunk_index": i,
                    "total_chunks": total,
                    "tags": "",
                    "generated": "false",
                    "mcp_server": "",
                }
            )

        if documents:
            self._add_to_collection(ids, documents, metadatas)

        logger.info("Ingested file %s (%s) → %d chunks", file_path, repo_name, total)
        return total, session_id

    def ingest_directory(
        self,
        path: str,
        repo_name: str,
        related_repos: list[str] | None = None,
        extensions: list[str] | None = None,
    ) -> dict:
        """Ingest a directory. Returns summary dict."""
        self._graph.validate_repo(repo_name)
        dir_path = Path(path)

        if not dir_path.exists() or not dir_path.is_dir():
            msg = f"Directory not found: {path}"
            raise FileNotFoundError(msg)

        allowed_ext = set(extensions) if extensions else _ALLOWED_EXTENSIONS

        session_id = str(uuid.uuid4())
        files_found = 0
        files_ingested = 0
        total_chunks = 0

        for file_path in sorted(dir_path.rglob("*")):
            if not file_path.is_file():
                continue

            # Skip ignored directories
            parts = file_path.relative_to(dir_path).parts
            if any(part in _SKIP_DIRS for part in parts):
                continue

            ext_ok = file_path.suffix.lower() in allowed_ext
            name_ok = file_path.name in _ALLOWED_FILENAMES
            if not ext_ok and not name_ok:
                continue

            files_found += 1

            try:
                count, _ = self.ingest_file(str(file_path), repo_name, related_repos)
                files_ingested += 1
                total_chunks += count
            except Exception:
                logger.exception("Failed to ingest %s", file_path)

        summary = {
            "ingest_session_id": session_id,
            "files_found": files_found,
            "files_ingested": files_ingested,
            "chunks_created": total_chunks,
        }
        logger.info("Directory ingestion complete: %s", summary)
        return summary

    def delete_by_session(self, session_id: str) -> int:
        """Delete all chunks for an ingest_session_id. Returns count."""
        results = self.collection.get(
            where={"ingest_session_id": session_id},
        )
        count = len(results["ids"])
        if count > 0:
            self.collection.delete(ids=results["ids"])
        return count

    def delete_by_file(self, path: str, repo_name: str) -> int:
        """Delete all chunks for a specific file + repo."""
        return self._delete_file_chunks(path, repo_name)

    def delete_by_repo(self, repo_name: str) -> int:
        """Delete all chunks for a repo."""
        results = self.collection.get(
            where={"repo": repo_name},
        )
        count = len(results["ids"])
        if count > 0:
            self.collection.delete(ids=results["ids"])
        return count

    def list_recent_ingestions(self, limit: int = 20) -> list[dict]:
        """List recent ingestion sessions."""
        results = self.collection.get(
            include=["metadatas"],
        )
        # Group by ingest_session_id
        sessions: dict[str, dict] = {}
        for meta in results["metadatas"]:
            sid = meta["ingest_session_id"]
            if sid not in sessions:
                sessions[sid] = {
                    "ingest_session_id": sid,
                    "source": meta["source"],
                    "repo": meta["repo"],
                    "ingested_at": meta["ingested_at"],
                    "chunk_count": 0,
                }
            sessions[sid]["chunk_count"] += 1

        # Sort by ingested_at descending, limit
        sorted_sessions = sorted(
            sessions.values(),
            key=lambda s: s["ingested_at"],
            reverse=True,
        )
        return sorted_sessions[:limit]

    def get_stats(self) -> dict:
        """Get chunk counts grouped by repo and source type."""
        results = self.collection.get(include=["metadatas"])
        stats: dict[str, dict[str, int]] = {}
        for meta in results["metadatas"]:
            repo = meta["repo"]
            source = meta["source"]
            if repo not in stats:
                stats[repo] = {}
            stats[repo][source] = stats[repo].get(source, 0) + 1
        return stats

    # ── Private helpers ──────────────────────────────────────────────

    def _add_to_collection(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """Add documents to the collection in batches."""
        batch_size = self._settings.embed_batch_size
        for i in range(0, len(ids), batch_size):
            end = i + batch_size
            self.collection.add(
                ids=ids[i:end],
                documents=documents[i:end],
                metadatas=metadatas[i:end],
            )

    def _delete_file_chunks(self, path: str, repo_name: str) -> int:
        """Delete existing chunks for a file path + repo."""
        try:
            results = self.collection.get(
                where={
                    "$and": [
                        {"file_path": path},
                        {"repo": repo_name},
                    ]
                },
            )
            count = len(results["ids"])
            if count > 0:
                self.collection.delete(ids=results["ids"])
            return count
        except Exception:
            return 0

    def _chunk_markdown(self, text: str) -> list[dict]:
        """Split markdown by headers, then by size if needed."""
        header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=_MD_HEADERS,
            strip_headers=False,
        )
        header_docs = header_splitter.split_text(text)

        size_splitter = RecursiveCharacterTextSplitter(
            chunk_size=_MD_CHUNK_SIZE,
            chunk_overlap=_MD_CHUNK_OVERLAP,
        )

        chunks = []
        for doc in header_docs:
            heading_parts = []
            for key in ("h1", "h2", "h3"):
                if key in doc.metadata:
                    heading_parts.append(doc.metadata[key])
            heading_context = " > ".join(heading_parts)

            sub_chunks = size_splitter.split_text(doc.page_content)
            for sub in sub_chunks:
                chunks.append(
                    {
                        "text": sub,
                        "heading_context": heading_context,
                    }
                )
        return chunks

    def _chunk_code(self, text: str, language: Language | None = None) -> list[dict]:
        """Split code by language-aware boundaries."""
        if language:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=_CODE_CHUNK_SIZE,
                chunk_overlap=_CODE_CHUNK_OVERLAP,
                separators=RecursiveCharacterTextSplitter.get_separators_for_language(
                    language
                ),
            )
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=_CODE_CHUNK_SIZE,
                chunk_overlap=_CODE_CHUNK_OVERLAP,
            )

        parts = splitter.split_text(text)
        return [{"text": p, "heading_context": ""} for p in parts]

    def _chunk_generic(self, text: str) -> list[dict]:
        """Generic text splitting for config files, etc."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=_MD_CHUNK_SIZE,
            chunk_overlap=_MD_CHUNK_OVERLAP,
        )
        parts = splitter.split_text(text)
        return [{"text": p, "heading_context": ""} for p in parts]
