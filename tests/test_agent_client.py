import pytest
from unittest.mock import patch, AsyncMock

from src.agent.client import client, ClaudeAgentOptions, load_system_prompt


def test_agent_initialization():
    """Tests that the ClaudeSDKClient is initialized correctly."""
    assert client is not None
    assert isinstance(client.options, ClaudeAgentOptions)
    assert client.options.model == "claude-3-5-sonnet-20241022"
    assert client.options.max_turns == 30
    assert "Google Ads campaign automation specialist" in client.options.system_prompt


def test_system_prompt_loading():
    """Tests that the system prompt is loaded correctly from the file."""
    prompt = load_system_prompt("google_ads_agent.txt")
    assert "You are an expert Google Ads campaign automation specialist." in prompt
    assert "Your capabilities include:" in prompt
    assert "Your boundaries are:" in prompt


@pytest.mark.asyncio
@patch("claude_agent_sdk.ClaudeSDKClient.query", new_callable=AsyncMock)
async def test_agent_health_check(mock_query):
    """Tests that the agent can respond to a simple 'Hello' message."""
    # Mock the response from the agent
    mock_response = {
        "status": "ok",
        "content": [
            {
                "text": "Hello there! How can I help you with your Google Ads campaigns today?"
            }
        ],
    }

    # Make the mock an async iterator
    async def mock_iterator():
        yield mock_response

    mock_query.return_value = mock_iterator()

    # Send a message to the agent
    async for response in await client.query("Hello"):
        # Assert that the mocked response is what we got
        assert response is not None
        assert response["status"] == "ok"
        assert "Hello there!" in response["content"][0]["text"]
        break  # Only expect one response

    # Verify that the mock was called
    mock_query.assert_called_once_with("Hello")
