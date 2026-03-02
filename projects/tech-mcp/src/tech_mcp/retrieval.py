import json
import logging

import chromadb

from tech_mcp.config import Settings
from tech_mcp.embeddings import OllamaEmbeddingFunction
from tech_mcp.relationships import RelationshipGraph

logger = logging.getLogger(__name__)


class Retrieval:
    """Semantic search across the knowledge base."""

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

    def search_kb(
        self,
        query: str,
        repos: list[str] | None = None,
        source_type: str | None = None,
        limit: int = 5,
    ) -> str:
        """Semantic search across the full knowledge base."""
        where_clauses: list[dict] = []
        if repos:
            if len(repos) == 1:
                where_clauses.append({"repo": repos[0]})
            else:
                where_clauses.append({"repo": {"$in": repos}})
        if source_type:
            where_clauses.append({"source": source_type})

        where = None
        if len(where_clauses) == 1:
            where = where_clauses[0]
        elif len(where_clauses) > 1:
            where = {"$and": where_clauses}

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            logger.exception("Search failed")
            return json.dumps({"error": str(exc)})

        return self._format_results(results)

    def search_related(
        self,
        query: str,
        repo: str,
        limit: int = 5,
    ) -> str:
        """Search a repo and its related repos."""
        self._graph.validate_repo(repo)
        related = self._graph.get_related_repos(repo)
        all_repos = [repo, *related]

        return self.search_kb(query=query, repos=all_repos, limit=limit)

    def _format_results(self, results: dict) -> str:
        """Format ChromaDB results into a readable JSON string."""
        if not results["ids"] or not results["ids"][0]:
            return json.dumps({"results": [], "count": 0})

        formatted = []
        for i, doc_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i]
            entry = {
                "id": doc_id,
                "content": results["documents"][0][i],
                "distance": results["distances"][0][i],
                "source_type": meta.get("source", ""),
                "repo": meta.get("repo", ""),
                "file_path": meta.get("file_path", ""),
                "heading_context": meta.get("heading_context", ""),
                "tags": meta.get("tags", ""),
            }
            formatted.append(entry)

        return json.dumps(
            {"results": formatted, "count": len(formatted)},
            indent=2,
        )
