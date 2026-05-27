"""GraphRAG retrieval: pull the evidence subgraph for a given loan decision.

The retriever runs a small set of bounded Cypher queries. We deliberately
return *structured* evidence (dicts), not free-form strings, so the LLM
prompt builder can format citations precisely.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .graph import session


@dataclass
class Evidence:
    loan_id: str
    decision: dict[str, Any]
    applicant: dict[str, Any]
    features: list[dict[str, Any]] = field(default_factory=list)
    triggered_policies: list[dict[str, Any]] = field(default_factory=list)
    similar_cases: list[dict[str, Any]] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.decision


def retrieve(loan_id: str, similarity_threshold: float = 0.80) -> Evidence:
    """Pull the evidence subgraph for one loan decision."""
    ev = Evidence(loan_id=loan_id, decision={}, applicant={})

    with session() as s:
        # Core decision + applicant
        rec = s.run(
            """
            MATCH (a:Applicant)-[:SUBMITTED]->(l:LoanApplication {id: $loan_id})-[:RECEIVED]->(d:Decision)
            RETURN a {.*} AS applicant,
                   l {.*} AS loan,
                   d {.*} AS decision
            """,
            loan_id=loan_id,
        ).single()

        if rec is None:
            return ev

        ev.applicant = dict(rec["applicant"])
        ev.decision = {**dict(rec["decision"]), "loan": dict(rec["loan"])}

        # Features
        feat_rows = s.run(
            """
            MATCH (:LoanApplication {id: $loan_id})-[:HAS_FEATURE]->(f:Feature)
            RETURN f {.*} AS feature
            ORDER BY f.name
            """,
            loan_id=loan_id,
        )
        ev.features = [dict(r["feature"]) for r in feat_rows]

        # Triggered policies (only those linked to this decision)
        pol_rows = s.run(
            """
            MATCH (:LoanApplication {id: $loan_id})-[:RECEIVED]->(:Decision)-[:APPLIED]->(p:Policy)
            RETURN p {.*} AS policy
            ORDER BY p.id
            """,
            loan_id=loan_id,
        )
        ev.triggered_policies = [dict(r["policy"]) for r in pol_rows]

        # Similar past cases above threshold
        sim_rows = s.run(
            """
            MATCH (:LoanApplication {id: $loan_id})-[r:SIMILAR_TO]->(other:LoanApplication)-[:RECEIVED]->(d:Decision)
            WHERE r.score >= $threshold
            RETURN other.id AS id,
                   r.score  AS score,
                   d.outcome AS outcome,
                   d.decided_at AS decided_at
            ORDER BY r.score DESC
            """,
            loan_id=loan_id,
            threshold=similarity_threshold,
        )
        ev.similar_cases = [dict(r) for r in sim_rows]

    return ev
