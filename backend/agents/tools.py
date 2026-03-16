from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from agents import function_tool


@function_tool
async def web_research(query: str) -> str:
    """Example research tool. Replace with real retrieval or web integrations."""
    return f"Research brief for '{query}': gather market, competitor, and user evidence before acting."


@function_tool
async def write_marketing_copy(product: str, audience: str) -> str:
    """Generate a starter message for marketing workflows."""
    return (
        f"Position {product} for {audience} with clear outcomes, proof points, and one focused CTA."
    )


@function_tool
async def generate_code_scaffold(service_name: str, language: str = "python") -> str:
    """Return a scaffold recommendation for implementation tasks."""
    return f"Recommended scaffold for {service_name} in {language}: API layer, domain layer, tests, and CI hooks."


@function_tool
async def record_decision(decision: str, metadata: dict[str, Any] | None = None) -> str:
    """Persistable decision log payload for audit trails."""
    payload = {
        "decision": decision,
        "metadata": metadata or {},
        "timestamp": datetime.now(UTC).isoformat(),
    }
    return json.dumps(payload)
