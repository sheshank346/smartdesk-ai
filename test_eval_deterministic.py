import pytest
from agent import handle_query

@pytest.mark.parametrize("query, expected_action", [
    ("What is the status of TCK-0001?", "tool_call: check_ticket_status"),
    ("Please check ticket TCK-0456", "tool_call: check_ticket_status"),
    ("How do I reset my password?", "rag_retrieval"),
    ("What are your support hours?", "rag_retrieval"),
    ("Tell me a random joke", "rag_retrieval"),
])
def test_deterministic_routing(query, expected_action):
    result = handle_query(query)
    
    assert result is not None, f"Result was None for query: {query}"
    assert isinstance(result, dict), f"Result must be a dictionary, got {type(result)}"
    assert "action_taken" in result, f"Result missing 'action_taken' key for query: {query}"
    
    assert result.get("action_taken") == expected_action, (
        f"Expected action '{expected_action}' but got '{result.get('action_taken')}' for query: {query}"
    )