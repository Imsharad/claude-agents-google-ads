"""
TASK-028: Implement Campaign Setup Workflow with User Approval (Corrected)

This version correctly uses the claude-agent-sdk's message streaming
and built-in CLI permission handling.
"""
import typer
import json
from typing import Optional

from claude_agent_sdk.client import ClaudeSDKClient
from claude_agent_sdk.types import (
    Message,
    ToolResultBlock,
    TextBlock,
    AssistantMessage,
    UserMessage,
)
from src.models.configuration import CampaignConfiguration
from pydantic import BaseModel

class CampaignResult(BaseModel):
    campaign_id: Optional[str] = None
    status: str
    message: Optional[str] = None

class CampaignSetupWorkflow:
    """
    Orchestrates the campaign setup process using the Claude Agent SDK.
    Relies on the SDK's built-in `permission_mode='cli'` for user approval.
    """

    async def run_setup(
        self, client: ClaudeSDKClient, config: CampaignConfiguration
    ) -> CampaignResult:
        """
        Main entry point for the campaign setup workflow.
        """
        typer.echo("Initializing campaign setup with automatic CLI approval...")

        prompt = (
            "You are a Google Ads expert. Your task is to generate a complete "
            "campaign plan and then use the available tools to create it. "
            "Start by outlining the campaign structure, keywords, negative keywords, "
            "and ad copy. Wait for user approval before creating the campaign.\n\n"
            f"Here is the configuration:\n- Offer: {config.offer_name}\n"
            f"- Vertical: {config.vertical_type}\n"
            f"- Target Audience: {config.target_audience_broad}\n"
            f"- Value Proposition: {config.value_proposition_primary}\n"
            f"- Monetization Model: {config.monetization_model}"
        )

        final_message: Optional[Message] = None
        async for message in await client.query(prompt, permission_mode="cli"):
            final_message = message
            if isinstance(message, AssistantMessage):
                for content in message.content:
                    if isinstance(content, TextBlock):
                        typer.echo(content.text, nl=False)

        # After the stream ends, inspect the final message for a tool result
        if isinstance(final_message, AssistantMessage):
            for content in final_message.content:
                if isinstance(content, ToolResultBlock):
                    try:
                        result_data = json.loads(content.content)
                    except (json.JSONDecodeError, TypeError):
                        result_data = {}

                    if content.is_success:
                        return CampaignResult(
                            campaign_id=str(result_data.get("campaign_id", "")),
                            status="SUCCESS",
                            message="Campaign created successfully!",
                        )
                    else:
                        error_message = result_data.get('error', 'Unknown error')
                        return CampaignResult(
                            status="FAILED",
                            message=f"Campaign creation tool failed: {error_message}",
                        )

        # Handle cases where the agent finishes without using a tool or stream is empty
        if final_message:
             # The last message might be the user's "yes" or "no"
            return CampaignResult(
                status="ABORTED", message="User did not approve the campaign creation."
            )

        return CampaignResult(
            status="ABORTED", message="Agent finished without creating a campaign."
        )


async def run_setup(
    client: ClaudeSDKClient, config: CampaignConfiguration
) -> CampaignResult:
    """
    Main entry point for the campaign setup workflow.
    """
    workflow = CampaignSetupWorkflow()
    return await workflow.run_setup(client, config)
