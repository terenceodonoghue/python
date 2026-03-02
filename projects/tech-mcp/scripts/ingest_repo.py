#!/usr/bin/env python
"""CLI for bulk ingestion of a repository into tech-mcp's knowledge base."""

import argparse
import sys

from tech_mcp.config import _load_settings
from tech_mcp.embeddings import OllamaEmbeddingFunction, check_ollama
from tech_mcp.ingestion import Ingestion
from tech_mcp.relationships import RelationshipGraph


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest a repository into tech-mcp's knowledge base",
    )
    parser.add_argument("path", help="Path to the repository directory")
    parser.add_argument(
        "repo_name",
        help="Repository name (must exist in relationships.json)",
    )
    parser.add_argument(
        "--related",
        nargs="*",
        default=None,
        help="Related repo names",
    )
    parser.add_argument(
        "--extensions",
        nargs="*",
        default=None,
        help="File extensions to include (e.g. .py .go .md)",
    )
    args = parser.parse_args()

    settings = _load_settings()

    if not check_ollama(settings.ollama_host, settings.ollama_embed_model):
        print(
            f"Error: Ollama not reachable at {settings.ollama_host} "
            f"or model '{settings.ollama_embed_model}' not available.",
            file=sys.stderr,
        )
        sys.exit(1)

    embedding_fn = OllamaEmbeddingFunction(
        host=settings.ollama_host,
        model=settings.ollama_embed_model,
        batch_size=settings.embed_batch_size,
    )
    graph = RelationshipGraph(settings.relationships_file)
    ingestion = Ingestion(settings, graph, embedding_fn)

    print(f"Ingesting {args.path} as '{args.repo_name}'...")
    summary = ingestion.ingest_directory(
        path=args.path,
        repo_name=args.repo_name,
        related_repos=args.related,
        extensions=args.extensions,
    )

    print(f"  Files found:           {summary['files_found']}")
    print(f"  Files ingested:        {summary['files_ingested']}")
    print(f"  Chunks created:        {summary['chunks_created']}")
    print(f"  Session ID:            {summary['ingest_session_id']}")


if __name__ == "__main__":
    main()
