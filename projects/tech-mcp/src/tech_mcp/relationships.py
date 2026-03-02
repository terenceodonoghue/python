import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_GRAPH: dict[str, dict] = {
    "auth-api": {
        "consumed_by": ["auth-web"],
        "depends_on": [],
        "description": "WebAuthn/passkey authentication service written in Go",
        "type": "service",
    },
    "fron-svc": {
        "depends_on": [],
        "description": "Fronius solar inverter polling service written in Go",
        "type": "service",
    },
    "auth-web": {
        "consumes": ["auth-api"],
        "depends_on": [],
        "description": "Login and registration UI for passkey auth",
        "type": "webapp",
    },
    "homelab": {
        "hosts": ["auth-api", "fron-svc", "auth-web", "home-mcp", "tech-mcp"],
        "depends_on": [],
        "description": "Infrastructure - Docker, Caddy, Ansible, Pi config",
        "type": "infrastructure",
    },
    "home-mcp": {
        "depends_on": ["homelab"],
        "description": "MCP server for querying solar data from InfluxDB",
        "type": "mcp",
        "mcp_server": True,
    },
    "tech-mcp": {
        "depends_on": ["homelab"],
        "description": "Knowledge base MCP server for cross-repo context",
        "type": "mcp",
        "mcp_server": True,
    },
}

# Valid relationship keys (directional edges in the graph)
_RELATIONSHIP_KEYS = frozenset({"consumes", "consumed_by", "depends_on", "hosts"})


class RelationshipGraph:
    """Manages the inter-repo relationship graph."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._graph: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            self._graph = json.loads(self._path.read_text())
            logger.info("Loaded relationship graph with %d repos", len(self._graph))
        else:
            logger.info("No relationship file found, seeding defaults")
            self._graph = _DEFAULT_GRAPH.copy()
            self._save()

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._graph, indent=2) + "\n")

    def validate_repo(self, repo_name: str) -> None:
        """Raise ValueError if repo is not in the graph."""
        if repo_name not in self._graph:
            available = ", ".join(sorted(self._graph.keys()))
            msg = (
                f"Repo '{repo_name}' not found in relationships.json. "
                f"Available repos: {available}. "
                f"Add it to relationships.json directly."
            )
            raise ValueError(msg)

    def list_repos(self) -> dict[str, dict]:
        """Return the full graph."""
        return self._graph.copy()

    def get_repo(self, repo_name: str) -> dict:
        """Return a single repo's entry."""
        self.validate_repo(repo_name)
        return self._graph[repo_name].copy()

    def is_mcp_server(self, repo_name: str) -> bool:
        """Check if a repo is flagged as an MCP server."""
        return self._graph.get(repo_name, {}).get("mcp_server", False)

    def get_repo_type(self, repo_name: str) -> str:
        """Return the type of a repo."""
        return self._graph.get(repo_name, {}).get("type", "unknown")

    def get_related_repos(self, repo_name: str) -> list[str]:
        """Return all repos directly related to the given repo."""
        self.validate_repo(repo_name)
        entry = self._graph[repo_name]
        related: set[str] = set()
        for key in _RELATIONSHIP_KEYS:
            for r in entry.get(key, []):
                related.add(r)
        # Also find repos that reference this one
        for name, data in self._graph.items():
            if name == repo_name:
                continue
            for key in _RELATIONSHIP_KEYS:
                if repo_name in data.get(key, []):
                    related.add(name)
        return sorted(related)
