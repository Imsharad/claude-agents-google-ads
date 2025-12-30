# User Stories: Growth-Tier Ads Protocol Agent

## Project Status (Dec 31, 2025)

**Phases 0-3 Complete** | 30/31 tasks done | 29 PRs merged

## Classification System
- ✅ **COMPLETE**: Fully implemented and tested
- ⚠️ **PHASE 4**: Planned for advanced features phase
- ❌ **DEFERRED**: Not in current scope

---

## Core User Stories

### US-001: Campaign Configuration Input
**As a** user
**I want to** provide a campaign configuration with vertical type, offer name, target audience, and value proposition
**So that** the agent can adapt to my specific business vertical

**Status**: ✅ **COMPLETE**
**Implementation**: TASK-012 ([PR #12](https://github.com/Imsharad/claude-agents-google-ads/pull/12))
**Deliverables**:
- `src/models/configuration.py` - Pydantic model with full validation
- Enum validation for `vertical_type` and `monetization_model`
- Unit tests with >80% coverage

---

### US-002: Automated Persona Segmentation
**As a** user
**I want to** automatically generate 3 distinct sub-personas from my broad target audience
**So that** I can create more targeted ad groups without manual market research

**Status**: ✅ **COMPLETE**
**Implementation**: TASK-022 ([PR #21](https://github.com/Imsharad/claude-agents-google-ads/pull/21))
**Deliverables**:
- `src/generators/persona_generator.py`
- `prompts/persona_generation.yaml` - YAML + Jinja2 templating
- Pydantic schema validation for 3 personas
- Integration tests with Workshop example config

---

### US-003: Polarity Ad Copy Testing
**As a** user
**I want to** automatically generate two psychological angles (Pull vs Push) for my offer
**So that** I can A/B test which messaging resonates better

**Status**: ✅ **COMPLETE**
**Implementation**: TASK-023 ([PR #28](https://github.com/Imsharad/claude-agents-google-ads/pull/28))
**Deliverables**:
- `src/generators/ad_copy_generator.py`
- `prompts/polarity_ad.yaml` - Pull (Desire/Gain) and Push (Fear/FOMO)
- Google Ads format validation (30 char headlines, 90 char descriptions)
- Policy pre-check with prohibited claims filter

---

### US-004: Monetization-Aware Upsell Scripting
**As a** user
**I want to** receive appropriate backend upsell messaging based on my monetization model
**So that** I can maximize customer lifetime value beyond the initial conversion

**Status**: ✅ **COMPLETE** (Text deliverable)
**Implementation**: TASK-026 ([PR #17](https://github.com/Imsharad/claude-agents-google-ads/pull/17))
**Deliverables**:
- `src/generators/upsell_script_generator.py`
- `prompts/upsell_scripts.yaml`
- Monetization model-specific scripts:
  - EDUCATION: Webinar transition script
  - SAAS: Demo booking nudge
  - SERVICE: Consultation value stack

---

### US-005: Growth-Tier Budget Management
**As a** user
**I want to** automatically allocate a ₹20,000 budget across 30 days
**So that** I can unlock the ₹20,000 platform credit

**Status**: ✅ **COMPLETE**
**Implementation**:
- TASK-014 ([PR #15](https://github.com/Imsharad/claude-agents-google-ads/pull/15)) - Static budget
- TASK-032 ([PR #27](https://github.com/Imsharad/claude-agents-google-ads/pull/27)) - Golden Ratio scaling
**Deliverables**:
- `src/budget/calculator.py` - Basic budget allocation
- `src/budget/golden_ratio_scaler.py` - Fibonacci scaling (1.618/2.618)
- LTV:CAC decision matrix implementation
- Circuit breaker with ₹2,000/day cap (1.2x safety margin)

---

### US-006: Keyword Expansion with Safety
**As a** user
**I want to** use phrase match keywords with automatic negative keyword deployment
**So that** I can capture intent variation without wasting budget on irrelevant traffic

**Status**: ✅ **COMPLETE**
**Implementation**:
- TASK-013 ([PR #14](https://github.com/Imsharad/claude-agents-google-ads/pull/14)) - Keyword generator
- TASK-027 ([PR #18](https://github.com/Imsharad/claude-agents-google-ads/pull/18)) - Shared negative sets
**Deliverables**:
- `src/generators/keyword_generator.py`
- `src/tools/negative_keywords_tool.py`
- Universal negative list (free, cheap, crack, job, etc.)
- Funnel sculpting (Tier 1 keywords negative in Tier 2/3)

---

### US-007: Campaign Setup Workflow
**As a** user
**I want to** review and approve the generated campaign structure before launch
**So that** I maintain control over what ads run

**Status**: ✅ **COMPLETE**
**Implementation**: TASK-028 ([PR #26](https://github.com/Imsharad/claude-agents-google-ads/pull/26))
**Deliverables**:
- `src/workflows/setup_workflow.py`
- CLI-based approval: [A]pprove/[E]dit/[R]eject/[Q]uit pattern
- Uses `typer/click` + `rich` for terminal UI
- Full preview of Keywords, Negatives, Ad copy before submission

---

### US-008: Real-Time Performance Monitoring (Days 1-14)
**As a** user
**I want to** automatically detect and kill underperforming ad angles based on CTR
**So that** I don't waste budget on ineffective creative

**Status**: ✅ **COMPLETE** (Daily monitoring, not real-time)
**Implementation**: TASK-031 ([PR #25](https://github.com/Imsharad/claude-agents-google-ads/pull/25))
**Deliverables**:
- `src/monitoring/ctr_monitor.py`
- Daily GAQL query for CTR + impressions
- CTR threshold: 1% with 100+ impressions
- Auto-pause via AdService.mutate + trigger new ad generation

---

### US-009: Automated Optimization (Days 15+)
**As a** user
**I want to** automatically pause losing personas and increase bids on winning ones
**So that** my ROI improves over the campaign lifecycle

**Status**: ✅ **COMPLETE**
**Implementation**: TASK-033 ([PR #30](https://github.com/Imsharad/claude-agents-google-ads/pull/30))
**Deliverables**:
- `src/optimization/persona_optimizer.py`
- Losing persona: `cost_per_conversion > target_cpa` OR `conversions=0 AND spend>₹2000`
- Winning persona: `cost_per_conversion < target_cpa AND conversions >= 5`
- Bid adjustment aligned with bidding strategy (TASK-006 mapping)

---

### US-010: Multi-Vertical Campaign Examples
**As a** user
**I want to** see example configurations for Workshop, Dentist, and SaaS verticals
**So that** I understand how to configure my specific use case

**Status**: ✅ **COMPLETE**
**Implementation**: TASK-015 ([PR #13](https://github.com/Imsharad/claude-agents-google-ads/pull/13))
**Deliverables**:
- `examples/workshop_config.json` (Education)
- `examples/dentist_config.json` (Service)
- `examples/saas_config.json` (SaaS)
- README.md with usage examples

---

## Additional Completed Features

### Policy Exception Handling
**Status**: ✅ **COMPLETE**
**Implementation**: TASK-025 ([PR #19](https://github.com/Imsharad/claude-agents-google-ads/pull/19))
- `src/utils/policy_handler.py`
- Try-Catch-Exempt-Retry workflow
- PolicyValidationParameter construction
- Human escalation on retry failure

### Agent Runtime (Claude SDK)
**Status**: ✅ **COMPLETE**
**Implementation**: TASK-020 ([PR #16](https://github.com/Imsharad/claude-agents-google-ads/pull/16))
- `src/agent/client.py`
- In-process MCP server pattern
- Daily session pattern
- 3-tier permission system

### Conversion Tracking Setup
**Status**: ✅ **COMPLETE**
**Implementation**: TASK-030 ([PR #24](https://github.com/Imsharad/claude-agents-google-ads/pull/24))
- `src/tools/conversion_setup_tool.py`
- Validates existing conversion actions
- Setup instructions if none found

### Reporting Dashboard
**Status**: ✅ **COMPLETE**
**Implementation**: TASK-034 ([PR #23](https://github.com/Imsharad/claude-agents-google-ads/pull/23))
- `src/reporting/query_builder.py`
- GAQL query generator with segmentation constraints
- Data grouped by Persona (ad_group) and Angle (ad)

### ₹20k Spend Monitor
**Status**: ✅ **COMPLETE**
**Implementation**: TASK-035 ([PR #29](https://github.com/Imsharad/claude-agents-google-ads/pull/29))
- `src/monitoring/spend_monitor.py`
- Shadow Ledger pattern for promo credit tracking
- Pacing alerts: Green/Yellow/Red status

---

## Phase 4: Advanced Features (Planned)

### US-P4-001: Custom Audience Creation
**Status**: ⚠️ **PHASE 4** (TASK-040)
**Description**: CustomAudienceService integration for audience layering
**Features**:
- CustomAudienceMember construction (KEYWORD, URL, APP)
- AUTO type for dynamic interpretation
- Integration with persona generator

### US-P4-002: Predictive Budget Forecasting
**Status**: ⚠️ **PHASE 4** (TASK-041)
**Description**: Pre-launch performance prediction using KeywordPlanIdeaService
**Features**:
- CampaignToForecast simulation
- 5 bid level testing for optimal point
- Impressions, clicks, cost estimates

### US-P4-003: Session Forking for Parallel Testing
**Status**: ⚠️ **PHASE 4** (TASK-043)
**Description**: A/B/C testing with parallel strategy simulation
**Features**:
- Fork 3 parallel threads (Volume-Max, Efficiency-Max, Competitor-Attack)
- Prompt caching for 90% cost savings
- Convergence logic for winning strategy

### US-P4-004: Multi-Agent Orchestration
**Status**: ⚠️ **PHASE 4** (TASK-044)
**Description**: Planner-Worker-Evaluator architecture
**Features**:
- Planner (Sonnet) for complex reasoning
- Worker (Haiku) for cost efficiency
- Evaluator for output verification

### US-P4-005: Visual Asset Pipeline
**Status**: ❌ **DEFERRED** (TASK-042)
**Description**: AssetService for image uploads
**Decision**: TEXT-ONLY for Phases 1-3, visual assets deferred as paid add-on
**Roadmap**:
- Phase 2: Stock integration (Unsplash/Pexels)
- Phase 3: User uploads (S3)
- Phase 4: GenAI Studio (DALL-E 3)

---

## Scope Summary

| Category | Count | Status |
|----------|-------|--------|
| ✅ **Core Stories Complete** | 10 | 100% |
| ✅ **Additional Features Complete** | 5 | 100% |
| ⚠️ **Phase 4 Planned** | 4 | 0% |
| ❌ **Deferred** | 1 | N/A |

**Total Implementation**: 15/15 Phase 0-3 user stories complete (100%)

---

## Architecture Decisions Implemented

| Decision | Choice | Impact |
|----------|--------|--------|
| DECISION-001 | Text-only assets | 30% reduction in backend complexity |
| DECISION-002 | CLI-only approval | 30-40% faster development |
| DECISION-003 | Containerized VM | Always-on agent with persistent storage |

---

## Technical Implementation Highlights

### Claude Agent SDK
- In-process MCP server (shared OAuth state)
- Daily session pattern
- 3-tier permission: Auto-Deny / Auto-Allow / Ask-Human

### Google Ads API
- Version: v22+
- Proactive OAuth refresh every 6 days
- Policy: validate_only=True + Try-Catch-Exempt-Retry

### Campaign Management
- Portfolio Bidding Strategies for data pooling
- Golden Ratio scaling (1.618/2.618)
- ₹2,000/day circuit breaker

### AI Generation
- YAML + Jinja2 prompt templates
- Pydantic output validation
- Polarity testing (Urgency vs Value)

---

## Next Steps

1. **Begin Phase 4** - Advanced features available for implementation
2. **Production Deployment** - Deploy to containerized VM (t3.medium)
3. **User Testing** - Validate with real campaigns
