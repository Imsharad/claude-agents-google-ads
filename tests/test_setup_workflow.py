"""
TASK-028: Tests for Corrected Campaign Setup Workflow
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch

from claude_agent_sdk.types import (
    AssistantMessage,
    ToolResultBlock,
    TextBlock,
    ToolUseBlock,
    UserMessage,
)
from src.workflows.setup_workflow import CampaignSetupWorkflow
from src.models.configuration import CampaignConfiguration
from src.models.enums import VerticalType, MonetizationModel

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_config():
    """Provides a mock CampaignConfiguration for tests."""
    return CampaignConfiguration(
        vertical_type=VerticalType.SERVICE,
        offer_name="Test Offer",
        target_audience_broad="Test Audience",
        value_proposition_primary="Test Value Prop",
        monetization_model=MonetizationModel.LEAD_GEN,
    )


def create_tool_result_block(tool_use_id, content_data, is_success):
    """Helper to create and modify a ToolResultBlock instance."""
    block = ToolResultBlock(tool_use_id=tool_use_id, content=json.dumps(content_data))
    # The is_success attribute is not part of the constructor
    block.is_success = is_success
    return block


async def mock_query_stream(*messages):
    """Helper to create an async generator from a list of messages."""
    for message in messages:
        yield message
        await asyncio.sleep(0)


@patch("src.workflows.setup_workflow.typer")
async def test_run_setup_success_flow(mock_typer, mock_config):
    """
    Tests the workflow where the agent successfully creates a campaign.
    """
    # Arrange
    mock_client = AsyncMock()
    mock_client.query.return_value = mock_query_stream(
        AssistantMessage(
            model="claude-3-opus-20240229",
            content=[
                TextBlock(text="Here is the campaign plan..."),
                ToolUseBlock(id="toolu_1234", name="create_campaign", input={}),
            ],
        ),
        UserMessage(content="yes"),  # Simulate user approving via CLI
        AssistantMessage(
            model="claude-3-opus-20240229",
            content=[
                create_tool_result_block(
                    "toolu_1234", {"campaign_id": "new-campaign-456"}, True
                )
            ],
        ),
    )

    workflow = CampaignSetupWorkflow()

    # Act
    result = await workflow.run_setup(mock_client, mock_config)

    # Assert
    assert result.status == "SUCCESS"
    assert result.campaign_id == "new-campaign-456"
    mock_client.query.assert_called_once()
    mock_typer.echo.assert_any_call("Here is the campaign plan...", nl=False)


@patch("src.workflows.setup_workflow.typer")
async def test_run_setup_tool_failure_flow(mock_typer, mock_config):
    """
    Tests the workflow where the campaign creation tool fails.
    """
    # Arrange
    mock_client = AsyncMock()
    mock_client.query.return_value = mock_query_stream(
        AssistantMessage(
            model="claude-3-opus-20240229",
            content=[
                TextBlock(text="Plan..."),
                ToolUseBlock(id="toolu_1234", name="create_campaign", input={}),
            ],
        ),
        UserMessage(content="yes"),
        AssistantMessage(
            model="claude-3-opus-20240229",
            content=[
                create_tool_result_block(
                    "toolu_1234", {"error": "API limit exceeded"}, False
                )
            ],
        ),
    )

    workflow = CampaignSetupWorkflow()

    # Act
    result = await workflow.run_setup(mock_client, mock_config)

    # Assert
    assert result.status == "FAILED"
    assert "API limit exceeded" in result.message


@patch("src.workflows.setup_workflow.typer")
async def test_run_setup_user_rejection_flow(mock_typer, mock_config):
    """
    Tests the workflow where the user rejects the plan.
    """
    # Arrange
    mock_client = AsyncMock()
    mock_client.query.return_value = mock_query_stream(
        AssistantMessage(
            model="claude-3-opus-20240229",
            content=[
                TextBlock(text="Here is the campaign plan..."),
                ToolUseBlock(id="toolu_1234", name="create_campaign", input={}),
            ],
        ),
        UserMessage(content="no"),
    )

    workflow = CampaignSetupWorkflow()

    # Act
    result = await workflow.run_setup(mock_client, mock_config)

    # Assert
    assert result.status == "ABORTED"
    assert "User did not approve" in result.message
