# User Stories: Growth-Tier Ads Protocol Agent

## Classification System
- ✅ **IN SCOPE**: Can be fulfilled with current PRD specification
- ⚠️ **PARTIAL SCOPE**: Can be partially fulfilled, needs clarification
- ❌ **OUT OF SCOPE**: Blocked by architectural gaps identified in stress test

---

## 🎯 Core User Stories

### US-001: Campaign Configuration Input
**As a** user
**I want to** provide a campaign configuration with vertical type, offer name, target audience, and value proposition
**So that** the agent can adapt to my specific business vertical

**Status**: ✅ **IN SCOPE**
**PRD Reference**: Section 3.1 (Configuration Interface)
**Acceptance Criteria**:
- System accepts JSON configuration payload
- Configuration includes: `vertical_type`, `offer_name`, `target_audience_broad`, `value_proposition_primary`, `monetization_model`
- System validates configuration schema before processing

**Technical Acceptance Criteria**:
- Pydantic model `CampaignConfiguration` implements REQ-1
- Enum validation for `vertical_type` ∈ {EDUCATION, SAAS, SERVICE, E-COMMERCE}
- Enum validation for `monetization_model` ∈ {TRIPWIRE_UPSELL, DIRECT_SALE, LEAD_GEN, BOOK_CALL}
- String field validations: `offer_name` (max 50 chars), `value_proposition_primary` (max 200 chars)
- Unit tests cover: valid config, missing required fields, invalid enum values, string length violations
- Error messages are user-friendly and actionable

**Implementation Notes**:
- Configuration schema is well-defined in PRD:13-21
- See REQ-1 (PRD:125-130) for detailed specifications
- Deliverable: `src/models/configuration.py` + `tests/test_configuration.py`

---

### US-002: Automated Persona Segmentation
**As a** user
**I want to** automatically generate 3 distinct sub-personas from my broad target audience
**So that** I can create more targeted ad groups without manual market research

**Status**: ⚠️ **PARTIAL SCOPE**
**PRD Reference**: Section 3.2.1 (Universal Persona Segmentation)
**Blockers**:
- ❌ No Claude Agent SDK integration specified (Gap 1)
- ❌ No prompt template implementation details (Issue 1)
- ✅ Strategic approach is validated by research

**Acceptance Criteria**:
- Given: `target_audience_broad: "Mid-Career Professionals"`
- Output: 3 distinct personas with psychological purchase drivers
- Each persona maps to separate ad group

**Technical Acceptance Criteria**:
- LLM prompt template follows REQ-2 (PRD:132-137) variable injection pattern
- Prompt file: `prompts/persona_generation.yaml` with placeholders for {target_audience_broad}, {vertical_type}
- Claude model: `claude-3-5-sonnet-20241022` (from REQ-5 SDK config)
- Output schema matches REQ-7 (PRD:193-206):
  ```json
  {
    "personas": [
      {"name": str, "pain_point": str, "purchase_driver": str, "ad_group_name": str}
    ]
  }
  ```
- Pydantic validation ensures 3 personas returned (no more, no less)
- Integration test: Workshop example config → validates against research personas (Manager, Marketer, Freelancer)
- Error handling: LLM hallucination detection (e.g., duplicate personas, generic outputs)

**Missing Requirements** (Now Addressed):
- ✅ REQ-7: Output schema defined (PRD:193-206)
- ✅ REQ-2: Prompt template architecture specified (PRD:132-137)
- ✅ Claude SDK: Section 3.4 added to PRD

---

### US-003: Polarity Ad Copy Testing
**As a** user
**I want to** automatically generate two psychological angles (Pull vs Push) for my offer
**So that** I can A/B test which messaging resonates better

**Status**: ⚠️ **PARTIAL SCOPE**
**PRD Reference**: Section 3.2.2 (Abstracted Asset Generation)
**Blockers**:
- ❌ No LLM prompt template architecture (Gap 1, REQ-2)
- ⚠️ "Hallucinate" terminology needs correction (Contradiction 3)
- ✅ Polarity framework validated by google-ads-20k.md:4.1

**Acceptance Criteria**:
- Angle A (Pull): Desire, Gain, Efficiency copy
- Angle B (Push): Fear, Loss Aversion, FOMO copy
- Both angles delivered as Google Ads compliant text (30 char headlines, 90 char descriptions)

**Technical Acceptance Criteria**:
- Prompt templates: `prompts/polarity_ad_pull.yaml` and `prompts/polarity_ad_push.yaml`
- Each template includes: {persona_name}, {pain_point}, {offer_name}, {value_proposition_primary}
- REQ-8 validation (PRD:208-212):
  - Headlines: max 30 chars (hard limit, LLM instructed + post-processing validation)
  - Descriptions: max 90 chars (hard limit)
  - Prohibited claims filter: "guaranteed", "free money", "#1", "best" (regex check)
- Output format: Google Ads API compatible structure
  ```python
  {
    "headlines": ["Headline 1", "Headline 2", "Headline 3"],
    "descriptions": ["Description 1", "Description 2"]
  }
  ```
- Integration test: Workshop example → generates 6 ads (3 personas × 2 angles)
- All ads pass character limit validation
- All ads pass policy pre-check (no prohibited terms)

**Missing Requirements** (Now Addressed):
- ✅ REQ-8: Ad copy format validation (PRD:208-212)
- ✅ Character limit enforcement documented
- ✅ Policy pre-check keywords defined

---

### US-004: Monetization-Aware Upsell Scripting
**As a** user
**I want to** receive appropriate backend upsell messaging based on my monetization model
**So that** I can maximize customer lifetime value beyond the initial conversion

**Status**: ❌ **OUT OF SCOPE**
**PRD Reference**: Section 3.2.3 (Dynamic Upsell/Bridging)
**Blockers**:
- ❌ Unclear delivery mechanism (Issue 4)
- ❌ Is this Google Ads ad extension copy or landing page copy?
- ❌ If ad extensions: AssetService architecture missing (Gap 4)

**Acceptance Criteria** (Currently Undefined):
- For EDUCATION: Generate webinar transition script
- For SAAS: Generate demo booking nudge
- For SERVICE: Generate consultation value stack

**Recommendation**:
- **Option 1**: Scope as "text deliverable" (agent outputs copy, user manually implements)
- **Option 2**: Defer to Phase 2 with full Asset Pipeline implementation

---

### US-005: Growth-Tier Budget Management
**As a** user
**I want to** automatically allocate a ₹20,000 budget across 30 days
**So that** I can unlock the ₹20,000 platform credit

**Status**: ⚠️ **PARTIAL SCOPE**
**PRD Reference**: Section 3.3.1 (Growth-Tier Financial Constraints)
**Blockers**:
- ⚠️ Static formula `Daily Budget = Total / 30` contradicts Golden Ratio research (Gap 6)
- ❌ No dynamic scaling logic for winning campaigns
- ❌ No circuit breaker for runaway spend

**Current Implementation**:
- ✅ ₹660/day flat budget
- ✅ Maximize Clicks with ₹50 cap

**Research-Recommended Enhancement** (Currently Missing):
- Fibonacci scaling: Next budget = Current × 1.618
- LTV:CAC ratio monitoring
- Automated pause at 1:1 ratio

**Acceptance Criteria** (Minimal Scope):
- Campaign budget set to ₹20,000
- Daily budget constraint enforced
- Bidding strategy: Maximize Clicks with cap

**Should Add** (for production readiness):
- REQ-NEW-6: Implement Golden Ratio budget adjustment algorithm
- REQ-NEW-7: Daily spend monitoring to ensure ₹20k threshold met in 60 days

---

### US-006: Keyword Expansion with Safety
**As a** user
**I want to** use phrase match keywords with automatic negative keyword deployment
**So that** I can capture intent variation without wasting budget on irrelevant traffic

**Status**: ✅ **IN SCOPE**
**PRD Reference**: Section 3.3.2 (Keyword Expansion Protocol)
**Implementation**:
- ✅ Phrase match strategy defined
- ✅ Universal negative list specified (free, cheap, crack, job)
- ✅ Vertical-specific negatives (LLM-generated)

**Acceptance Criteria**:
- Keywords created with PHRASE match type
- Universal negatives applied to all campaigns
- LLM generates 10+ vertical-specific negatives

**Technical Acceptance Criteria**:
- Keyword match type: `KeywordMatchType.PHRASE` (Google Ads API enum)
- Universal Negative List (REQ-9, PRD:215-218):
  - Hardcoded: ["free", "cheap", "crack", "torrent", "download", "job", "career", "hiring", "apply"]
  - Implementation: `SharedSetService.mutate` to create shared negative keyword list
  - Apply to all campaigns via `CampaignSharedSetService`
- Vertical-Specific Negatives:
  - LLM prompt: "Generate 10-15 negative keywords for {vertical_type} offer {offer_name}"
  - Validation: Minimum 10 negatives returned
  - Storage: Campaign-level via `CampaignCriterionService.mutate`
- Funnel Sculpting (REQ-9):
  - Tier 1 keywords added as negatives in Tier 2 campaign
  - Tier 2 keywords added as negatives in Tier 3 campaign
  - Prevents "awareness" keywords from triggering "consideration" campaigns
- Unit test: Verify shared set creation + campaign linkage
- Integration test: Workshop example → universal list applied to all 3 personas

**Google Ads API Requirement** (Now Addressed):
- ✅ REQ-9: Negative keyword management architecture (PRD:215-218)
- ✅ `SharedSetService` for universal list specified
- ✅ Funnel sculpting pattern documented

---

### US-007: Campaign Setup Workflow
**As a** user
**I want to** review and approve the generated campaign structure before launch
**So that** I maintain control over what ads run

**Status**: ⚠️ **PARTIAL SCOPE**
**PRD Reference**: Section 4.1 (The Setup - Day 0)
**Blockers**:
- ❌ No UX specification for "User Review" interface
- ❌ No agent-human interaction pattern defined
- ✅ Workflow sequence is logical

**Acceptance Criteria**:
- Agent drafts: Keywords, Negatives, Ads
- User receives structured output for review
- User can approve/edit before API submission

**Missing Architecture**:
- How does user provide feedback? (CLI? Web UI? Conversational?)
- Claude SDK supports `permission_mode='ask'` for tool approval (research: google-ads-claude-code.md:311)

**Recommendation**:
- REQ-NEW-10: Implement "ask permission" mode for campaign creation tools
- REQ-NEW-11: Define user feedback schema (approve | edit | reject)

---

### US-008: Real-Time Performance Monitoring (Days 1-14)
**As a** user
**I want to** automatically detect and kill underperforming ad angles based on CTR
**So that** I don't waste budget on ineffective creative

**Status**: ❌ **OUT OF SCOPE** (as specified)
**PRD Reference**: Section 4.2 (The Ramp)
**Blockers**:
- ❌ "Real-time" CTR checking not feasible (Issue 2)
- ❌ Google Ads metrics have 2-3 hour delay
- ❌ Statistical significance requires 24-48 hours minimum

**PRD Spec**: "Is CTR > 1%? If no, kill Angle"
**Reality**: Can only check every 24-48 hours

**Acceptance Criteria** (Revised):
- Daily check (not real-time) for ad CTR
- If CTR < 1% after 100+ impressions: Pause ad
- Request new creative variant from LLM

**Technical Acceptance Criteria**:
- REQ-11 implementation (PRD:237-241):
  - Frequency: Daily cron job (not real-time due to API delay)
  - GAQL query:
    ```sql
    SELECT
      ad_group_ad.ad.id,
      metrics.ctr,
      metrics.impressions,
      ad_group_ad.status
    FROM ad_group_ad
    WHERE
      metrics.impressions > 100
      AND campaign.id = {campaign_id}
      AND segments.date DURING LAST_7_DAYS
    ```
  - Threshold logic: `if ctr < 0.01 AND impressions > 100`
  - Action: `AdService.mutate(ad_id, status=AD_STATUS_PAUSED)`
  - Trigger: Call persona generation agent (TASK-023) to create replacement ad
- Error handling: Handle API exceptions, log failed pause attempts
- Monitoring: Track paused ads count, alert if >50% of ads paused (indicates larger issue)
- Integration test: Mock low-CTR ad → verify pause mutation called

**Missing Requirements** (Now Addressed):
- ✅ REQ-11: CTR monitoring specification (PRD:237-241)
- ✅ Minimum impression threshold: 100 (documented)
- ✅ GAQL query structure defined
- ✅ AdService mutation pattern specified

---

### US-009: Automated Optimization (Days 15+)
**As a** user
**I want to** automatically pause losing personas and increase bids on winning ones
**So that** my ROI improves over the campaign lifecycle

**Status**: ⚠️ **PARTIAL SCOPE**
**PRD Reference**: Section 4.3 (The Optimization)
**Blockers**:
- ⚠️ "Losing Persona" metric not defined (High CPC + Low Conv)
- ❌ No conversion tracking setup specified
- ❌ Bid increase logic ("+20%") conflicts with "Maximize Clicks" strategy

**Current Spec**:
- Action 1: Pause high CPC, low conversion ad groups
- Action 2: Increase bid cap by 20% on winners

**Technical Issue**:
- If using "Maximize Clicks" bidding: You don't control bids directly
- If using Manual CPC: You can adjust keyword-level bids
- PRD mixes strategies (Contradiction 1)

**Acceptance Criteria** (Needs Clarification):
- Define "Losing": `cost_per_conversion > target_cpa` OR `conversions = 0 AND spend > ₹2000`
- Action: Pause ad group via `AdGroupService.mutate`
- Bid adjustment: Only applicable if using Manual CPC or bid caps

**Missing Requirements**:
- REQ-NEW-15: Specify conversion tracking implementation
- REQ-NEW-16: Define target CPA per vertical
- REQ-NEW-17: Align bidding strategy with optimization actions

---

### US-010: Multi-Vertical Campaign Examples
**As a** user
**I want to** see example configurations for Workshop, Dentist, and SaaS verticals
**So that** I understand how to configure my specific use case

**Status**: ✅ **IN SCOPE** (Documentation)
**PRD Reference**: Section 5 (Deployment Scenarios)
**Implementation**:
- ✅ Workshop example provided
- ✅ Local Service (Invisalign) example provided
- ✅ Micro-SaaS example provided

**Acceptance Criteria**:
- Each example includes: Input configuration, Expected output (personas, ads, bridge)
- Examples cover different `monetization_model` types

**Note**: These are illustrative, not functional requirements

---

## 🚫 Currently Blocked User Stories (Out of Scope)

### US-BLOCKED-001: Automated Policy Exemption Handling
**Status**: ❌ **BLOCKED**
**Why**: No policy compliance architecture (Gap 5)
**Required**: Try-Catch-Exempt-Retry algorithm from research (google-ads-2-claude-agent.md:5.2)

**What's Missing**:
- Exception handling for `GoogleAdsException`
- `PolicyValidationParameter` construction
- Automated exemption request submission

**User Impact**: Campaigns will get stuck in DISAPPROVED state, requiring manual intervention

---

### US-BLOCKED-002: Custom Audience Creation
**Status**: ❌ **BLOCKED**
**Why**: No CustomAudienceService implementation (Implied by PRD but not specified)
**Required**: Section 2 of google-ads-2-claude-agent.md

**What's Missing**:
- `CustomAudienceMember` construction (Keywords, URLs, Apps)
- `AdGroupCriterionService` linkage
- AUTO vs PURCHASE_INTENT type selection

**User Impact**: Can only use keyword targeting, not audience layering

---

### US-BLOCKED-003: Predictive Budget Forecasting
**Status**: ❌ **BLOCKED**
**Why**: No `KeywordPlanIdeaService` integration
**Required**: Section 3 of google-ads-2-claude-agent.md

**What User Wants**:
- "Before launching, show me expected clicks, CPC, and conversions"

**What's Missing**:
- `CampaignToForecast` simulation object
- `GenerateKeywordForecastMetrics` API call
- Geo and language modifiers configuration

**User Impact**: No pre-launch performance estimates, blind budget allocation

---

### US-BLOCKED-004: Visual Asset Management
**Status**: ❌ **BLOCKED**
**Why**: No AssetService architecture (Gap 4)
**Required**: Section 4 of google-ads-2-claude-agent.md

**What User Wants**:
- "Generate and upload images for my Display campaigns"

**What's Missing**:
- Base64 encoding pipeline
- Dimension validation (aspect ratios)
- Asset-to-campaign linking

**User Impact**: Text-only ads, no visual creative

---

### US-BLOCKED-005: Agent Runtime Persistence
**Status**: ❌ **BLOCKED**
**Why**: No Claude Agent SDK initialization architecture (Gap 1)
**Required**: Section 2.3, 6, 7 of claude-agents-sdk-1.md

**What User Wants**:
- "Run the agent continuously to monitor and optimize campaigns"

**What's Missing**:
- `ClaudeSDKClient` setup
- Tool registration pattern
- Agentic loop implementation

**User Impact**: No autonomous operation, manual execution only

---

### US-BLOCKED-006: Session Forking for Parallel Testing
**Status**: ❌ **BLOCKED**
**Why**: Advanced SDK feature not in PRD scope
**Required**: Section 6.1 of claude-agents-sdk-1.md

**What Power User Wants**:
- "Test 3 different campaign strategies in parallel, pick the winner"

**What's Missing**:
- `fork_session=True` implementation
- Planner-Worker-Evaluator architecture
- Result convergence logic

**User Impact**: Sequential testing only, slower iteration

---

## 📊 Scope Summary

| Category | Count | Percentage |
|----------|-------|------------|
| ✅ **Fully In Scope** | 3 | 30% |
| ⚠️ **Partially In Scope** | 4 | 40% |
| ❌ **Out of Scope / Blocked** | 9 | ~60% |

**Key Insight**: While the PRD describes an ambitious vision, **60% of user value is currently blocked by missing technical architecture**.

---

## 🎯 Recommended Prioritization

### Phase 1: Minimum Viable Agent (Core 30%)
Focus on fully specified features:
1. US-001: Configuration input
2. US-006: Keyword expansion with negatives
3. US-010: Documentation examples

### Phase 2: Fill Critical Gaps (Enable 40%)
Address blockers for partial-scope stories:
1. US-BLOCKED-005: Claude Agent SDK runtime (CRITICAL)
2. US-BLOCKED-001: Policy compliance handling (CRITICAL)
3. US-002: Persona generation (with proper SDK)
4. US-003: Polarity ad copy generation

### Phase 3: Advanced Features (Unlock Final 30%)
1. US-BLOCKED-003: Predictive forecasting
2. US-BLOCKED-002: Custom Audience creation
3. US-009: Automated optimization (with proper bidding)
4. US-BLOCKED-004: Visual asset management

### Phase 4: Enterprise Scale
1. US-BLOCKED-006: Session forking and parallel testing
2. Multi-agent orchestration
3. Advanced reporting dashboards

---

## ✅ Acceptance Testing Notes

For stories marked "IN SCOPE", implementation can proceed with current PRD.
For "PARTIAL SCOPE", technical specifications must be added before development.
For "OUT OF SCOPE", architectural design work is required.

**Next Steps**:
1. Review this categorization with product stakeholders
2. Prioritize which blocked stories are MVP-critical
3. Create technical specifications for Phase 2 gaps
4. Update PRD with missing REQ-NEW-* requirements
