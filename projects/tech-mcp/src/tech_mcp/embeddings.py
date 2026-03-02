import logging
import time

import httpx
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_INITIAL_BACKOFF = 1.0


class OllamaEmbeddingFunction(EmbeddingFunction):
    """ChromaDB-compatible embedding function backed by Ollama."""

    def __init__(self, host: str, model: str, batch_size: int = 10) -> None:
        self._host = host.rstrip("/")
        self._model = model
        self._batch_size = batch_size
        self._client = httpx.Client(timeout=120.0)

    def __call__(self, input: Documents) -> Embeddings:  # noqa: A002
        all_embeddings: Embeddings = []
        for i in range(0, len(input), self._batch_size):
            batch = input[i : i + self._batch_size]
            embeddings = self._embed_with_retry(batch)
            all_embeddings.extend(embeddings)
        return all_embeddings

    def _embed_with_retry(self, texts: list[str]) -> list[list[float]]:
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                start = time.monotonic()
                response = self._client.post(
                    f"{self._host}/api/embed",
                    json={"model": self._model, "input": texts},
                )
                response.raise_for_status()
                elapsed = time.monotonic() - start
                logger.debug("Embedded %d texts in %.2fs", len(texts), elapsed)
                return response.json()["embeddings"]
            except (httpx.HTTPError, KeyError) as exc:
                last_error = exc
                if attempt < _MAX_RETRIES - 1:
                    backoff = _INITIAL_BACKOFF * (2**attempt)
                    logger.warning(
                        "Ollama embed attempt %d failed: %s (retrying in %.1fs)",
                        attempt + 1,
                        exc,
                        backoff,
                    )
                    time.sleep(backoff)

        msg = (
            f"Ollama embedding failed after {_MAX_RETRIES} attempts. "
            f"Host: {self._host}, Model: {self._model}. "
            f"Last error: {last_error}"
        )
        raise RuntimeError(msg)


def check_ollama(host: str, model: str) -> bool:
    """Check if Ollama is reachable and the model is available."""
    try:
        client = httpx.Client(timeout=5.0)
        response = client.get(f"{host.rstrip('/')}/api/tags")
        response.raise_for_status()
        models = [m["name"] for m in response.json().get("models", [])]
        # Model names may include :latest tag
        available = any(m == model or m.startswith(f"{model}:") for m in models)
        if not available:
            logger.warning(
                "Ollama reachable but model '%s' not found. "
                "Available: %s. Run: ollama pull %s",
                model,
                models,
                model,
            )
        return available
    except httpx.HTTPError as exc:
        logger.warning("Ollama unreachable at %s: %s", host, exc)
        return False
