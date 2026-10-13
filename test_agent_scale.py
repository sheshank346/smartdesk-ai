import itertools
import pytest
from agent import handle_query

actions = ["What is the status of", "Please check", "Can you look up", "Where is", "Check status for"]
ticket_ids = [f"TCK-{i:04d}" for i in range(1, 250)]
fillers = ["", " please!", " thanks.", " urgent!!"]

generated_ticket_tests = list(itertools.product(actions, ticket_ids, fillers))
ACTIVE_TEST_SAMPLE = generated_ticket_tests[:1000]

@pytest.mark.parametrize("action, ticket_id, filler", ACTIVE_TEST_SAMPLE)
def test_mass_ticket_routing_scale(action, ticket_id, filler):
    query = f"{action} {ticket_id}{filler}"
    try:
        result = handle_query(query)
        assert result is not None, f"Returned None for query: {query}"
        assert "action_taken" in result, f"Missing action_taken key for query: {query}"
        assert result.get("action_taken") in ["tool_call: check_ticket_status", "rag_retrieval"]
    except Exception as e:
        pytest.fail(f"Failed on generated query: {e}")

