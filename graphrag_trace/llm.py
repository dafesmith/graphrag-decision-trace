"""OpenAI prompt construction + invocation.

The prompt is deliberately strict about citing only the evidence we pass in.
If the API key is missing or the call fails, we fall back to a deterministic
template explanation so the demo still runs offline.
"""
from __future__ import annotations

import json
from typing import Any

from openai import OpenAI, OpenAIError

from .config import get_settings
from .retriever import Evidence

SYSTEM_PROMPT = """You are an explainability assistant for a regulated lending institution.

You will be given a JSON 'evidence' object retrieved from a knowledge graph
about one specific loan-application decision. Write a clear, factual explanation
of why this decision was made, using ONLY the evidence provided.

Rules:
- Cite each claim with the source: feature ids (f_LOAN-xxx_name), policy ids
  (POL-...), or similar-case ids (LOAN-...).
- Do NOT invent facts, policies, or numbers not present in the evidence.
- If no policies were triggered, the decision was APPROVED — state that plainly.
- Keep it tight: aim for 5-10 short lines.
"""


def explain(evidence: Evidence) -> str:
    """Generate a natural-language explanation. Falls back if no API key."""
    settings = get_settings()
    payload = _evidence_to_payload(evidence)

    if not settings.openai_api_key or settings.openai_api_key.startswith("sk-replace"):
        return _fallback(evidence)

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, indent=2)},
            ],
            temperature=0.1,
        )
        return resp.choices[0].message.content or _fallback(evidence)
    except OpenAIError as e:
        return f"[LLM call failed: {e}]\n\n{_fallback(evidence)}"


def _evidence_to_payload(ev: Evidence) -> dict[str, Any]:
    return {
        "loan_id": ev.loan_id,
        "applicant": ev.applicant,
        "decision": ev.decision,
        "features": ev.features,
        "triggered_policies": ev.triggered_policies,
        "similar_cases": ev.similar_cases,
    }


def _fallback(ev: Evidence) -> str:
    """Deterministic template explanation when the LLM isn't available."""
    if ev.is_empty():
        return f"No record found for {ev.loan_id}."

    lines = [f"Decision: {ev.decision.get('outcome', 'UNKNOWN')}"]
    lines.append(f"Decided: {ev.decision.get('decided_at', 'unknown date')}")
    lines.append("")

    if ev.triggered_policies:
        lines.append("Why:")
        for p in ev.triggered_policies:
            lines.append(f"  - {p['id']} — {p['name']}: {p['description']}")
        lines.append("")
        feat_by_name = {f["name"]: f for f in ev.features}
        cited_features = [
            f for f in ("fico", "dti", "income_annual", "employment_years", "loan_amount", "recent_default")
            if f in feat_by_name
        ]
        if cited_features:
            lines.append("Cited features:")
            for name in cited_features:
                f = feat_by_name[name]
                lines.append(f"  - {name} = {f['value']}  [feature id: {f['id']}]")
            lines.append("")
    else:
        lines.append("No policies were triggered — the application met all underwriting criteria.")
        lines.append("")

    if ev.similar_cases:
        lines.append("Precedent (similar past cases):")
        for c in ev.similar_cases:
            lines.append(f"  - {c['id']} ({c['outcome']}, similarity {c['score']:.2f})")

    return "\n".join(lines)
