# Product & Architecture Decisions
**Date**: 2025-12-26
**Status**: 2 of 3 decisions finalized
**Source**: Research answers from Prompt 1-6

---

## DECISION-001: Asset Generation Scope ✅ FINALIZED

**Question**: Should Phase 1-3 MVP include visual asset generation (images/videos) or text-only?

**Research Source**: RQ-034 (Prompt 6)

**Decision**: **TEXT-ONLY for Phase 1-3** (Defer visual to Phase 4)

### Rationale

**Strategic Case for Text-First**:
1. **Search Network is primary value proposition**
   - SMB/mid-market growth marketers (target persona) focus on Search
   - Search ads are fundamentally text-based (headlines + descriptions)
   - Core pain point: "Structure & Relevance" (keyword grouping + copywriting)

2. **Competitive analysis supports text focus**
   - Optmyzr & Adalysis (market leaders): No native image generation
   - They focus on "math" (analytics, auditing, optimization), not "art"
   - Users churn due to poor ROAS, not lack of visual assets

3. **Unit economics favor text**
   - Text generation cost: $0.005-$0.01 per campaign (500-1000 tokens)
   - Image generation cost: $0.08 per HD image via DALL-E 3
   - Scenario: 1,000 users × 20 images/day = **$48,000/month** operational cost
   - Text edits: Zero-cost (simple token changes vs. full regeneration)

4. **Latency & UX friction**
   - Text generation: Near-instantaneous (maintains flow state)
   - Image generation: 10-15 seconds per image (requires async queue architecture)

5. **Performance data**
   - Image Extensions boost CTR by 10-15% (proven)
   - **BUT**: Uplift comes from *presence* of image, not AI-generated uniqueness
   - Stock photos often outperform mediocre AI images

### Phased Roadmap

| Phase | Feature Scope | Technology | Rationale |
|-------|---------------|------------|-----------|
| **Phase 1 (MVP)** | Text-Only Search (Headlines, Descriptions, Sitelinks) | LLM (Claude/GPT) | Focus on "Message-Market Fit" & Quality Score. Lowest risk. |
| **Phase 2 (PMF)** | Stock Integration (Unsplash/Pexels API) | Unsplash API (Free tier) | Capture 10-15% CTR uplift without GenAI cost |
| **Phase 3 (Scale)** | User Uploads (DAM) | S3 / Cloud Storage | Allow brand assets (logos, product shots) |
| **Phase 4 (Advanced)** | GenAI Studio (Custom images) | DALL-E 3 / Stable Diffusion | Paid add-on/"Pro Tier" to offset high unit costs |

### Impact on Project

**Unblocks**:
- ✅ TASK-005: Clarify Asset Generation Scope → Status changed to `ready`
- ✅ TASK-026: Implement Persona Generator → Can finalize schema
- ✅ TASK-042: Asset Creation Automation → Deferred to Phase 4

**Technical Decisions**:
- Schema: `AdObject = { headlines: [], descriptions: [], paths: [] }` (no binary media)
- No `AssetService` image processing in Phase 1-3 (reduces backend engineering load by ~30%)
- No async job queue for image generation (simpler architecture)

**Cost Savings**:
- Eliminates $48k/month operational expense line item
- Reduces LLM rejection/regeneration costs (text edits are cheap)

---

## DECISION-002: User Approval Workflow UX ✅ FINALIZED

**Question**: What interface should users use to approve/edit/reject AI-generated campaigns? CLI, Web Dashboard, or Conversational?

**Research Source**: RQ-031 (Prompt 6)

**Decision**: **CLI-ONLY** (Interactive Command-Line Interface)

**User Override**: Research recommended "Conversational Commander" (Hybrid Chat + Slack), but user selected **CLI-only** for simplicity and faster implementation.

### CLI Interface Design

**Interactive Command-Line Workflow**:

```bash
$ python agent.py optimize --vertical saas --offer free-trial

🤖 Growth-Tier Ads Agent v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Generated 3 campaigns for SaaS Q1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CAMPAIGN 1: 🚀_SaaS_FreeTrial_IN_Srch_Exact_2025Q1

Budget: ₹2,000/day
Bidding: Target CPA ₹50

Ad Group 1: P01_StatusSeeker_Exact
  Headlines:
    • Automate Your Sales CRM
    • #1 Rated CRM for Startups
    • Close Deals Faster Today

  Descriptions:
    • Join 10,000+ teams automating sales. Free 14-day trial.
    • No credit card required. Setup in 5 minutes.

Ad Group 2: P02_BudgetConscious_Exact
  Headlines:
    • Affordable CRM for Small Teams
    • Start Free, Upgrade When Ready
    • Pay Only for What You Use

  Descriptions:
    • Plans from ₹500/month. Cancel anytime.
    • Free tier includes unlimited contacts.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Actions:
  [A]pprove all campaigns
  [E]dit campaign (select by number)
  [R]eject all
  [V]iew full details
  [Q]uit without saving

Choice: █
```

**Why CLI-Only**:
- ✅ **Simplicity**: No web framework, no Slack integration
- ✅ **Speed**: Faster to build (weeks vs. months)
- ✅ **Control**: Perfect for power users, developers, agencies
- ✅ **Automation-friendly**: Can be scripted, piped, integrated into CI/CD

**Why NOT Conversational/Slack** (research recommendation):
- ❌ Requires chat UI framework (React/Vue)
- ❌ Requires Slack API integration + webhooks
- ❌ More complex architecture
- ❌ Longer development timeline

### CLI Approval & Edit Workflow

#### **1. Approve Flow**

```bash
Choice: A

✅ Approving 3 campaigns...

  ✓ Creating campaign 1/3... Done
  ✓ Creating campaign 2/3... Done
  ✓ Creating campaign 3/3... Done

✅ All campaigns created successfully!

Campaign IDs:
  - 🚀_SaaS_FreeTrial_IN_Srch_Exact_2025Q1: 123456789
  - 🧪_SaaS_Demo_IN_Srch_Broad_2025Q1: 123456790
  - 📈_SaaS_Webinar_IN_Srch_Auto_2025Q1: 123456791

View in Google Ads: https://ads.google.com/...

Starting 7-day autonomous monitoring...
```

#### **2. Edit Flow**

```bash
Choice: E

Which campaign? [1-3]: 1
Which ad group? [1-2]: 1

Edit what?
  [1] Regenerate all headlines
  [2] Regenerate all descriptions
  [3] Edit specific headline (manual)
  [4] Change budget
  [5] Back

Choice: 1

🤖 Regenerating headlines for P01_StatusSeeker...

New headlines:
  • Transform Your Sales Process
  • Enterprise CRM Made Simple
  • Automate. Close. Grow.

[A]ccept | [R]egenerate again | [C]ancel: █
```

#### **3. Reject Flow**

```bash
Choice: R

Why reject? (helps improve future generations)
  [1] Headlines too generic
  [2] Tone doesn't match brand
  [3] Budget too high
  [4] Wrong targeting
  [5] Other

Choice: 2

💬 Optional: Describe your brand tone (or press Enter to skip)
> We're a fun, casual brand. Less corporate, more friendly.

✅ Feedback saved. This will improve future generations.

Exiting without creating campaigns.
```

#### **4. Timeout Behavior** (Headless Mode)

When running in autonomous mode (e.g., daily cron job):

```python
# Auto-approval for low-risk operations
if operation.risk_level == "low" and operation.budget_change < 1000:
    # Auto-approve small optimizations
    execute_operation(operation)
else:
    # Queue for manual approval
    save_to_approval_queue(operation)
    send_notification(
        message=f"Approval needed: {operation.description}",
        expiry="24h"
    )
```

**Policy**: If no approval within 24h → Auto-reject (safety default)

### Technical Implementation

**Tech Stack**:
- `click` or `typer` for CLI framework
- `rich` for beautiful terminal output (colors, tables, progress bars)
- `inquirer` or `questionary` for interactive prompts
- Standard Python (no web framework needed)

**Example Code**:

```python
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
import typer

app = typer.Typer()
console = Console()

@app.command()
def optimize(vertical: str, offer: str):
    """Generate and approve campaigns."""

    # Generate campaigns
    campaigns = agent.generate_campaigns(vertical=vertical, offer=offer)

    # Display campaigns
    for i, campaign in enumerate(campaigns, 1):
        console.print(f"\n[bold]CAMPAIGN {i}:[/bold] {campaign.name}")
        console.print(f"Budget: ₹{campaign.budget}/day")

        for ad_group in campaign.ad_groups:
            table = Table(title=ad_group.name)
            table.add_column("Headlines", style="cyan")
            for headline in ad_group.headlines:
                table.add_row(headline)
            console.print(table)

    # Interactive approval
    choice = Prompt.ask(
        "Actions",
        choices=["A", "E", "R", "V", "Q"],
        default="A"
    )

    if choice == "A":
        # Approve all
        with console.status("[bold green]Creating campaigns..."):
            results = google_ads_client.create_campaigns(campaigns)
        console.print("✅ All campaigns created!")

    elif choice == "E":
        # Edit flow
        campaign_num = Prompt.ask("Which campaign?", choices=["1", "2", "3"])
        # ... edit logic

    # ... other flows

if __name__ == "__main__":
    app()
```

### Impact on Project

**Unblocks**:
- ✅ TASK-028: User Approval Workflow → Status changed to `ready`
- ✅ TASK-029: Ad Copy Generator → Can implement with CLI edit flow

**Technical Requirements** (Simplified):
- ✅ `typer` or `click` (CLI framework)
- ✅ `rich` (terminal UI - tables, colors, progress bars)
- ✅ `inquirer` or `questionary` (interactive prompts)
- ✅ Standard Python only (no web framework, no Slack API)

**Removed from Scope**:
- ❌ Web framework (React/Vue/Flask/FastAPI for UI)
- ❌ Slack API integration
- ❌ Chat UI components
- ❌ WebSocket/SSE for real-time updates
- ❌ Block Kit webhooks

**Benefits**:
- ✅ **30-40% faster development** (weeks vs. months)
- ✅ **Simpler architecture** (fewer moving parts)
- ✅ **Lower operational cost** (no web hosting needed)
- ✅ **Scriptable/automatable** (perfect for CI/CD, cron jobs)

---

## DECISION-003: Deployment Architecture ⏳ PENDING

**Question**: What deployment architecture should be used for 7-day autonomous monitoring? Cloud VM, Serverless, or Container?

**Research Source**: RQ-024 (Prompt 5) - **NOT YET COMPLETED**

**Status**: ⏳ **BLOCKED - Awaiting Prompt 5 research**

**Missing Research Questions**:
- RQ-024: Deployment options (VM/Serverless/Container) pros/cons
- RQ-025: Monitoring & alerts architecture
- RQ-026: Database & state persistence (PostgreSQL vs. DynamoDB vs. other)
- RQ-027: Testing strategy (80% coverage requirement)
- RQ-028: CI/CD pipeline design
- RQ-029: **Security & secrets management** (CRITICAL for production)
- RQ-030: Cost optimization strategies

**Blocks**:
- Phase 3 deployment tasks
- Production security implementation
- Cannot deploy safely without RQ-029 (secrets management)

**Next Steps**:
- Complete Prompt 5 research (7 questions)
- Make DECISION-003 based on findings
- Update this document

---

## DECISION-004: Agent Loop Pattern ✅ FINALIZED

**Question**: What agent loop pattern should be used? (Gather-Action-Verify, etc.)

**Research Source**: RQ-006 (Prompt 6)

**Decision**: **Session Forking for Parallel Strategy Simulation**

### Pattern: "Simulation Engine" (Not Just Management)

**Traditional Tools**: Manage existing campaigns
**Our Approach**: Simulate divergent strategies before spending money

### Technical Mechanism: `fork_session`

**Claude SDK Feature**: Create branching conversation history (tree structure vs. linear)

**Implementation**:
```python
# Session_Root: Contains system prompt + user context (website scrape)
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
    prompt="Generate Competitor Attack Strategy (Competitor Keywords, High Bids)"
)
```

### Workflow: Parallel Simulation

1. **Ingest**: User uploads URL → System analyzes → Builds `Session_Root`
2. **Fork**: System secretly forks session into 3 parallel threads
   - Thread 1: "Volume-Max" (Broad Match, Max Conversions)
   - Thread 2: "Efficiency-Max" (Exact Match, Target ROAS)
   - Thread 3: "Competitor-Attack" (Competitor Keywords, Aggressive Bids)
3. **Convergence**: System presents comparison table
   - "Strategy 1 will get you more traffic. Strategy 2 will get you cheaper leads."
4. **Selection**: User clicks "Select Strategy 2"
   - System discards Threads 1 & 3
   - Promotes Thread 2 to Master Session

### Cost & Performance

**Latency**: Run threads asynchronously (via `asyncio` in Python)

**Cost**: With Prompt Caching (Anthropic):
- `Session_Root` (heavy with website context) is **cached**
- Forks only pay for **divergent tokens**
- **Up to 90% cheaper** for cached prefix

### Impact on Project

**Unblocks**:
- ✅ TASK-004: Define Agent Loop → Status changed to `ready`
- ✅ Unique differentiator (competitive advantage)

**Positioning**: "Strategy Engine", not just "Management Tool"

---

## Decision Summary Table

| Decision | Question | Status | Answer | Impact |
|----------|----------|--------|--------|--------|
| **DECISION-001** | Asset scope (text vs. visual)? | ✅ Finalized | **Text-Only Phase 1-3** | Unblocks TASK-005, 026, 042 |
| **DECISION-002** | Approval UX (CLI/web/conv.)? | ✅ Finalized | **CLI-Only** (user override) | Unblocks TASK-028, 029 | Simplifies architecture 30-40% |
| **DECISION-003** | Deployment (VM/serverless/container)? | ⏳ Pending | **Awaiting Prompt 5** | Blocks Phase 3 deployment |
| **DECISION-004** | Agent loop pattern? | ✅ Finalized | **Session Forking (Simulation)** | Unblocks TASK-004 |

---

## Newly Unblocked Tasks (After Decisions)

**Phase 0: Specification**
- ✅ TASK-004: Define Agent Loop → Use session forking pattern
- ✅ TASK-005: Clarify Asset Scope → Text-only for Phase 1-3

**Phase 2: Agent Implementation**
- ✅ TASK-026: Persona Generator → Schema finalized (text-only)
- ✅ TASK-028: Approval Workflow → Conversational Commander + Slack
- ✅ TASK-029: Ad Copy Generator → Conversational edit loop

**Phase 4: Advanced Features** (Deferred)
- ⏸️ TASK-042: Asset Creation Automation → Moved to Phase 4 (GenAI Studio)

---

## Additional Strategic Decisions from Prompt 6

### Campaign Naming Convention (RQ-032)

**Pattern**: `{Status}_{Vertical}_{Offer}_{Geo}_{Network}_{MatchType}_{Date}`

**Example**: `🚀_SaaS_FreeTrial_IN_Srch_Exact_2025Q1`

**Rationale**:
- Regex-parseable for automated reporting
- Sortable (status emoji floats to top)
- GAQL-friendly (`WHERE campaign.name LIKE '%_IN_%'`)

**Ad Group Naming**: `{PersonaID}_{Theme}_{Match}`
- Example: `P01_StatusSeeker_Broad`
- Enables cross-campaign persona reporting

### Golden Ratio Circuit Breaker (RQ-033)

**Limit**: ₹2,000/day (hard cap)

**Trigger**: 1.2x safety margin (₹2,400) → Pause campaign

**Rationale**:
- Google's "2x rule" allows spending 2× daily budget on any given day
- ₹2,000 = 10% of ₹20k promotional credit (safe testing budget)
- 25-40 clicks/day at India CPC (₹50-₹80) = statistical significance in 7-10 days

**Implementation**: Hourly cron job checks spend, applies `Circuit_Breaker_Paused` label

### Shadow Ledger (RQ-035)

**Problem**: Google Ads API doesn't expose "Progress toward ₹20k promo credit"

**Solution**: Build local tracking database
- Record: `Promo_Target = 20000`, `Connection_Date`
- Daily job: Sum `metrics.cost_micros` since start
- Pacing algorithm: Calculate required daily spend to hit goal

**Alerts**:
- Green: On track
- Yellow: 20% behind → Suggest budget increase
- Red: 2× behind → "Miss risk alert" with spend-up recommendation

---

**End of Decisions Document**
**Next Action**: Complete Prompt 5 research to finalize DECISION-003
