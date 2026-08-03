"""
tools.py
Simulates a real backend action the agent can take: looking up a support
ticket's live status. In a real company system, check_ticket_status()
would call an internal REST API or query a database instead of a JSON file.
Keeping the interface the same (a plain Python function returning a dict)
means swapping in a real API later requires no change to agent.py.
"""

import json

with open("data/tickets.json", "r", encoding="utf-8") as f:
    TICKETS = json.load(f)


def check_ticket_status(ticket_id: str) -> dict:
    """Look up a ticket by ID. Returns the ticket record, or a not-found dict."""
    ticket_id = ticket_id.strip().upper()
    if ticket_id in TICKETS:
        return {"found": True, "ticket_id": ticket_id, **TICKETS[ticket_id]}
    return {"found": False, "ticket_id": ticket_id}
