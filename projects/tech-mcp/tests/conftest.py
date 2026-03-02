import hashlib
import json
from pathlib import Path

import pytest
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from tech_mcp.config import Settings
from tech_mcp.ingestion import Ingestion
from tech_mcp.relationships import RelationshipGraph
from tech_mcp.retrieval import Retrieval

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class FakeEmbeddingFunction(EmbeddingFunction):
    """Deterministic embeddings from text hashes. No Ollama required."""

    def __init__(self) -> None:
        pass

    def __call__(self, input: Documents) -> Embeddings:  # noqa: A002
        embeddings = []
        for text in input:
            hash_bytes = hashlib.sha256(text.encode()).digest()
            values = []
            for i in range(768):
                byte_val = hash_bytes[i % 32]
                values.append((byte_val / 255.0) * 2 - 1)
            embeddings.append(values)
        return embeddings


@pytest.fixture()
def settings(tmp_path):
    return Settings(
        ollama_host="http://fake:11434",
        ollama_embed_model="nomic-embed-text",
        chroma_persist_dir=str(tmp_path / "chroma"),
        relationships_file=str(tmp_path / "relationships.json"),
        embed_batch_size=10,
        log_level="DEBUG",
        port=8091,
        mcp_host="0.0.0.0",
    )


@pytest.fixture()
def fake_ef():
    return FakeEmbeddingFunction()


@pytest.fixture()
def graph(settings):
    return RelationshipGraph(settings.relationships_file)


@pytest.fixture()
def ingestion(settings, graph, fake_ef):
    return Ingestion(settings, graph, fake_ef)


@pytest.fixture()
def retrieval(settings, graph, fake_ef):
    return Retrieval(settings, graph, fake_ef)


@pytest.fixture()
def populated_kb(ingestion, retrieval, graph):
    """Ingest all fixtures and return (ingestion, retrieval) tuple."""
    # Ingest auth-api docs
    ingestion.ingest_file(
        str(FIXTURES_DIR / "auth-api" / "README.md"),
        "auth-api",
    )

    # Ingest auth-web docs
    ingestion.ingest_file(
        str(FIXTURES_DIR / "auth-web" / "README.md"),
        "auth-web",
    )

    # Ingest python-mcp as code
    ingestion.ingest_file(
        str(FIXTURES_DIR / "python-mcp" / "server.py"),
        "home-mcp",
    )

    # Ingest debug session
    session_data = json.loads((FIXTURES_DIR / "debug_session.json").read_text())
    ingestion.ingest_session(**session_data)

    return ingestion, retrieval
