import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ollama_host: str
    ollama_embed_model: str
    chroma_persist_dir: str
    relationships_file: str
    embed_batch_size: int
    log_level: str
    port: int
    mcp_host: str


def _load_settings() -> Settings:
    ollama_host = os.environ.get("OLLAMA_HOST")
    if not ollama_host:
        msg = "OLLAMA_HOST is required (e.g. http://host.docker.internal:11434)"
        raise RuntimeError(msg)

    port_str = os.environ.get("PORT")
    if not port_str:
        msg = "PORT is required (e.g. 8091)"
        raise RuntimeError(msg)

    return Settings(
        ollama_host=ollama_host,
        ollama_embed_model=os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
        chroma_persist_dir=os.environ.get("CHROMA_PERSIST_DIR", "./data/chroma"),
        relationships_file=os.environ.get(
            "RELATIONSHIPS_FILE", "./data/relationships.json"
        ),
        embed_batch_size=int(os.environ.get("EMBED_BATCH_SIZE", "10")),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        port=int(port_str),
        mcp_host=os.environ.get("MCP_HOST", "0.0.0.0"),
    )
