"""FastAPI service with a minimal HTML page for browsing decisions."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from .graph import session
from .tracer import trace

app = FastAPI(title="GraphRAG Decision Trace", version="0.1.0")


@app.get("/api/loans")
def list_loans() -> list[dict]:
    with session() as s:
        rows = s.run(
            """
            MATCH (l:LoanApplication)-[:RECEIVED]->(d:Decision)
            RETURN l.id AS id, l.purpose AS purpose, d.outcome AS outcome, d.decided_at AS decided_at
            ORDER BY d.decided_at DESC, l.id
            """
        )
        return [dict(r) for r in rows]


@app.get("/api/trace/{loan_id}")
def api_trace(loan_id: str) -> dict:
    result = trace(loan_id)
    if result.evidence.is_empty():
        raise HTTPException(status_code=404, detail=f"No record for {loan_id}")
    return {
        "loan_id": result.loan_id,
        "evidence": asdict(result.evidence),
        "explanation": result.explanation,
    }


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>GraphRAG Decision Trace</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root { color-scheme: light dark; }
    body { font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; max-width: 920px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }
    h1 { margin-bottom: 0.25rem; }
    p.subtitle { color: #666; margin-top: 0; }
    table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
    th, td { text-align: left; padding: 0.5rem 0.75rem; border-bottom: 1px solid #eee2; }
    th { background: #88888812; font-weight: 600; }
    tr:hover { background: #88888808; cursor: pointer; }
    .approved { color: #1a7f37; font-weight: 600; }
    .denied   { color: #b52a1d; font-weight: 600; }
    pre { background: #88888812; padding: 1rem; border-radius: 6px; white-space: pre-wrap; word-wrap: break-word; }
    #explanation { margin-top: 1.5rem; }
    .pill { display: inline-block; padding: 0.1rem 0.5rem; border-radius: 999px; background: #88888822; font-size: 0.85em; }
  </style>
</head>
<body>
  <h1>GraphRAG Decision Trace</h1>
  <p class="subtitle">Click a loan to see why it was approved or denied — evidence is retrieved from a Neo4j knowledge graph, then explained by an LLM with citations.</p>

  <table id="loans">
    <thead><tr><th>Loan</th><th>Purpose</th><th>Decision</th><th>Date</th></tr></thead>
    <tbody></tbody>
  </table>

  <section id="explanation"></section>

<script>
async function loadLoans() {
  const res = await fetch('/api/loans');
  const loans = await res.json();
  const tbody = document.querySelector('#loans tbody');
  tbody.innerHTML = loans.map(l => `
    <tr data-id="${l.id}">
      <td>${l.id}</td>
      <td><span class="pill">${l.purpose}</span></td>
      <td class="${l.outcome.toLowerCase()}">${l.outcome}</td>
      <td>${l.decided_at}</td>
    </tr>`).join('');
  tbody.querySelectorAll('tr').forEach(tr => tr.addEventListener('click', () => trace(tr.dataset.id)));
}

async function trace(id) {
  const el = document.querySelector('#explanation');
  el.innerHTML = `<p>Tracing <code>${id}</code>...</p>`;
  const res = await fetch(`/api/trace/${id}`);
  if (!res.ok) { el.innerHTML = `<p>Not found.</p>`; return; }
  const data = await res.json();
  el.innerHTML = `
    <h2>${id} <span class="pill">${data.evidence.decision.outcome}</span></h2>
    <pre>${data.explanation.replace(/</g,'&lt;')}</pre>
    <details><summary>Raw evidence subgraph</summary><pre>${JSON.stringify(data.evidence, null, 2)}</pre></details>
  `;
  window.scrollTo({ top: el.offsetTop - 16, behavior: 'smooth' });
}

loadLoans();
</script>
</body>
</html>
"""
