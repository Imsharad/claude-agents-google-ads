# Implementation Ready: Phase 1 Kickoff Guide
**Date**: 2025-12-26
**Status**: ✅ Ready to Start Phase 1
**Research**: 28/35 questions answered (80% complete)

---

## 🎯 FINALIZED DECISIONS

### DECISION-001: TEXT-ONLY Assets ✅
- No image/video generation until Phase 4
- Focus on Search Network (headlines + descriptions only)
- Schema: `{headlines: [], descriptions: [], sitelinks: []}`

### DECISION-002: CLI-ONLY Interface ✅
- Interactive terminal UI using `typer` + `rich`
- No web framework, no Slack integration
- 30-40% faster development

### DECISION-004: Session Forking ✅
- Parallel strategy simulation (Conservative/Aggressive/Competitor)
- User picks strategy before spending money
- Unique competitive differentiator

---

## 📦 Tech Stack (Finalized)

**Core**:
- Python 3.10+
- `google-ads-python` v22+
- `claude-agent-sdk` (Anthropic)
- `pydantic` v2.x (schema validation)

**CLI**:
- `typer` or `click` (CLI framework)
- `rich` (terminal UI - tables, colors, progress bars)
- `inquirer` or `questionary` (interactive prompts)

**LLM & Prompts**:
- Claude Sonnet 4.5 (primary model)
- YAML + Jinja2 (prompt template management)

**Google Ads API**:
- Target: API v22 (skip v15-v21)
- OAuth2 with 6-day proactive refresh
- In-Process MCP Server (not subprocess)

**NOT in Scope** (Phase 1-3):
- ❌ Web framework (React/Vue/Flask)
- ❌ Slack API integration
- ❌ Image generation APIs (DALL-E, Stable Diffusion)
- ❌ Database (defer to Phase 2 for persistence)

---

## 🏗️ Architecture Patterns (From Research)

### 1. Claude SDK - In-Process MCP Server

**Pattern**: Shared OAuth state, no subprocess overhead

```python
from claude_agent_sdk import create_sdk_mcp_server, tool, ClaudeSDKClient, ClaudeAgentOptions
from google.ads.googleads.client import GoogleAdsClient

# Initialize Google Ads client ONCE (shared across all tools)
google_ads_client = GoogleAdsClient.load_from_storage("google-ads.yaml")

@tool
def get_campaign_metrics(customer_id: str, campaign_id: str) -> dict:
    """Fetch performance metrics for a campaign."""
    ga_service = google_ads_client.get_service("GoogleAdsService")

    gaql = f"""
        SELECT campaign.id, campaign.name, metrics.impressions,
               metrics.clicks, metrics.cost_micros
        FROM campaign
        WHERE campaign.id = {campaign_id}
    """

    response = ga_service.search(customer_id=customer_id, query=gaql)
    # Parse and return
    return {...}

@tool
def update_campaign_budget(customer_id: str, campaign_id: str, new_budget_micros: int) -> dict:
    """Update campaign daily budget."""
    campaign_service = google_ads_client.get_service("CampaignService")
    # Mutation logic
    return {"status": "success"}

# Create in-process MCP server
mcp_server = create_sdk_mcp_server(
    name="google_ads",
    tools=[get_campaign_metrics, update_campaign_budget, ...]
)

# Initialize agent
options = ClaudeAgentOptions(
    model="claude-sonnet-4-5",
    max_turns=30,
    system_prompt=load_prompt("prompts/optimizer_agent.yaml"),
    mcp_servers={"google_ads": mcp_server},
    allowed_tools=["mcp__google_ads__get_campaign_metrics", ...],
    permission_mode="custom"  # Use custom callback
)

client = ClaudeSDKClient(options)
```

**Why In-Process**:
- Shared `GoogleAdsClient` instance (OAuth handled once)
- No IPC overhead
- Simpler debugging

---

### 2. Permission System - Custom Callback

**Pattern**: 3-tier safety (Auto-Deny, Auto-Allow, Ask-Human)

```python
from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

def google_ads_permission_callback(tool_name: str, args: dict) -> PermissionResult:
    """
    Financial safety guardrail for Google Ads mutations.
    """

    # Tier 1: DENY - Destructive operations
    BLOCKED_TOOLS = ["DeleteCampaign", "DeleteAdGroup", "RemovePaymentMethod"]
    if tool_name in BLOCKED_TOOLS:
        return PermissionResultDeny(
            message="Destructive operations are permanently blocked."
        )

    # Tier 2: ALLOW - Read-only operations
    READ_ONLY = ["get_campaign_metrics", "search_keywords", "get_budget"]
    if tool_name in READ_ONLY:
        return PermissionResultAllow()

    # Tier 3: ASK - Budget changes (CLI prompt in Phase 1)
    if tool_name == "update_campaign_budget":
        budget_change = args.get("new_budget_micros", 0) - args.get("current_budget_micros", 0)
        budget_change_inr = budget_change / 1_000_000

        if budget_change_inr > 500:  # ₹500 threshold
            # In CLI: Prompt user
            from rich.prompt import Confirm
            approved = Confirm.ask(
                f"[yellow]Approve budget increase of ₹{budget_change_inr:.2f}?[/yellow]"
            )
            return PermissionResultAllow() if approved else PermissionResultDeny(message="User rejected")

        return PermissionResultAllow()  # Small changes auto-approved

    # Default: Deny unknown tools
    return PermissionResultDeny(message="Tool not authorized")

# Use in options
options = ClaudeAgentOptions(
    ...
    can_use_tool=google_ads_permission_callback
)
```

---

### 3. Daily Session Pattern

**Pattern**: New session per day, not single 7-day session

```python
from datetime import date

def start_daily_optimization():
    """Run daily optimization cycle."""

    today = date.today().isoformat()
    session_id = f"ads-optimization-{today}"

    # Load previous day summary (if exists)
    previous_summary = load_previous_summary(today)

    # Initial prompt with context
    initial_prompt = f"""
    Date: {today}
    Previous Day Summary: {previous_summary}

    Please review today's campaign performance and optimize as needed.
    Focus on:
    - Pausing keywords with CTR < 0.5% (7+ days)
    - Adjusting bids for high-performing keywords
    - Monitoring ₹2,000/day budget limit
    """

    # Create daily session
    options = ClaudeAgentOptions(
        session_id=session_id,  # Fresh session daily
        max_turns=30,
        ...
    )

    with ClaudeSDKClient(options) as client:
        for event in client.run(initial_prompt):
            # Process events, log to external DB
            log_event_to_db(session_id, event)

    # Save summary for tomorrow
    save_daily_summary(today, generate_summary(events))
```

**Why Daily Sessions**:
- Clean context window (no 7-day token accumulation)
- Isolated failures (Day 4 crash doesn't corrupt Day 1-3)
- Lower token costs

---

### 4. OAuth2 Proactive Refresh

**Pattern**: Refresh every 6 days (before 7-day expiration)

```python
import schedule
import time
from google.ads.googleads.client import GoogleAdsClient

def refresh_oauth_token():
    """Proactively refresh Google Ads OAuth token."""
    client = GoogleAdsClient.load_from_storage("google-ads.yaml")

    # Force refresh by making dummy API call
    customer_service = client.get_service("CustomerService")
    customer_service.list_accessible_customers()

    print(f"✅ Token refreshed at {datetime.utcnow()}")

# Schedule: Every 6 days (144 hours)
schedule.every(6).days.do(refresh_oauth_token)

while True:
    schedule.run_pending()
    time.sleep(3600)  # Check hourly
```

**Why 6 Days**:
- Google's refresh tokens expire after **7 days of inactivity**
- 6-day refresh ensures we never hit expiration

---

### 5. Prompt Templates - YAML + Jinja2

**Pattern**: Store in YAML, inject with Jinja2

```yaml
# prompts/persona_generation.yaml
system_prompt: |
  You are a marketing persona generator for Google Ads campaigns.
  Generate realistic buyer personas based on business context.

user_prompt: |
  Business: {{ business_name }}
  Vertical: {{ vertical }}
  Product: {{ product_description }}

  Generate 3 buyer personas with:
  - Name (e.g., "Status Seeker", "Budget Conscious")
  - Demographics (age range, income, location)
  - Pain points (3-5 specific problems)
  - Buying triggers (what makes them purchase NOW)
  - Search keywords (10-15 keywords they'd use)

  Output as JSON matching this schema:
  {{ persona_schema }}
```

```python
import yaml
from jinja2 import Template
from pydantic import BaseModel

class PersonaSchema(BaseModel):
    name: str
    age_range: str  # "25-35"
    pain_points: list[str]
    keywords: list[str]

def load_prompt(template_path: str, **kwargs) -> dict:
    """Load and render YAML prompt template."""
    with open(template_path) as f:
        template_data = yaml.safe_load(f)

    # Render user prompt with Jinja2
    user_template = Template(template_data["user_prompt"])
    user_prompt = user_template.render(**kwargs)

    return {
        "system": template_data["system_prompt"],
        "user": user_prompt
    }

# Usage
prompt = load_prompt(
    "prompts/persona_generation.yaml",
    business_name="CRM Software Inc.",
    vertical="SaaS",
    product_description="Cloud-based CRM for small teams",
    persona_schema=PersonaSchema.schema_json(indent=2)
)
```

---

### 6. Pydantic Schema Validation

**Pattern**: Validate all LLM outputs

```python
from pydantic import BaseModel, Field, validator
import json

class AdCopySchema(BaseModel):
    """Schema for AI-generated ad copy."""
    headlines: list[str] = Field(..., min_items=3, max_items=15)
    descriptions: list[str] = Field(..., min_items=2, max_items=4)

    @validator("headlines")
    def validate_headline_length(cls, v):
        """Google Ads headline limit: 30 characters."""
        for headline in v:
            if len(headline) > 30:
                raise ValueError(f"Headline too long: '{headline}' ({len(headline)} chars)")
        return v

    @validator("descriptions")
    def validate_description_length(cls, v):
        """Google Ads description limit: 90 characters."""
        for desc in v:
            if len(desc) > 90:
                raise ValueError(f"Description too long: '{desc}' ({len(desc)} chars)")
        return v

def generate_ad_copy(persona: dict, product: str) -> AdCopySchema:
    """Generate ad copy with schema validation."""

    # Call LLM
    response = claude_client.messages.create(
        model="claude-sonnet-4-5",
        messages=[{"role": "user", "content": f"Generate ad copy for {persona}"}]
    )

    # Parse and validate
    try:
        ad_data = json.loads(response.content[0].text)
        ad_copy = AdCopySchema(**ad_data)  # ← Pydantic validation
        return ad_copy
    except ValidationError as e:
        # Re-prompt with error details
        print(f"Validation failed: {e.json()}")
        return regenerate_with_feedback(persona, error=e)
```

---

### 7. Google Ads API v22 - Campaign Creation

**Pattern**: tCPA with warm-up strategy

```python
from google.ads.googleads.client import GoogleAdsClient
import uuid

def create_tcpa_campaign(
    client: GoogleAdsClient,
    customer_id: str,
    budget_resource_name: str,
    target_cpa_micros: int = 50_000_000  # ₹50
):
    """Create Search campaign with Target CPA bidding."""

    campaign_service = client.get_service("CampaignService")
    campaign_operation = client.get_type("CampaignOperation")
    campaign = campaign_operation.create

    # Campaign basics
    campaign.name = f"🚀_SaaS_FreeTrial_IN_Srch_Exact_{date.today().strftime('%Y%m%d')}"
    campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
    campaign.status = client.enums.CampaignStatusEnum.PAUSED  # Start paused
    campaign.campaign_budget = budget_resource_name

    # Bidding strategy: Maximize Conversions with Target CPA (v22)
    campaign.bidding_strategy_type = client.enums.BiddingStrategyTypeEnum.MAXIMIZE_CONVERSIONS
    campaign.maximize_conversions.target_cpa_micros = target_cpa_micros

    # Network settings (Search only)
    campaign.network_settings.target_google_search = True
    campaign.network_settings.target_search_network = True
    campaign.network_settings.target_content_network = False  # No Display

    # Create campaign
    response = campaign_service.mutate_campaigns(
        customer_id=customer_id,
        operations=[campaign_operation]
    )

    return response.results[0].resource_name
```

**v22 Breaking Changes** (from research):
- `MAXIMIZE_CONVERSIONS` + `target_cpa_micros` field (not separate strategy)
- "Targetless" optimization available (`OPTIMIZE_WITHOUT_TARGET...`)
- `validate_only=True` for policy pre-flight checks

---

### 8. Golden Ratio Circuit Breaker

**Pattern**: Hourly watchdog with 1.2x safety margin

```python
def check_circuit_breaker(client: GoogleAdsClient, customer_id: str):
    """Hourly job: Pause campaigns exceeding ₹2,000/day."""

    HARD_LIMIT_RATIO = 1.2
    ACCOUNT_LIMIT_MICROS = 2_000_000_000  # ₹2,000

    ga_service = client.get_service("GoogleAdsService")

    # Query today's spend
    gaql = """
        SELECT campaign.id, campaign.name, metrics.cost_micros
        FROM campaign
        WHERE campaign.status = 'ENABLED'
          AND segments.date = TODAY
    """

    response = ga_service.search(customer_id=customer_id, query=gaql)

    for row in response:
        spend_today = row.metrics.cost_micros

        # Check against 1.2x limit (₹2,400)
        if spend_today > (ACCOUNT_LIMIT_MICROS * HARD_LIMIT_RATIO):
            # Pause campaign
            campaign_service = client.get_service("CampaignService")
            operation = client.get_type("CampaignOperation")
            operation.update.resource_name = row.campaign.resource_name
            operation.update.status = client.enums.CampaignStatusEnum.PAUSED
            operation.update_mask.paths.append("status")

            campaign_service.mutate_campaigns(
                customer_id=customer_id,
                operations=[operation]
            )

            # Apply label for tracking
            apply_label(row.campaign.resource_name, "Circuit_Breaker_Paused")

            print(f"⚠️ PAUSED: {row.campaign.name} at ₹{spend_today/1_000_000:.2f}")
```

**Run**: Hourly cron job or within agent loop

---

### 9. CLI Approval Workflow

**Pattern**: Interactive terminal prompts

```python
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
import typer

app = typer.Typer()
console = Console()

@app.command()
def optimize(vertical: str = "saas", offer: str = "free-trial"):
    """Generate and approve campaigns."""

    console.print("\n🤖 [bold]Growth-Tier Ads Agent v1.0[/bold]")
    console.print("━" * 60)

    # Generate campaigns
    with console.status("[bold green]Generating campaigns..."):
        campaigns = agent.generate_campaigns(vertical=vertical, offer=offer)

    console.print(f"\n✅ Generated {len(campaigns)} campaigns\n")
    console.print("━" * 60)

    # Display campaigns
    for i, campaign in enumerate(campaigns, 1):
        console.print(f"\n[bold]CAMPAIGN {i}:[/bold] {campaign.name}")
        console.print(f"Budget: ₹{campaign.budget}/day")
        console.print(f"Bidding: {campaign.bidding_strategy}\n")

        for ad_group in campaign.ad_groups:
            table = Table(title=ad_group.name)
            table.add_column("Headlines", style="cyan")
            for headline in ad_group.headlines:
                table.add_row(headline)
            console.print(table)

    console.print("━" * 60)

    # Approval prompt
    choice = Prompt.ask(
        "\nActions",
        choices=["A", "E", "R", "V", "Q"],
        default="A"
    )

    if choice == "A":
        # Approve all
        if Confirm.ask(f"Create {len(campaigns)} campaigns in Google Ads?"):
            with console.status("[bold green]Creating campaigns..."):
                results = google_ads_client.create_campaigns(campaigns)
            console.print("\n✅ [bold green]All campaigns created successfully![/bold green]")

            # Display campaign IDs
            for result in results:
                console.print(f"  - {result.campaign_name}: {result.campaign_id}")

            console.print("\n🔄 Starting 7-day autonomous monitoring...")

    elif choice == "E":
        # Edit flow
        campaign_num = Prompt.ask("Which campaign?", choices=[str(i) for i in range(1, len(campaigns)+1)])
        # Edit logic...

    elif choice == "R":
        # Reject flow
        console.print("[yellow]Campaigns rejected. No changes made.[/yellow]")

if __name__ == "__main__":
    app()
```

---

## 📋 Phase 1 Tasks (Ready to Start)

### TASK-010: Python Environment Setup
**Status**: ✅ Ready
**Estimated**: 2-3 hours

```bash
# Create project
mkdir google-ads-agent && cd google-ads-agent
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install google-ads-python==22.1.0
pip install anthropic
pip install claude-agent-sdk
pip install pydantic==2.5.0
pip install typer rich inquirer
pip install pyyaml jinja2
pip install python-dotenv

# Save requirements
pip freeze > requirements.txt

# Create directory structure
mkdir -p src/{agents,tools,prompts,schemas}
touch src/__init__.py
```

---

### TASK-011: OAuth2 Setup
**Status**: ✅ Ready
**Estimated**: 3-4 hours

1. Create Google Ads developer token
2. Setup OAuth2 credentials (Web Application)
3. Generate refresh token using `google-ads-python` auth flow
4. Create `google-ads.yaml`:

```yaml
developer_token: "YOUR_DEVELOPER_TOKEN"
client_id: "YOUR_CLIENT_ID"
client_secret: "YOUR_CLIENT_SECRET"
refresh_token: "YOUR_REFRESH_TOKEN"
login_customer_id: "1234567890"
use_proto_plus: True
```

5. Test connection:

```python
from google.ads.googleads.client import GoogleAdsClient

client = GoogleAdsClient.load_from_storage("google-ads.yaml")
customer_service = client.get_service("CustomerService")
customers = customer_service.list_accessible_customers()
print(f"✅ Connected to {len(customers.resource_names)} accounts")
```

6. Implement 6-day proactive refresh (see pattern #4 above)

---

### TASK-012: Pydantic Models
**Status**: ✅ Ready
**Estimated**: 4-5 hours

Create `src/schemas/` with:

**campaign.py**:
```python
from pydantic import BaseModel, Field
from typing import Literal

class CampaignConfig(BaseModel):
    vertical: Literal["SAAS", "EDUCATION", "SERVICE", "ECOMMERCE"]
    offer_name: str
    target_audience: str
    budget_daily_micros: int = 2_000_000_000  # ₹2,000
    bidding_strategy: Literal["TARGET_CPA", "TARGET_ROAS", "MAX_CLICKS"]
```

**persona.py**:
```python
class PersonaSchema(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    age_range: str = Field(..., regex=r"^\d{2}-\d{2}$")
    pain_points: list[str] = Field(..., min_items=3, max_items=5)
    keywords: list[str] = Field(..., min_items=10, max_items=15)
```

**ad_copy.py**:
```python
class AdCopySchema(BaseModel):
    headlines: list[str] = Field(..., min_items=3, max_items=15)
    descriptions: list[str] = Field(..., min_items=2, max_items=4)

    @validator("headlines")
    def validate_headline_length(cls, v):
        for h in v:
            if len(h) > 30:
                raise ValueError(f"Headline too long: {h}")
        return v
```

---

### TASK-013: GAQL Query Builder
**Status**: ✅ Ready
**Estimated**: 3-4 hours

Create `src/tools/gaql.py`:

```python
def get_campaign_performance(
    customer_id: str,
    date_range: str = "LAST_30_DAYS"
) -> list[dict]:
    """Fetch campaign performance metrics."""

    gaql = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr
        FROM campaign
        WHERE segments.date DURING {date_range}
        ORDER BY metrics.cost_micros DESC
        LIMIT 100
    """

    ga_service = client.get_service("GoogleAdsService")
    response = ga_service.search(customer_id=customer_id, query=gaql)

    results = []
    for row in response:
        results.append({
            "id": row.campaign.id,
            "name": row.campaign.name,
            "status": row.campaign.status.name,
            "impressions": row.metrics.impressions,
            "clicks": row.metrics.clicks,
            "cost_inr": row.metrics.cost_micros / 1_000_000,
            "conversions": row.metrics.conversions,
            "ctr": row.metrics.ctr
        })

    return results
```

---

## 🚀 Next Steps (Your Action)

**Immediate**:
1. ✅ Review DECISIONS.md (critical product choices)
2. ✅ Review this IMPLEMENTATION_READY.md (code patterns)
3. ✅ Start TASK-010 (Python environment setup)

**Within 24 Hours**:
1. Complete TASK-011 (OAuth2 setup)
2. Complete TASK-012 (Pydantic models)
3. Complete TASK-013 (GAQL query builder)

**Phase 1 Timeline**: 2-3 weeks
**Phase 1 Exit Criteria**: 80% test coverage, validated Google Ads API connection, working CLI prototype

---

## 📞 Questions or Blockers?

If you hit any blockers:
1. Check research_summary.md for detailed explanations
2. Check DECISIONS.md for rationale behind choices
3. Prompt 5 (Production/Deployment) still needed for Phase 3 (can do in parallel with Phase 1)

---

**Status**: ✅ **You are UNBLOCKED. Start Phase 1 now!**
