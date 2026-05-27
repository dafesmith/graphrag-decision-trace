"""Load sample loans and policies from data/ into Neo4j."""
from __future__ import annotations

import json
from pathlib import Path

from .graph import bootstrap_schema, session, wipe

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_json(name: str):
    with (DATA_DIR / name).open() as f:
        return json.load(f)


def seed() -> None:
    wipe()
    bootstrap_schema()

    policies = _load_json("policies.json")
    loans = _load_json("loans.json")

    with session() as s:
        s.run(
            """
            UNWIND $policies AS p
            MERGE (pol:Policy {id: p.id})
            SET pol.name = p.name,
                pol.description = p.description,
                pol.rule = p.rule,
                pol.regulatory_basis = p.regulatory_basis,
                pol.outcome_on_trigger = p.outcome_on_trigger
            """,
            policies=policies,
        )

        for loan in loans:
            s.run(
                """
                MERGE (a:Applicant {id: $applicant.id})
                SET a.name = $applicant.name, a.age = $applicant.age

                MERGE (l:LoanApplication {id: $id})
                SET l.purpose = $features.purpose,
                    l.loan_amount = $features.loan_amount,
                    l.loan_term_months = $features.loan_term_months,
                    l.decided_at = $decision.decided_at

                MERGE (a)-[:SUBMITTED]->(l)

                MERGE (d:Decision {id: 'DEC-' + $id})
                SET d.outcome = $decision.outcome,
                    d.decided_at = $decision.decided_at
                MERGE (l)-[:RECEIVED]->(d)

                WITH l, d, $features AS feat, $id AS loan_id, $decision.applied_policies AS pol_ids
                UNWIND keys(feat) AS feat_name
                MERGE (f:Feature {id: 'f_' + loan_id + '_' + feat_name})
                SET f.name = feat_name, f.value = feat[feat_name]
                MERGE (l)-[:HAS_FEATURE]->(f)

                WITH d, pol_ids
                UNWIND pol_ids AS pol_id
                MATCH (pol:Policy {id: pol_id})
                MERGE (d)-[:APPLIED]->(pol)
                """,
                id=loan["id"],
                applicant=loan["applicant"],
                features=loan["features"],
                decision=loan["decision"],
            )

            for sim in loan.get("similar_to", []):
                s.run(
                    """
                    MATCH (a:LoanApplication {id: $a_id})
                    MATCH (b:LoanApplication {id: $b_id})
                    MERGE (a)-[r:SIMILAR_TO]->(b)
                    SET r.score = $score
                    """,
                    a_id=loan["id"],
                    b_id=sim["id"],
                    score=sim["score"],
                )

    print(f"Seeded {len(policies)} policies and {len(loans)} loan applications.")


if __name__ == "__main__":
    seed()
