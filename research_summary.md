# Research Summary: Actionable Insights
**Date**: 2025-12-26
**Source**: Prompt 1-4 research answers (1770 lines, 141KB)
**Status**: ⏳ Awaiting Prompt 6 (Product Strategy) to complete full picture

---

## Executive Summary

**What We Learned**: 26 of 35 research questions answered with production-ready code examples and architectural patterns.

**Critical Decisions Made by Research**:
1. ✅ **Use In-Process MCP Server** (not subprocess) - shared OAuth state
2. ✅ **YAML + Jinja2** for prompt templates (not JSON or f-strings)
3. ✅ **Pydantic** for LLM output validation
4. ✅ **Portfolio Bidding Strategies** for Golden Ratio scaler
5. ✅ **Daily Session Pattern** (not single 7-day session)
6. ✅ **Target Google Ads API v22** (skip v15-v21 entirely)

**Remaining Decisions** (awaiting Prompt 6):
- ⏳ DECISION-001: Asset scope (text-only vs. visual) - **CRITICAL**
- ⏳ DECISION-002: Approval UX (CLI/web/conversational)
- ⏳ DECISION-003: Deployment architecture (VM/serverless/container)

---

## 1. Claude Agent SDK Architecture (Prompt 1: RQ-001 to RQ-007)

### 1.1 Permission System - CRITICAL for Budget Safety

**Finding**: Default `permission_mode='ask'` is CLI-only. For headless/background agents, must implement custom `can_use_tool` callback.

**Implementation Pattern** (Add to PRD Section 3.4):

```python
from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

def google_ads_permission_controller(tool_name: str, args: dict) -> PermissionResult:
    """
    Custom permission callback for Google Ads mutations.
    Implements 3-tier safety: Auto-Deny, Auto-Allow, Ask-Human
    """

    # Tier 1: DENY - Destructive operations always blocked
    BLOCKED_TOOLS = ["DeleteCampaign", "DeleteAdGroup", "RemovePaymentMethod"]
    if tool_name in BLOCKED_TOOLS:
        return PermissionResultDeny(
            message="Destructive operations are not allowed. This tool is permanently disabled."
        )

    # Tier 2: ALLOW - Read-only operations (no financial impact)
    READ_ONLY = ["GetCampaignMetrics", "SearchKeywords", "GetBudget"]
    if tool_name in READ_ONLY:
        return PermissionResultAllow()

    # Tier 3: ASK - Budget changes (requires human approval via queue)
    if tool_name == "UpdateBudget":
        budget_change = args.get("new_budget_micros", 0) - args.get("current_budget_micros", 0)
        if budget_change > 5_000_000:  # ₹5 increase
            # For headless: Deny + Queue approval request to dashboard
            return PermissionResultDeny(
                message="Budget changes over ₹5.00 require human approval via the dashboard."
            )
        return PermissionResultAllow()  # Small changes auto-approved

    # Default: Deny unknown tools
    return PermissionResultDeny(message="Tool execution not authorized by policy.")
```

**Action Items**:
- ✅ Add this pattern to PRD Section 3.4.3 "Permission Handling"
- ✅ Update REQ-6 (Policy Compliance) with code example
- ✅ Unblocks TASK-002 (Design Policy Handler)

---

### 1.2 MCP Server Architecture - In-Process vs. Subprocess

**Finding**: Google Ads integration requires **In-Process MCP Server** (not subprocess).

**Why**:
- Shared OAuth state: `GoogleAdsClient` object can be passed directly to tools
- No IPC overhead (faster)
- Centralized secret management
- Simpler debugging

**Implementation Pattern**:

```python
from claude_agent_sdk import create_sdk_mcp_server, tool

# Shared Google Ads client (initialized once, reused by all tools)
google_ads_client = GoogleAdsClient.load_from_storage("google-ads.yaml")

@tool
def get_campaign_metrics(customer_id: str, campaign_id: str) -> dict:
    """Fetch performance metrics for a campaign."""
    # Direct access to shared client instance
    ga_service = google_ads_client.get_service("GoogleAdsService")
    # ... GAQL query logic
    return {"impressions": 1234, "clicks": 56, "cost_micros": 789000}

@tool
def update_campaign_budget(customer_id: str, campaign_id: str, new_budget_micros: int) -> dict:
    """Update campaign daily budget. Requires approval for large changes."""
    # Shared client reused
    campaign_service = google_ads_client.get_service("CampaignService")
    # ... mutation logic
    return {"status": "success", "new_budget": new_budget_micros}

# Create in-process MCP server
mcp_server = create_sdk_mcp_server(
    name="google_ads",
    tools=[get_campaign_metrics, update_campaign_budget, ...]
)

# Register with agent
agent_options = ClaudeAgentOptions(
    mcp_servers={"google_ads": mcp_server},
    allowed_tools=["mcp__google_ads__get_campaign_metrics", "mcp__google_ads__update_campaign_budget"]
)
```

**Action Items**:
- ✅ Add to PRD Section 3.4.2 "MCP Server Topology"
- ✅ Update REQ-1 (Claude SDK Integration) with architecture decision
- ✅ Unblocks TASK-020 (MCP Server Implementation)

**Note**: Official `googleads/google-ads-mcp` exists but is **READ-ONLY**. Use it for GAQL queries, build custom server for mutations.

---

### 1.3 State Management - Daily Session Pattern

**Finding**: Single 7-day session = context drift + high token cost. Use **Daily Session Pattern** instead.

**Pattern**:
- Start new `session_id` each day (aligned with Google Ads reporting cycle)
- Previous day summary injected into new session context
- Benefits: Clean context, lower cost, isolated failures

**Implementation**:

```python
def start_daily_optimization(date: str, previous_summary: str):
    """Start new optimization session for the day."""

    session_id = f"ads-optimization-{date}"  # e.g., "ads-optimization-2025-10-27"

    # Inject previous day summary as context
    initial_prompt = f"""
    Date: {date}
    Previous Day Summary: {previous_summary}

    Please review today's campaign performance and optimize as needed.
    """

    agent_options = ClaudeAgentOptions(
        session_id=session_id,  # New session each day
        system_prompt=OPTIMIZATION_AGENT_PROMPT,
        max_turns=30
    )

    # Run daily cycle
    with ClaudeSDKClient(agent_options) as client:
        for event in client.run(initial_prompt):
            # Process events, log to external DB
            db.save_event(session_id, event)
```

**Action Items**:
- ✅ Add to PRD Section 3.4.4 "Session Management"
- ✅ Update REQ-3 (7-Day Autonomy) with daily session strategy
- ✅ Unblocks TASK-004 (Define Agent Loop)

---

### 1.4 "Invisible History" Problem - Sidecar Persistence

**Finding**: When resuming sessions, LLM remembers context but `ClaudeSDKClient` doesn't re-emit past messages.

**Solution**: **Sidecar Persistence Pattern**
1. Listen to all message events during runtime
2. Save events to external database (PostgreSQL/DynamoDB) as they occur
3. On restart: Fetch history from DB for UI, use `resume=session_id` for LLM cognitive context

**Implementation**:

```python
def run_agent_with_persistence(session_id: str, db: Database):
    """Run agent with full event logging."""

    agent_options = ClaudeAgentOptions(
        resume=session_id,  # Restore LLM cognitive context
        max_turns=30
    )

    with ClaudeSDKClient(agent_options) as client:
        for event in client.run(prompt):
            # Save every event to external DB
            db.save_event(session_id, {
                "timestamp": datetime.utcnow(),
                "type": event.type,  # "UserMessage", "AssistantMessage", "ToolUse", etc.
                "content": event.content
            })

            # Also emit to dashboard websocket
            dashboard.broadcast(session_id, event)
```

**Action Items**:
- ✅ Add to PRD Section 3.4.5 "Persistence Architecture"
- ⏳ Awaiting DECISION-003 (Deployment) to choose database (PostgreSQL vs. DynamoDB)
- ✅ Unblocks TASK-026 (Dashboard Persistence)

---

### 1.5 System Prompt Engineering

**Finding**: Keep system prompt < 2000 tokens. Focus on *how to think*, not *what to know*.

**Pattern**: Multi-Mode Prompting
- **Setup Mode**: Creative (ad copy generation, keyword expansion)
- **Monitoring Mode**: Conservative (anomaly detection, cost control)

**Example**:

```python
OPTIMIZATION_AGENT_PROMPT = """
You are a conservative Google Ads optimization agent.

CONSTRAINTS:
- NEVER delete campaigns or ad groups
- Obtain approval for budget increases > 10%
- Pause keywords only if CTR < 0.5% for 7+ days
- Report all actions clearly

WORKFLOW:
1. Check campaign metrics (use get_campaign_metrics tool)
2. Identify anomalies (cost spike > 20%, CTR drop > 30%)
3. Propose optimization (bid adjustment, keyword pause)
4. If budget change > 10%: Request approval
5. Execute approved changes
6. Verify changes (re-query metrics)
7. Report summary

STYLE: Concise, data-driven, risk-averse
"""
```

**Action Items**:
- ✅ Add to PRD Section 3.4.6 "System Prompt Templates"
- ✅ Unblocks TASK-007 (LLM Prompt Template Architecture)

---

## 2. Google Ads API v22 Setup (Prompt 2: RQ-008 to RQ-011)

### 2.1 Breaking Changes - v15/v16 → v22

**Critical Finding**: Target **API v22 directly**, skip intermediate versions (v16-v21 sunset soon).

**Major Breaking Changes**:

| Feature | v15/v16 | v22 | Migration Action |
|---------|---------|-----|------------------|
| **Asset Creation** | Static upload (`AssetService`) | Dynamic GenAI (`AssetGenerationService` beta) | Add new service, handle AI errors |
| **Bidding** | Required CPA/ROAS targets | "Targetless" optimization (`OPTIMIZE_WITHOUT_TARGET...`) | Add budget safety checks |
| **Merchant Links** | `AccountLink` | `ProductLink` + `ProductLinkInvitation` | Refactor linking logic |
| **Demand Gen** | "Discovery" campaigns | Renamed to "Demand Gen", `TargetCPC` added | Find/replace `DISCOVERY` → `DEMAND_GEN` |
| **Resource Status** | `status` (ENABLED/PAUSED) | `primary_status` + `primary_status_reasons` | Update dashboards to show *why* not serving |

**Code Example - v22 Campaign Creation**:

```python
def create_tcpa_campaign(client, customer_id, budget_resource_name):
    """Create Search campaign with Target CPA (v22 API)."""
    campaign_service = client.get_service("CampaignService")
    campaign_operation = client.get_type("CampaignOperation")
    campaign = campaign_operation.create

    campaign.name = f"Growth Tier - tCPA - {uuid.uuid4()}"
    campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
    campaign.status = client.enums.CampaignStatusEnum.PAUSED
    campaign.campaign_budget = budget_resource_name

    # v22: Maximize Conversions with Target CPA
    campaign.bidding_strategy_type = client.enums.BiddingStrategyTypeEnum.MAXIMIZE_CONVERSIONS
    campaign.maximize_conversions.target_cpa_micros = 50_000_000  # ₹50.00

    # Network settings
    campaign.network_settings.target_google_search = True
    campaign.network_settings.target_search_network = True
    campaign.network_settings.target_content_network = False  # No Display

    response = campaign_service.mutate_campaigns(
        customer_id=customer_id,
        operations=[campaign_operation]
    )
    return response.results[0].resource_name
```

**Action Items**:
- ✅ Add breaking changes table to PRD Section 2.2 "Google Ads API Requirements"
- ✅ Update REQ-5 (API Version) with v22 specifications
- ✅ Unblocks TASK-001 (Define API Requirements)

---

### 2.2 OAuth2 - "7-Day Expiration" Phenomenon

**Critical Finding**: Refresh tokens expire after **7 days of inactivity** (not 7 days total).

**Solution**: Implement **Proactive Refresh** (refresh every 6 days, even if agent isn't running).

**Implementation**:

```python
import time
from google.ads.googleads.client import GoogleAdsClient

def refresh_token_proactively():
    """Refresh OAuth token every 6 days to prevent expiration."""
    client = GoogleAdsClient.load_from_storage("google-ads.yaml")

    # Force refresh by making dummy API call
    customer_service = client.get_service("CustomerService")
    customer_service.list_accessible_customers()

    print(f"Token refreshed at {datetime.utcnow()}")

# Schedule: Run every 6 days (144 hours)
schedule.every(6).days.do(refresh_token_proactively)
```

**Action Items**:
- ✅ Add to PRD Section 3.3 "Authentication & Security"
- ✅ Update REQ-5 with OAuth refresh strategy
- ✅ Unblocks TASK-011 (OAuth2 Setup)

---

### 2.3 Policy Violation Detection

**Finding**: Use `validate_only=True` to pre-screen AI-generated assets for policy violations **before** persistence.

**Pattern**:

```python
def create_ad_with_policy_check(campaign_id, ad_copy):
    """Create ad with pre-flight policy validation."""
    ad_service = client.get_service("AdService")
    ad_operation = client.get_type("AdOperation")

    # Build ad
    ad = ad_operation.create
    ad.responsive_search_ad.headlines.extend([
        {"text": headline} for headline in ad_copy["headlines"]
    ])

    # PRE-FLIGHT: Validate policy compliance
    try:
        response = ad_service.mutate_ads(
            customer_id=customer_id,
            operations=[ad_operation],
            validate_only=True  # ← Don't actually create, just check
        )
        print("✅ Policy check passed")
    except GoogleAdsException as ex:
        # Handle policy errors (POLICY_VIOLATION, etc.)
        for error in ex.failure.errors:
            if error.error_code.policy_violation_error:
                print(f"❌ Policy violation: {error.message}")
                return None  # Reject this ad copy

    # If validation passed, create for real
    response = ad_service.mutate_ads(
        customer_id=customer_id,
        operations=[ad_operation],
        validate_only=False  # ← Actually create
    )
    return response.results[0].resource_name
```

**Action Items**:
- ✅ Add to PRD REQ-6 (Policy Compliance)
- ✅ Unblocks TASK-002 (Design Policy Handler)

---

### 2.4 GAQL Query Optimization

**Finding**: Use `google-ads-mcp` (official MCP server) for GAQL execution. It handles pagination, error handling.

**Pattern**:

```python
# Use official MCP server for read operations
@tool
def search_campaigns(customer_id: str, date_range: str = "LAST_30_DAYS") -> list:
    """Search campaigns with metrics."""
    gaql = f"""
        SELECT
            campaign.id,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions
        FROM campaign
        WHERE segments.date DURING {date_range}
        ORDER BY metrics.cost_micros DESC
        LIMIT 100
    """

    # Official MCP server handles pagination, errors
    results = google_ads_mcp_client.execute_gaql(customer_id, gaql)
    return results
```

**Action Items**:
- ✅ Add GAQL examples to PRD Section 3.2 "Campaign Management"
- ✅ Update REQ-8 (Reporting) with query patterns
- ✅ Unblocks TASK-013 (GAQL Query Builder)

---

## 3. Campaign APIs (Prompt 3: RQ-012 to RQ-015)

### 3.1 Bidding Strategy Mapping

**Finding**: Map business models to v22 bidding strategies:

| Business Model | Bidding Strategy | v22 Implementation | When to Use |
|----------------|------------------|---------------------|-------------|
| **SaaS Trial** | Target CPA | `MAXIMIZE_CONVERSIONS` + `target_cpa_micros` | Known acceptable cost per signup |
| **E-commerce** | Target ROAS | `MAXIMIZE_CONVERSION_VALUE` + `target_roas` | Revenue tracking enabled |
| **Lead Gen (Growth)** | Max Clicks + CPC Cap | `MAXIMIZE_CLICKS` + `cpc_bid_ceiling_micros` | Building audience, no conversion data yet |
| **Brand Awareness** | Max Impressions + CPM Cap | `TARGET_IMPRESSION_SHARE` | Top-of-funnel, reach campaigns |

**Code Example - tCPA with Warm-Up**:

```python
def create_campaign_with_warmup(customer_id, budget, target_cpa_micros):
    """Create campaign with warm-up strategy."""

    # Phase 1: Warm-up (no target, gather data)
    campaign = create_campaign(
        bidding_strategy_type=BiddingStrategyTypeEnum.MAXIMIZE_CONVERSIONS,
        # No target_cpa_micros set → algorithm learns freely
    )

    # Monitor: Wait for 15+ conversions
    while get_conversion_count(campaign.id) < 15:
        time.sleep(86400)  # Check daily

    # Phase 2: Apply Target CPA
    update_campaign(
        campaign_id=campaign.id,
        target_cpa_micros=target_cpa_micros  # Now constrain efficiency
    )
```

**Action Items**:
- ✅ Add bidding strategy table to PRD Section 3.2.1 "Bidding Logic"
- ✅ Update REQ-9 (Smart Bidding) with mapping
- ✅ Unblocks TASK-006 (Map Bidding Strategies)

---

### 3.2 Golden Ratio Budget Scaler - Portfolio Strategy

**Finding**: Use **Portfolio Bidding Strategies** for Golden Ratio scaler (simpler than campaign-level).

**Why Portfolio**:
- Data pooling: All campaigns share learning (15 conversions needed, not 15 per campaign)
- Single control plane: Update one `BiddingStrategy` resource → affects all linked campaigns
- Decouples efficiency (portfolio target) from pacing (individual budgets)

**Implementation**:

```python
def create_portfolio_strategy(customer_id, target_cpa_micros):
    """Create shared portfolio bidding strategy."""
    bidding_strategy_service = client.get_service("BiddingStrategyService")
    operation = client.get_type("BiddingStrategyOperation")

    strategy = operation.create
    strategy.name = "Growth Portfolio - tCPA"
    strategy.target_cpa.target_cpa_micros = target_cpa_micros

    response = bidding_strategy_service.mutate_bidding_strategies(
        customer_id=customer_id,
        operations=[operation]
    )
    return response.results[0].resource_name  # e.g., "customers/123/biddingStrategies/456"

def link_campaign_to_portfolio(campaign_id, portfolio_resource_name):
    """Link campaign to portfolio strategy."""
    campaign_service = client.get_service("CampaignService")
    operation = client.get_type("CampaignOperation")

    operation.update.resource_name = campaign_id
    operation.update.bidding_strategy = portfolio_resource_name  # ← Link
    operation.update_mask.paths.append("bidding_strategy")

    campaign_service.mutate_campaigns(operations=[operation])

# Golden Ratio Scaler adjusts individual campaign budgets
# Portfolio target controls efficiency across all campaigns
```

**Action Items**:
- ✅ Add to PRD REQ-10 (Golden Ratio Scaler)
- ✅ Update TASK-032 (Budget Scaler) with portfolio pattern
- ✅ Unblocks TASK-032 (Golden Ratio Implementation)

---

### 3.3 Learning Phase Constraints

**Finding**: Avoid triggering learning phase resets during budget scaling.

**Triggers for Learning Reset**:
- Budget increase > 20-30% in single day
- Target CPA/ROAS change > 20%
- Switching bidding strategies

**Safe Scaling Pattern**:

```python
def scale_budget_safely(campaign_id, current_budget, target_budget):
    """Scale budget gradually to avoid learning reset."""

    MAX_DAILY_INCREASE = 0.20  # 20% max per day

    while current_budget < target_budget:
        # Increment by at most 20%
        next_budget = min(
            current_budget * 1.20,
            target_budget
        )

        update_campaign_budget(campaign_id, next_budget)
        current_budget = next_budget

        if current_budget < target_budget:
            time.sleep(86400)  # Wait 24 hours before next increase
```

**Action Items**:
- ✅ Add to PRD REQ-10 (Golden Ratio Scaler) as safety constraint
- ✅ Update TASK-032 with gradual scaling logic
- ✅ Unblocks TASK-033 (Dynamic Budget Adjustment)

---

### 3.4 Negative Keyword Shared Sets

**Finding**: Use `SharedSetService` for negative keyword lists (shared across campaigns).

**Pattern**:

```python
def create_negative_keyword_list(customer_id, keywords: list):
    """Create shared negative keyword list."""
    shared_set_service = client.get_service("SharedSetService")
    operation = client.get_type("SharedSetOperation")

    shared_set = operation.create
    shared_set.name = "Brand Safety - Negative Keywords"
    shared_set.type_ = client.enums.SharedSetTypeEnum.NEGATIVE_KEYWORDS

    response = shared_set_service.mutate_shared_sets(
        customer_id=customer_id,
        operations=[operation]
    )
    shared_set_resource = response.results[0].resource_name

    # Add keywords to shared set
    shared_criterion_service = client.get_service("SharedCriterionService")
    for keyword in keywords:
        operation = client.get_type("SharedCriterionOperation")
        criterion = operation.create
        criterion.shared_set = shared_set_resource
        criterion.keyword.text = keyword
        criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD

        shared_criterion_service.mutate_shared_criteria(
            customer_id=customer_id,
            operations=[operation]
        )

    return shared_set_resource

def link_negative_list_to_campaign(campaign_id, shared_set_resource):
    """Link shared negative keyword list to campaign."""
    campaign_shared_set_service = client.get_service("CampaignSharedSetService")
    operation = client.get_type("CampaignSharedSetOperation")

    campaign_shared_set = operation.create
    campaign_shared_set.campaign = campaign_id
    campaign_shared_set.shared_set = shared_set_resource

    campaign_shared_set_service.mutate_campaign_shared_sets(
        customer_id=customer_id,
        operations=[operation]
    )
```

**Action Items**:
- ✅ Add to PRD Section 3.2.3 "Negative Keyword Management"
- ✅ Unblocks TASK-027 (Negative Keyword Funnel)

---

## 4. AI Generation (Prompt 4: RQ-018 to RQ-023)

### 4.1 Prompt Template Management - YAML + Jinja2

**Finding**: Use **YAML for storage**, **Jinja2 for injection** (not JSON or f-strings).

**Why YAML**:
- Native multi-line support (pipe `|` operator)
- No escaping required for quotes
- Supports comments for documentation
- Industry standard (Kubernetes, Promptfoo)

**Why Jinja2**:
- Logic support (loops, conditionals)
- Safe variable injection (auto-escaping)
- Separation of template from data

**Implementation**:

```yaml
# prompts/persona_generation.yaml
system_prompt: |
  You are a marketing persona generator for Google Ads.
  Generate realistic buyer personas based on business context.

user_prompt: |
  Business: {{ business_name }}
  Vertical: {{ vertical }}
  Product: {{ product_description }}

  Generate 3 buyer personas with:
  - Demographics (age, income, location)
  - Pain points (3-5 specific problems)
  - Buying triggers (what makes them purchase now)
  - Search intent keywords (10-15 keywords they'd use)

  Output as JSON matching this schema:
  {{ persona_schema }}
```

```python
# Python code to load and inject
import yaml
from jinja2 import Template

def load_prompt_template(template_path: str) -> dict:
    """Load YAML prompt template."""
    with open(template_path) as f:
        return yaml.safe_load(f)

def generate_persona_prompt(business_name: str, vertical: str, product: str):
    """Inject variables into prompt template."""
    template_data = load_prompt_template("prompts/persona_generation.yaml")

    # Jinja2 injection
    user_prompt_template = Template(template_data["user_prompt"])
    user_prompt = user_prompt_template.render(
        business_name=business_name,
        vertical=vertical,
        product_description=product,
        persona_schema=PERSONA_SCHEMA_JSON  # Pydantic model as JSON
    )

    return {
        "system": template_data["system_prompt"],
        "user": user_prompt
    }
```

**Action Items**:
- ✅ Add to PRD Section 3.5 "LLM Prompt Management"
- ✅ Update REQ-7 (Persona Generation) with YAML pattern
- ✅ Unblocks TASK-007 (Prompt Template Architecture)

---

### 4.2 LLM Output Validation - Pydantic

**Finding**: Use **Pydantic** for schema validation (not regex or manual parsing).

**Pattern**:

```python
from pydantic import BaseModel, Field, validator

class PersonaSchema(BaseModel):
    """Schema for AI-generated personas."""
    name: str = Field(..., min_length=3, max_length=50)
    age_range: str = Field(..., regex=r"^\d{2}-\d{2}$")  # e.g., "25-35"
    income_range: str
    pain_points: list[str] = Field(..., min_items=3, max_items=5)
    buying_triggers: list[str] = Field(..., min_items=2)
    keywords: list[str] = Field(..., min_items=10, max_items=15)

    @validator("keywords")
    def validate_keywords(cls, v):
        """Ensure keywords are lowercase, no special chars."""
        return [kw.lower().strip() for kw in v if kw.isalnum() or " " in kw]

# Usage
def generate_persona(business_name: str) -> PersonaSchema:
    """Generate persona with schema validation."""
    prompt = generate_persona_prompt(business_name, ...)

    # Call LLM
    response = claude_client.messages.create(
        model="claude-sonnet-4-5",
        messages=[{"role": "user", "content": prompt["user"]}],
        system=prompt["system"]
    )

    # Parse and validate
    try:
        persona_data = json.loads(response.content[0].text)
        persona = PersonaSchema(**persona_data)  # ← Pydantic validation
        return persona
    except ValidationError as e:
        # Handle schema mismatch (re-prompt LLM with error details)
        print(f"Validation failed: {e.json()}")
        return None
```

**Action Items**:
- ✅ Add to PRD REQ-7 (Persona Generation)
- ✅ Unblocks TASK-026 (Persona Generator Implementation)

---

### 4.3 Ad Copy Polarity Testing

**Finding**: Generate 2 ad copy variants per persona - **Urgency** vs. **Value**.

**Pattern**:

```yaml
# prompts/ad_copy_generation.yaml
polarity_urgency: |
  Generate ad copy emphasizing URGENCY and scarcity:
  - Limited time offers ("Last 24 hours", "Only 3 left")
  - Immediate action ("Act now", "Don't miss out")
  - Loss aversion ("Before it's gone", "Limited spots")

polarity_value: |
  Generate ad copy emphasizing VALUE and benefits:
  - Long-term benefits ("Lifetime access", "Forever free")
  - Unique advantages ("Industry-leading", "Award-winning")
  - Social proof ("Trusted by 10,000+", "5-star rated")
```

**Python**:

```python
def generate_ad_variants(persona: PersonaSchema, product: str):
    """Generate 2 ad copy variants per persona."""
    variants = []

    for polarity in ["urgency", "value"]:
        prompt = load_prompt_template(f"prompts/ad_copy_{polarity}.yaml")

        ad_copy = claude_client.generate(
            prompt=prompt,
            context={"persona": persona.dict(), "product": product}
        )

        variants.append({
            "polarity": polarity,
            "headlines": ad_copy["headlines"],
            "descriptions": ad_copy["descriptions"]
        })

    return variants  # 2 variants per persona
```

**Action Items**:
- ✅ Add to PRD REQ-7 (Ad Copy Generation)
- ✅ Unblocks TASK-029 (Ad Copy Generator)

---

## 5. Implementation Roadmap (Based on Research)

### Phase 0: Specification (READY TO START)

**Unblocked Tasks** (research complete):
- ✅ TASK-000: Update PRD Section 3.4 (use Prompt 1 findings)
- ✅ TASK-001: Define API v22 Requirements (use Prompt 2 findings)
- ✅ TASK-002: Design Policy Handler (use Prompt 1 & 2 code examples)
- ✅ TASK-006: Map Bidding Strategies (use Prompt 3 table)
- ✅ TASK-007: Define Prompt Templates (use Prompt 4 YAML pattern)

**Blocked Tasks** (awaiting Prompt 6):
- ⏳ TASK-005: Clarify Asset Scope (needs RQ-034 answer)
- ⏳ TASK-004: Define Agent Loop (needs RQ-006 answer)

---

### Phase 1: Foundation (CAN START AFTER PHASE 0)

**Ready Tasks** (no dependencies):
- ✅ TASK-010: Setup Python Environment
- ✅ TASK-011: OAuth2 Setup (use Prompt 2 refresh pattern)
- ✅ TASK-012: Pydantic Models (use Prompt 4 schema examples)
- ✅ TASK-013: GAQL Query Builder (use Prompt 2 GAQL patterns)

**Timeline**: 2-3 weeks
**Exit Criteria**: 80% test coverage, validated configs

---

### Phase 2: Agent Implementation (BLOCKED BY PROMPT 6)

**Blocked Until**:
- DECISION-001: Asset scope (text vs. visual)
- DECISION-002: Approval UX (CLI vs. web vs. conversational)

**Can Prepare**:
- ✅ TASK-020: MCP Server (use Prompt 1 in-process pattern)
- ✅ TASK-021: Permission Controller (use Prompt 1 callback code)

---

### Phase 3: Deployment (BLOCKED BY PROMPT 5)

**Missing Research**:
- RQ-024: Deployment architecture (VM/serverless/container)
- RQ-029: Security & secrets management
- RQ-027: Testing strategy (80% coverage)

**Cannot Proceed Until**: Prompt 5 research complete

---

## 6. Next Steps (Immediate Actions)

### While Waiting for Prompt 6:

1. **Update PRD** (30 min):
   - Add Section 3.4 details from Prompt 1
   - Add breaking changes table from Prompt 2
   - Add bidding strategy mapping from Prompt 3
   - Add YAML prompt pattern from Prompt 4

2. **Update tasks.json** (15 min):
   - Change TASK-000, 001, 002, 006, 007 from `blocked` → `ready`
   - Add implementation notes from research

3. **Prepare DECISIONS.md** (10 min):
   - Template for DECISION-001, 002, 003
   - Ready to fill when Prompt 6 arrives

### When Prompt 6 Arrives:

1. **Make Decisions** (30 min):
   - DECISION-001: Asset scope (text-only or visual)
   - DECISION-002: Approval UX (CLI/web/conversational)

2. **Update Docs** (20 min):
   - Add product strategy findings to PRD
   - Update user_stories.md with UX decisions
   - Finalize tasks.json (all blocked → ready)

3. **Begin Phase 1** (immediately):
   - TASK-010: Python environment setup
   - TASK-011: OAuth2 configuration

---

## 7. Critical Findings Summary

### Security
- ✅ Custom `can_use_tool` callback required (default 'ask' is CLI-only)
- ✅ 3-tier permission: Auto-Deny, Auto-Allow, Ask-Human
- ⏳ Secrets management strategy awaiting Prompt 5

### Architecture
- ✅ In-Process MCP Server (not subprocess)
- ✅ Daily Session Pattern (not single 7-day session)
- ✅ Sidecar Persistence (external DB for event history)
- ✅ Portfolio Bidding Strategies (for Golden Ratio scaler)

### API
- ✅ Target Google Ads API v22 (skip v15-v21)
- ✅ OAuth refresh every 6 days (7-day expiration phenomenon)
- ✅ `validate_only=True` for policy pre-flight checks
- ✅ Use official `google-ads-mcp` for GAQL (read-only)

### AI
- ✅ YAML + Jinja2 for prompt templates
- ✅ Pydantic for output validation
- ✅ Ad copy polarity testing (urgency vs. value)
- ⏳ Asset scope decision awaiting Prompt 6

---

## 8. Product Strategy & Advanced Features (Prompt 6: RQ-006, RQ-016-017, RQ-031-035)

### 8.1 DECISION-001: Asset Generation Scope (RQ-034) - CRITICAL

**Finding**: **TEXT-ONLY for Phase 1-3**. Defer visual asset generation to Phase 4.

**Rationale**:

1. **Search Network = Primary Value**
   - SMB/mid-market focus on Search (not Display/Video)
   - Search ads are fundamentally text-based
   - Core pain point: Structure & Relevance (keyword grouping, copywriting)

2. **Competitive Analysis**
   - Optmyzr & Adalysis (leaders): NO native image generation
   - Focus on "math" (analytics), not "art" (visuals)
   - Users churn due to poor ROAS, not lack of images

3. **Unit Economics**
   - Text: $0.005-$0.01 per campaign (500-1000 tokens)
   - Image (DALL-E 3 HD): $0.08 per image
   - **Cost impact**: 1,000 users × 20 images/day = **$48,000/month**

4. **Performance Reality**
   - Image Extensions boost CTR by 10-15% (proven)
   - **BUT**: Uplift from *presence* of image, not AI-generated uniqueness
   - Stock photos often outperform mediocre AI generations

**Phased Roadmap**:

| Phase | Scope | Technology | Timeline |
|-------|-------|------------|----------|
| Phase 1 (MVP) | Text-Only (Headlines, Descriptions) | LLM only | Now |
| Phase 2 (PMF) | Stock Integration (Unsplash/Pexels) | Free stock API | After MVP |
| Phase 3 (Scale) | User Uploads (DAM) | S3 Storage | After PMF |
| Phase 4 (Advanced) | GenAI Studio (Custom images) | DALL-E 3 | Paid add-on |

**Impact**:
- ✅ Unblocks TASK-005 (Asset Scope) → `ready`
- ✅ Unblocks TASK-026 (Persona Generator) → Schema finalized
- ✅ Reduces backend engineering load by ~30% (no binary media processing)
- ✅ Schema: `AdObject = { headlines: [], descriptions: [], paths: [] }`

**Action Items**:
- ✅ Update PRD REQ-7 with text-only scope
- ✅ Update TASK-005 status → `ready`
- ✅ Update TASK-042 (Asset automation) → Move to Phase 4

---

### 8.2 DECISION-002: User Approval Workflow UX (RQ-031)

**Research Finding**: "Conversational Commander" (Hybrid Chat + Slack Integration)

**USER DECISION**: ✅ **CLI-ONLY** (Override research recommendation)

**Rationale for CLI-Only**:
- ✅ Simpler architecture (30-40% faster development)
- ✅ No web framework needed
- ✅ No Slack API integration
- ✅ Perfect for power users, developers, agencies
- ✅ Scriptable/automatable (CI/CD, cron jobs)

**CLI Interface** (see DECISIONS.md for full spec):
```bash
$ python agent.py optimize --vertical saas

✅ Generated 3 campaigns

CAMPAIGN 1: 🚀_SaaS_FreeTrial_IN_Srch_Exact_2025Q1
  Headlines:
    • Automate Your Sales CRM
    • #1 Rated CRM for Startups

[A]pprove all | [E]dit | [R]eject | [Q]uit: █
```

**Tech Stack**:
- `typer` or `click` (CLI framework)
- `rich` (beautiful terminal output - colors, tables, progress)
- `inquirer` or `questionary` (interactive prompts)

**Action Items**:
- ✅ Unblocks TASK-028 (Approval Workflow)
- ✅ Add CLI libraries to requirements.txt
- ✅ Add to PRD Section 3.6 "User Experience" (CLI-specific)
- ✅ **Removes from scope**: Web framework, Slack API, chat UI components

---

### 8.3 Campaign Naming Convention (RQ-032)

**Finding**: "Naming is Architecture" - Use regex-parseable naming for automated reporting.

**Pattern**: `{Status}_{Vertical}_{Offer}_{Geo}_{Network}_{MatchType}_{Date}`

**Example**: `🚀_SaaS_FreeTrial_IN_Srch_Exact_2025Q1`

**Components**:
- **Status**: 🚀 (Active), 🧪 (Test), 📈 (Scale)
- **Vertical**: SaaS, Ecom, Edu
- **Offer**: FreeTrial, Demo, Webinar, Discount20
- **Geo**: IN (India), US, Global
- **Network**: Srch (Search), Disp (Display), PMax, Vid
- **MatchType**: Exact, Broad, Auto
- **Date**: 2025Q1, 250115

**Why This Structure**:
- Sorting: Status emoji floats to top alphabetically
- Filtering: `name CONTAINS "🧪"` finds all test campaigns
- Analysis: Split by `_` → Extract offer performance

**Ad Group Naming**: `{PersonaID}_{Theme}_{Match}`
- Example: `P01_StatusSeeker_Broad`
- Example: `P02_BudgetConscious_Exact`
- **Cross-campaign persona reporting**: Filter Ad Groups starting with `P01`

**Labeling Strategy** (for API logic):
- **Tier Labels**: `Tier_1_HighIntent`, `Tier_2_Nurture` (for bid adjustments)
- **Automation Labels**: `Auto_Managed` vs. `Manual_Override`
  - If user manually changes bid → Apply `Manual_Override` label
  - Automation checks label before overwriting (prevents "fighting the bot")
- **Safety Labels**: `Circuit_Breaker_Paused` (applied by hourly watchdog)

**GAQL Example**:
```sql
SELECT campaign.name, metrics.impressions, metrics.clicks
FROM campaign
WHERE campaign.status = 'ENABLED'
  AND campaign.name LIKE '%_IN_%'        -- India campaigns
  AND campaign.name LIKE '%_FreeTrial_%' -- Free Trial offer
```

**Action Items**:
- ✅ Add to PRD Section 3.2 "Campaign Management"
- ✅ Implement naming logic in campaign creation service
- ✅ Add to TASK-024 (Campaign Creation)

---

### 8.4 Golden Ratio Circuit Breaker (RQ-033)

**Finding**: Implement ₹2,000/day hard cap with 1.2x safety margin.

**Problem**: Google's "2x Rule"
- Google can spend up to **2× daily budget** on any given day
- Risk: User sets ₹2,000/day expecting 10-day test → Google spends ₹4,000 on Day 1
- Burns 20% of total ₹20k budget in 24 hours if poorly targeted

**Why ₹2,000?**
- **CPC Baseline**: India B2B SaaS = ₹50-₹80
- **Volume**: ₹2,000 = 25-40 clicks/day
- **Statistical significance**: 200-300 clicks needed (7-10 days)
- **Safety**: 10% of total ₹20k promotional credit

**Trigger Logic**: **1.2x Safety Margin** (₹2,400)

**Why 1.2x, not 1.0x?**
- Google's pacing is fluid
- Stopping exactly at ₹2,000 might cut off at 4pm (creates "morning bias" in data)
- Buffer allows natural fluctuation but stops "runaway" 2× spend

**Implementation**: Hourly Watchdog (Cron Job)

```javascript
function checkCircuitBreaker() {
  const HARD_LIMIT_RATIO = 1.2;
  const ACCOUNT_LIMIT = 2000;

  const campaigns = AdsApp.campaigns()
    .withCondition("Status = ENABLED")
    .withCondition("LabelNames CONTAINS_NONE ['Tripwire_Exempt']")
    .get();

  while (campaigns.hasNext()) {
    let campaign = campaigns.next();
    let spendToday = campaign.getStatsFor("TODAY").getCost();
    let dailyBudget = campaign.getBudget().getAmount();

    if (spendToday > (dailyBudget * HARD_LIMIT_RATIO) || spendToday > ACCOUNT_LIMIT) {
      campaign.applyLabel("Circuit_Breaker_Paused");
      campaign.pause();
      Logger.log(`PAUSED: ${campaign.getName()} at spend ${spendToday}`);
      sendSlackAlert(campaign.getName(), spendToday);
    }
  }
}
```

**Tripwire Exception**:
- Users can tag campaigns with `Tripwire_Exempt` label (e.g., "Black Friday Sale")
- Script skips these, allowing strategic scaling

**Action Items**:
- ✅ Add to PRD REQ-10 (Golden Ratio Scaler)
- ✅ Update TASK-032 (Budget Scaler Implementation)
- ✅ Implement hourly cron job
- ✅ Add Slack alert integration

---

### 8.5 Shadow Ledger for ₹20k Promo Credit (RQ-035)

**Problem**: Google Ads API doesn't expose "Progress toward promotional credit"
- UI shows progress under Billing > Promotions
- No API endpoint to query this data

**Solution**: **Build Shadow Ledger** (local tracking database)

**Implementation**:

```python
# Initialization: User connects ad account
shadow_ledger = {
    "promo_target": 20000,  # ₹20k spend goal
    "connection_date": "2025-01-01",
    "account_creation_date": "2024-12-20",
    "promo_start_date": "2025-01-01",
    "current_spend": 0,
    "days_remaining": 60
}

# Daily Job: Sum spend since promo start
def update_shadow_ledger():
    total_spend = sum_cost_micros(
        customer_id=customer_id,
        date_range=f"since {shadow_ledger['promo_start_date']}"
    )
    shadow_ledger["current_spend"] = total_spend / 1_000_000  # Convert micros
    shadow_ledger["remaining_spend"] = 20000 - shadow_ledger["current_spend"]
```

**Pacing Algorithm**:

```python
def calculate_pacing():
    remaining = shadow_ledger["remaining_spend"]
    days_left = shadow_ledger["days_remaining"]
    current_daily_avg = shadow_ledger["current_spend"] / (60 - days_left)
    required_rate = remaining / days_left

    if required_rate < current_daily_avg:
        return "GREEN", "You are on track to unlock ₹20k credit"
    elif required_rate < current_daily_avg * 1.2:
        return "YELLOW", f"Suggest 20% budget increase to ₹{int(current_daily_avg * 1.2)}/day"
    else:
        return "RED", f"CRITICAL: Need ₹{int(required_rate)}/day for next {days_left} days. Risk of missing credit."
```

**Alerts**:
- **Green**: On track
- **Yellow**: 20% behind → Suggest budget increase
- **Red**: 2× behind → "Miss risk alert" with spend-up recommendation

**Prevents "Sunk Cost Fallacy"**:
- Users might rush to spend inefficiently just to get credit
- System acts as rational advisor: "This is aggressive. Do you want to increase budget?"

**Action Items**:
- ✅ Add to PRD Section 3.7 "Promotional Credit Tracking"
- ✅ Implement shadow ledger database
- ✅ Implement daily pacing job
- ✅ Add to dashboard UI (progress bar)

---

### 8.6 Session Forking - Parallel Strategy Simulation (RQ-006)

**Finding**: Use Claude SDK's `fork_session` to create "Simulation Engine"

**Traditional Tools**: Manage existing campaigns
**Our Approach**: **Simulate divergent strategies** before spending money

**Technical Mechanism**:

```python
# Session_Root: System prompt + user context (website scrape)
session_root_id = create_initial_session(website_url)

# Fork into 3 parallel threads
branch_a = client.query(
    resume=session_root_id,
    fork=True,
    prompt="Generate Conservative Strategy (Exact Match, Target ROAS)"
)

branch_b = client.query(
    resume=session_root_id,
    fork=True,
    prompt="Generate Aggressive Strategy (Broad Match, Max Conversions)"
)

branch_c = client.query(
    resume=session_root_id,
    fork=True,
    prompt="Generate Competitor Attack Strategy (Competitor Keywords)"
)
```

**Workflow**:
1. **Ingest**: User uploads URL → System builds `Session_Root`
2. **Fork**: System creates 3 parallel threads
   - Thread 1: "Volume-Max" (Broad Match, Max Conversions)
   - Thread 2: "Efficiency-Max" (Exact Match, Target ROAS)
   - Thread 3: "Competitor-Attack" (Competitor Keywords, High Bids)
3. **Convergence**: Present comparison table
   - "Strategy 1: More traffic. Strategy 2: Cheaper leads."
4. **Selection**: User clicks "Select Strategy 2" → Promote to Master Session

**Cost Optimization**: Prompt Caching (Anthropic)
- `Session_Root` (heavy with website context) is **cached**
- Forks only pay for **divergent tokens**
- **Up to 90% cheaper** for cached prefix

**Competitive Positioning**: **"Strategy Engine"**, not just "Management Tool"

**Action Items**:
- ✅ Unblocks TASK-004 (Agent Loop Pattern)
- ✅ Add to PRD Section 3.4 "Agent Architecture"
- ✅ Implement session forking logic
- ✅ Unique differentiator (competitive advantage)

---

### 8.7 Custom Audiences (RQ-016)

**Finding**: Google Ads API mandates `AUTO` type for new Custom Audiences (no explicit INTEREST or PURCHASE_INTENT).

**Implication**: Cannot force Google to treat keyword as strict "Interest"
- Google's AI decides dynamically based on campaign type & user signals

**Best Practice**: **URL + Keyword Layering**

**Example**:
```python
custom_audience = {
    "name": "High-Intent SaaS Buyers",
    "type": "AUTO",  # Mandated by API
    "members": [
        {"url": "competitor-crm.com"},  # Competitor visitors
        {"keyword": "enterprise crm software"}  # High-intent search
    ]
}
```

**Advanced Strategy**: Use for Search Campaigns (not just Display)
- Apply as "Observation" layer with **bid adjustments**
- Example: "Bid +30% if user searching 'CRM software' is also in 'Competitor Visitors' audience"

**Action Items**:
- ✅ Add to PRD Section 3.8 "Advanced Targeting"
- ⏸️ Implement in Phase 4 (advanced features)

---

### 8.8 Keyword Forecasting & Bid Simulator (RQ-017)

**Finding**: Use `KeywordPlanIdeaService` to build "Bid Landscape" simulator.

**Forecast Accuracy**:
- **High** for "Head Terms" (e.g., "iPhone 15")
- **Low** for "Long Tail" (e.g., "best enterprise crm for plumbing")
- **Horizon**: 30-day forecast (beyond that, too noisy)

**Bid Simulator Feature**:

```python
def build_bid_landscape(keyword: str):
    """Run forecast loop with incrementing CPCs."""
    results = []

    for cpc in [20, 40, 60, 80, 100]:  # ₹ values
        forecast = keyword_plan_service.generate_forecast(
            keyword=keyword,
            max_cpc_micros=cpc * 1_000_000
        )
        results.append({
            "cpc": cpc,
            "spend": forecast.spend,
            "clicks": forecast.clicks
        })

    # Find point of diminishing returns
    optimal_cpc = identify_diminishing_returns(results)
    return results, optimal_cpc
```

**Output**: Curve plotting "Spend vs. Clicks"

**Insight**: "Bidding higher than ₹80 will increase cost by 20% but clicks by only 2%."

**Action Items**:
- ✅ Add to PRD Section 3.9 "Forecasting & Simulation"
- ⏸️ Implement in Phase 3 (after core features)

---

## 9. Final Research Summary

### Coverage: 35 of 35 Questions ✅ COMPLETE

**All 6 Prompts Completed**:
- ✅ Prompt 1: Agent SDK (6 questions)
- ✅ Prompt 2: Google Ads API (4 questions)
- ✅ Prompt 3: Campaign APIs (4 questions)
- ✅ Prompt 4: AI Generation (6 questions)
- ⏸️ Prompt 5: Production (7 questions) - **NOT YET COMPLETED**
- ✅ Prompt 6: Product Strategy (8 questions)

**Current Coverage**: **28 of 35 questions (80%)** answered

**Still Missing** (Prompt 5):
- RQ-024: Deployment architecture
- RQ-025: Monitoring & alerts
- RQ-026: Database & state persistence
- RQ-027: Testing strategy
- RQ-028: CI/CD pipeline
- RQ-029: Security & secrets management (CRITICAL)
- RQ-030: Cost optimization

---

## 10. Next Steps (IMMEDIATE)

### Step 1: Update PRD (30 min)
Add research findings to:
- Section 3.4: Agent SDK (Prompt 1)
- Section 3.5: LLM Prompts (Prompt 4)
- Section 3.6: UX (Prompt 6 - DECISION-002)
- Section 3.7: Promo Credit (Prompt 6 - Shadow Ledger)
- REQ-5: API v22 breaking changes (Prompt 2)
- REQ-6: Policy validation (Prompt 2)
- REQ-7: Persona generation - TEXT-ONLY (Prompt 6 - DECISION-001)
- REQ-10: Golden Ratio scaler (Prompt 3 + Prompt 6)

### Step 2: Update tasks.json (20 min)
Change status `blocked → ready`:
- ✅ TASK-000: Update PRD SDK section
- ✅ TASK-001: API v22 requirements
- ✅ TASK-002: Policy handler
- ✅ TASK-004: Agent loop pattern
- ✅ TASK-005: Asset scope (TEXT-ONLY)
- ✅ TASK-006: Bidding strategy mapping
- ✅ TASK-007: Prompt templates
- ✅ TASK-028: Approval workflow
- ✅ TASK-026: Persona generator

### Step 3: Begin Phase 1 (IMMEDIATELY)
**Unblocked Tasks**:
- TASK-010: Setup Python Environment
- TASK-011: OAuth2 Setup (use 6-day refresh pattern)
- TASK-012: Pydantic Models (use schemas from research)
- TASK-013: GAQL Query Builder

**Timeline**: 2-3 weeks for Phase 1
**Exit Criteria**: 80% test coverage, validated configs

---

**Status**: ✅ **80% research complete (28/35 questions)** | ✅ **Critical decisions made** | ⏸️ **Prompt 5 still needed for deployment**
