from pathlib import Path
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions


def load_system_prompt(prompt_name: str) -> str:
    """Loads a system prompt from the prompts directory."""
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / prompt_name
    with open(prompt_path, "r") as f:
        return f.read()


# Configure agent options
options = ClaudeAgentOptions(
    model="claude-3-5-sonnet-20241022",
    max_turns=30,
    system_prompt=load_system_prompt("google_ads_agent.txt"),
    permission_mode="ask",  # User approval for mutations
)

client = ClaudeSDKClient(options)
