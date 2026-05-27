"""High-level orchestration: retrieve evidence + ask the LLM to explain."""
from __future__ import annotations

from dataclasses import dataclass

from .llm import explain
from .retriever import Evidence, retrieve


@dataclass
class TraceResult:
    loan_id: str
    evidence: Evidence
    explanation: str


def trace(loan_id: str) -> TraceResult:
    ev = retrieve(loan_id)
    text = explain(ev)
    return TraceResult(loan_id=loan_id, evidence=ev, explanation=text)
