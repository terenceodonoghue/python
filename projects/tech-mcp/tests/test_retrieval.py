"""Eval harness for retrieval quality.

8 cases: single-repo, cross-repo, sessions.
Run: uv run pytest tests/test_retrieval.py -v
"""

import json

import pytest

# Each eval case: (query, expected_source_types, expected_repos, description)
EVAL_CASES = [
    # ── Single-repo queries (3) ──────────────────────────────────────────
    (
        "What endpoints does the auth API expose?",
        ["doc"],
        ["auth-api"],
        "Single-repo: auth-api endpoints",
    ),
    (
        "How does the JavaScript frontend authenticate users?",
        ["doc"],
        ["auth-web"],
        "Single-repo: auth-web auth flow",
    ),
    (
        "What is the WebAuthn relying party configuration?",
        ["doc"],
        ["auth-api"],
        "Single-repo: auth-api WebAuthn config",
    ),
    # ── Cross-repo queries (3) ───────────────────────────────────────────
    (
        "How does the frontend call the registration API?",
        ["doc"],
        ["auth-api", "auth-web"],
        "Cross-repo: frontend → API registration",
    ),
    (
        "What does the login flow look like end to end?",
        ["doc"],
        ["auth-api", "auth-web"],
        "Cross-repo: end-to-end login",
    ),
    (
        "Which services use PostgreSQL?",
        ["doc"],
        ["auth-api"],
        "Cross-repo: PostgreSQL usage",
    ),
    # ── Session queries (2) ──────────────────────────────────────────────
    (
        "502 error with Caddy reverse proxy",
        ["session"],
        ["auth-api", "homelab"],
        "Session: Caddy 502 debugging",
    ),
    (
        "Docker DNS resolution failure between containers",
        ["session"],
        ["auth-api", "homelab"],
        "Session: Docker network DNS issue",
    ),
]


def _check_hit(
    results_json: str,
    expected_types: list[str],
    expected_repos: list[str],
) -> bool:
    """Check if at least one result matches expected source type AND repo."""
    data = json.loads(results_json)
    results = data.get("results", [])
    for result in results:
        source_type = result.get("source_type", "")
        repo = result.get("repo", "")
        if source_type in expected_types and repo in expected_repos:
            return True
    return False


@pytest.mark.parametrize(
    "query,expected_types,expected_repos,description",
    EVAL_CASES,
    ids=[c[3] for c in EVAL_CASES],
)
def test_eval_case(populated_kb, query, expected_types, expected_repos, description):
    _, retrieval = populated_kb
    results = retrieval.search_kb(query, limit=5)
    hit = _check_hit(results, expected_types, expected_repos)
    if not hit:
        data = json.loads(results)
        actual = [f"{r['source_type']}:{r['repo']}" for r in data.get("results", [])]
        pytest.fail(f"[{description}] No hit. Got: {actual}")


def test_eval_report(populated_kb):
    """Run all cases and print a summary report."""
    _, retrieval = populated_kb
    hits = 0
    failures = []

    for query, expected_types, expected_repos, description in EVAL_CASES:
        results = retrieval.search_kb(query, limit=5)
        if _check_hit(results, expected_types, expected_repos):
            hits += 1
        else:
            data = json.loads(results)
            actual = [
                f"{r['source_type']}:{r['repo']}" for r in data.get("results", [])
            ]
            failures.append(f"  MISS: {description} → got {actual}")

    total = len(EVAL_CASES)
    print(f"\n{'=' * 60}")
    print(f"Eval Score: {hits}/{total}")
    print(f"{'=' * 60}")
    if failures:
        print("Failures:")
        for f in failures:
            print(f)
    print(f"{'=' * 60}")

    # This test always passes — it's for reporting only
    assert True
