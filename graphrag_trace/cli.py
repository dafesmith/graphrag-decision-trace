"""CLI entry point: `python -m graphrag_trace.cli trace LOAN-1042`."""
from __future__ import annotations

import sys

from .tracer import trace


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv or argv[0] in {"-h", "--help"}:
        print("Usage: python -m graphrag_trace.cli trace <LOAN_ID>")
        return 0

    cmd = argv[0]
    if cmd != "trace" or len(argv) < 2:
        print("Usage: python -m graphrag_trace.cli trace <LOAN_ID>")
        return 2

    loan_id = argv[1]
    result = trace(loan_id)

    if result.evidence.is_empty():
        print(f"No record found for {loan_id}.")
        return 1

    print(result.explanation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
