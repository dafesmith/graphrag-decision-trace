"""End-to-end smoke test. Requires a running, seeded Neo4j.

Skips automatically if Neo4j isn't reachable, so it's safe to run in CI
without a database.
"""
from __future__ import annotations

import pytest
from neo4j.exceptions import ServiceUnavailable

from graphrag_trace.graph import session
from graphrag_trace.llm import _fallback
from graphrag_trace.retriever import retrieve
from graphrag_trace.tracer import trace


def _neo4j_available() -> bool:
    try:
        with session() as s:
            s.run("RETURN 1").single()
        return True
    except ServiceUnavailable:
        return False


pytestmark = pytest.mark.skipif(
    not _neo4j_available(),
    reason="Neo4j is not reachable — start it with `make neo4j && make seed`",
)


def test_retrieve_denied_loan_returns_triggered_policies():
    ev = retrieve("LOAN-1042")
    assert not ev.is_empty()
    assert ev.decision["outcome"] == "DENIED"
    policy_ids = {p["id"] for p in ev.triggered_policies}
    assert {"POL-DTI-MAX", "POL-FICO-MIN"}.issubset(policy_ids)


def test_retrieve_approved_loan_has_no_triggered_policies():
    ev = retrieve("LOAN-1001")
    assert not ev.is_empty()
    assert ev.decision["outcome"] == "APPROVED"
    assert ev.triggered_policies == []


def test_retrieve_unknown_loan_returns_empty_evidence():
    ev = retrieve("LOAN-DOES-NOT-EXIST")
    assert ev.is_empty()


def test_fallback_explanation_cites_policies():
    ev = retrieve("LOAN-1042")
    text = _fallback(ev)
    assert "POL-DTI-MAX" in text
    assert "POL-FICO-MIN" in text


def test_tracer_returns_explanation():
    result = trace("LOAN-1042")
    assert result.loan_id == "LOAN-1042"
    assert len(result.explanation) > 0
