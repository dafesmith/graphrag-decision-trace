"""Neo4j connection + schema bootstrap.

The graph schema:

    (:Applicant {id, name, age})
        -[:SUBMITTED]->
    (:LoanApplication {id, purpose, loan_amount, loan_term_months, decided_at})
        -[:HAS_FEATURE]->
    (:Feature {id, name, value})

    (:LoanApplication)-[:RECEIVED]->(:Decision {id, outcome, decided_at})
    (:Decision)-[:APPLIED]->(:Policy {id, name, description, rule, regulatory_basis})
    (:LoanApplication)-[:SIMILAR_TO {score}]->(:LoanApplication)
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from neo4j import Driver, GraphDatabase

from .config import get_settings

CONSTRAINTS = [
    "CREATE CONSTRAINT applicant_id IF NOT EXISTS FOR (a:Applicant) REQUIRE a.id IS UNIQUE",
    "CREATE CONSTRAINT loan_id IF NOT EXISTS FOR (l:LoanApplication) REQUIRE l.id IS UNIQUE",
    "CREATE CONSTRAINT decision_id IF NOT EXISTS FOR (d:Decision) REQUIRE d.id IS UNIQUE",
    "CREATE CONSTRAINT policy_id IF NOT EXISTS FOR (p:Policy) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT feature_id IF NOT EXISTS FOR (f:Feature) REQUIRE f.id IS UNIQUE",
]


def driver() -> Driver:
    s = get_settings()
    return GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password))


@contextmanager
def session() -> Iterator:
    d = driver()
    try:
        with d.session() as s:
            yield s
    finally:
        d.close()


def bootstrap_schema() -> None:
    """Create uniqueness constraints. Idempotent."""
    with session() as s:
        for stmt in CONSTRAINTS:
            s.run(stmt)


def wipe() -> None:
    """Delete every node and relationship. Use only in dev/test."""
    with session() as s:
        s.run("MATCH (n) DETACH DELETE n")
