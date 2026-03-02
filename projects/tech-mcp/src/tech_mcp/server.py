import json
import logging

from mcp.server.fastmcp import FastMCP

from tech_mcp.config import _load_settings
from tech_mcp.embeddings import OllamaEmbeddingFunction, check_ollama
from tech_mcp.ingestion import Ingestion
from tech_mcp.relationships import RelationshipGraph
from tech_mcp.retrieval import Retrieval

settings = _load_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Check Ollama connectivity at startup (warn, don't crash)
_ollama_ok = check_ollama(settings.ollama_host, settings.ollama_embed_model)

mcp = FastMCP(
    "tech-mcp",
    host=settings.mcp_host,
    port=settings.port,
)

# Shared dependencies
_embedding_fn = OllamaEmbeddingFunction(
    host=settings.ollama_host,
    model=settings.ollama_embed_model,
    batch_size=settings.embed_batch_size,
)
_graph = RelationshipGraph(settings.relationships_file)
_ingestion = Ingestion(settings, _graph, _embedding_fn)
_retrieval = Retrieval(settings, _graph, _embedding_fn)


# ── Health endpoint ──────────────────────────────────────────────────────────


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    from starlette.responses import JSONResponse

    ollama_ok = check_ollama(settings.ollama_host, settings.ollama_embed_model)
    try:
        _ingestion.client.heartbeat()
        chroma_ok = True
    except Exception:
        chroma_ok = False

    return JSONResponse(
        {
            "status": "ok",
            "ollama": ollama_ok,
            "chroma": chroma_ok,
        }
    )


# ── Search Tools ─────────────────────────────────────────────────────────────


@mcp.tool()
def search_kb(
    query: str,
    repos: list[str] | None = None,
    source_type: str | None = None,
    limit: int = 5,
) -> str:
    """Semantic search across the full knowledge base.

    Args:
        query: Natural language search query.
        repos: Optional list of repo names to restrict search to.
        source_type: Optional filter — "doc", "code", or "session".
        limit: Maximum number of results to return.
    """
    return _retrieval.search_kb(query, repos, source_type, limit)


@mcp.tool()
def search_related(
    query: str,
    repo: str,
    limit: int = 5,
) -> str:
    """Expand search to include related repos via the relationship graph.

    Labels each result with its repo and source type.

    Args:
        query: Natural language search query.
        repo: Starting repo — related repos are included automatically.
        limit: Maximum number of results to return.
    """
    return _retrieval.search_related(query, repo, limit)


# ── Session Ingestion Tools ──────────────────────────────────────────────────


@mcp.tool()
def ingest_session(
    problem: str,
    attempts: list[dict[str, str]],
    root_cause: str,
    solution: str,
    repos: list[str],
    tags: list[str] | None = None,
) -> str:
    """Ingest a debugging session for future reference.

    Each attempt should have: action, outcome, why_failed.
    Repos must exist in relationships.json.

    Args:
        problem: Description of the problem encountered.
        attempts: List of dicts with keys: action, outcome, why_failed.
        root_cause: The identified root cause.
        solution: The working solution.
        repos: List of repo names involved. Must exist in
            relationships.json.
        tags: Optional tags for categorisation (e.g. "caddy", "502",
            "docker").
    """
    session_id = _ingestion.ingest_session(
        problem, attempts, root_cause, solution, repos, tags
    )
    return json.dumps({"ingest_session_id": session_id})


# ── Document Ingestion Tools ─────────────────────────────────────────────────


@mcp.tool()
def ingest_file(
    path: str,
    repo_name: str,
    related_repos: list[str] | None = None,
) -> str:
    """Ingest a single file into the knowledge base.

    Reads the file from the server's filesystem.

    Args:
        path: Absolute path to the file (on the server).
        repo_name: Repo name (must exist in relationships.json).
        related_repos: Optional list of related repo names.
    """
    count, session_id = _ingestion.ingest_file(path, repo_name, related_repos)
    return json.dumps({"chunk_count": count, "ingest_session_id": session_id})


@mcp.tool()
def ingest_directory(
    path: str,
    repo_name: str,
    related_repos: list[str] | None = None,
    extensions: list[str] | None = None,
) -> str:
    """Ingest all supported files in a directory.

    Skips: node_modules, vendor, .git, __pycache__, dist, build, .venv.

    Default extensions: .md, .py, .go, .js, .ts, .yaml, .yml, .toml

    Args:
        path: Absolute path to the directory.
        repo_name: Repo name (must exist in relationships.json).
        related_repos: Optional list of related repo names.
        extensions: Optional list of file extensions to include.
    """
    summary = _ingestion.ingest_directory(path, repo_name, related_repos, extensions)
    return json.dumps(summary)


# ── Rollback Tools ───────────────────────────────────────────────────────────


@mcp.tool()
def list_recent_ingestions(limit: int = 20) -> str:
    """List recent ingestion sessions.

    Shows: ingest_session_id, timestamp, source type, repo, chunk count.

    Args:
        limit: Maximum number of sessions to return.
    """
    sessions = _ingestion.list_recent_ingestions(limit)
    return json.dumps(sessions, indent=2)


@mcp.tool()
def forget_session(ingest_session_id: str) -> str:
    """Delete all chunks from a specific ingestion session.

    Args:
        ingest_session_id: The UUID returned by an ingestion tool.
    """
    count = _ingestion.delete_by_session(ingest_session_id)
    return json.dumps({"deleted_chunks": count})


@mcp.tool()
def forget_file(path: str, repo_name: str) -> str:
    """Delete all chunks for a specific file.

    Args:
        path: The file path used during ingestion.
        repo_name: The repo name used during ingestion.
    """
    count = _ingestion.delete_by_file(path, repo_name)
    return json.dumps({"deleted_chunks": count})


@mcp.tool()
def forget_repo(repo_name: str, confirm: bool = False) -> str:
    """Delete ALL chunks for a repo.

    Requires confirm=True to prevent accidents.

    Args:
        repo_name: Repo to forget.
        confirm: Must be True to proceed.
    """
    if not confirm:
        return json.dumps(
            {"error": "Set confirm=True to delete all chunks for this repo."}
        )
    count = _ingestion.delete_by_repo(repo_name)
    return json.dumps({"deleted_chunks": count})


# ── Relationship Tools ───────────────────────────────────────────────────────


@mcp.tool()
def list_repos() -> str:
    """List all repos from the relationship graph with chunk counts.

    Flags which repos are MCP servers.
    """
    repos = _graph.list_repos()
    stats = _ingestion.get_stats()

    result = []
    for name, info in sorted(repos.items()):
        entry = {
            "repo": name,
            "type": info.get("type", ""),
            "description": info.get("description", ""),
            "mcp_server": info.get("mcp_server", False),
            "chunks": stats.get(name, {}),
        }
        result.append(entry)

    return json.dumps(result, indent=2)


@mcp.tool()
def get_repo_relationships(repo_name: str) -> str:
    """Show full relationship context for a repo.

    Args:
        repo_name: Repo to inspect.
    """
    info = _graph.get_repo(repo_name)
    related = _graph.get_related_repos(repo_name)
    return json.dumps(
        {
            "repo": repo_name,
            "info": info,
            "related_repos": related,
        },
        indent=2,
    )


# ── Maintenance Tools ────────────────────────────────────────────────────────


@mcp.tool()
def get_kb_stats() -> str:
    """Get knowledge base statistics.

    Returns chunk counts by repo and source type, Ollama connectivity,
    and ChromaDB status.
    """
    stats = _ingestion.get_stats()

    ollama_ok = check_ollama(settings.ollama_host, settings.ollama_embed_model)

    try:
        _ingestion.client.heartbeat()
        chroma_ok = True
    except Exception:
        chroma_ok = False

    total_chunks = sum(
        count for repo_stats in stats.values() for count in repo_stats.values()
    )

    return json.dumps(
        {
            "total_chunks": total_chunks,
            "by_repo": stats,
            "ollama": {
                "host": settings.ollama_host,
                "model": settings.ollama_embed_model,
                "reachable": ollama_ok,
            },
            "chroma": {
                "persist_dir": settings.chroma_persist_dir,
                "healthy": chroma_ok,
            },
        },
        indent=2,
    )
