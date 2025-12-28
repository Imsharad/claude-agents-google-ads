---
**FILE SUMMARY**: Campaign Management APIs - Bidding, Budgets & Attribution
**RESEARCH QUESTIONS**: RQ-012 to RQ-015
**KEY TOPICS**: Bidding strategies (tCPA, tROAS, Maximize Clicks with CPC cap), portfolio vs standard strategies, budget scaling (Golden Ratio), learning phase constraints, conversion attribution, negative keyword shared sets
**CRITICAL PATTERNS**: Bidding strategy migration, data pooling with portfolio strategies, budget circuit breakers, warm-up phases for new campaigns
**USE THIS FOR**: Creating campaigns programmatically, implementing budget scalers, managing bidding strategies
---

# Google Ads API v22 Campaign Management Architecture: A Comprehensive Technical Report

## Executive Summary

The architectural landscape of programmatic advertising has evolved from simple resource manipulation to complex, event-driven orchestration. For engineering teams and solution architects tasked with building automated growth engines—specifically targeting the phases of Campaign Creation and Optimization—a superficial understanding of the Google Ads API is insufficient. The release of version 22 (v22) introduces critical changes to bidding configurations, budget handling, and conversion attribution that necessitate a rigorous re-evaluation of standard integration patterns.

This report provides an exhaustive technical analysis of the Google Ads API v22, focusing on the programmatic construction of sophisticated bidding strategies, robust budget scaling logic, and conversion attribution architectures. It addresses the specific requirements of creating growth-tier campaigns, implementing "Golden Ratio" budget scalers, and establishing airtight negative keyword funnels. The analysis extends beyond mere field definitions to explore the causal relationships between API objects, the implications of system latency and machine learning periods, and the architectural patterns necessary to build resilient, high-velocity advertising systems. By examining the interplay between the `CampaignService`, `BudgetService`, `ConversionActionService`, and `SharedSetService`, this document serves as a foundational blueprint for implementing TASK-024 (Growth Campaign Creation), TASK-032 (Budget Scaler), and TASK-027 (Negative Keyword Management).

---

## Section 1: Advanced Bidding Strategy Configuration (RQ-012)

The determination of a bidding strategy is the single most consequential decision in the lifecycle of a programmatic campaign. It dictates not only how the Google Ads auction algorithm values individual impressions but also how the campaign reacts to market volatility and competitive pressure. The API exposes these strategies as complex polymorphic objects, and successful implementation requires mapping business monetization models to these technical configurations with absolute precision.

### 1.1 Programmatic Bidding Architectures and Monetization Mapping

The Google Ads API distinguishes fundamentally between  **Standard Bidding Strategies** , which are attributes configured directly on a specific `Campaign` resource, and  **Portfolio Bidding Strategies** , which are independent resources (`BiddingStrategy`) shared across multiple campaigns. Understanding when to employ each is critical for scalable architecture.

#### 1.1.1 Standard Strategies: Direct Campaign Configuration

For isolated campaigns where performance data does not need to be aggregated for bidding decisions, or where distinct cost controls are required per campaign, standard strategies are the appropriate architectural choice. The following analysis maps the required monetization models to their API implementation details in v22.

##### Model A: "Maximize Conversions with Target CPA" (tCPA)

This model represents a shift from purely volume-based bidding to efficiency-based bidding. The objective is to acquire as many conversions as possible while adhering to a strict cost-per-acquisition (CPA) constraint.

* API Implementation Mechanics:
  To implement this programmatically, the Campaign resource's bidding_strategy_type field must be set to MAXIMIZE_CONVERSIONS. It is a common misconception that "Target CPA" is a distinct strategy type in the modern API. Instead, it is a configuration state of the MaximizeConversions object. To enable the "Target CPA" behavior, the developer must populate the target_cpa_micros field within the maximize_conversions sub-object.1
* Configuration Logic and Precision:
  The target_cpa_micros field accepts an integer value representing the monetary amount in micros (one millionth of the fundamental currency unit). For example, a Target CPA of ₹50 would be passed as 50,000,000. This high-precision integer format avoids floating-point errors common in financial calculations. Setting this field fundamentally alters the algorithm's objective function: it changes from spending the entire daily budget to constraining bids such that the weighted average cost of conversions converges on the target.
* Mutability and Dynamic Adjustment:
  A critical feature for the "Growth Tier" tool is the ability to adjust targets without effectively killing the campaign. The target_cpa_micros value is fully mutable via a standard CampaignOperation.update request. This allows for dynamic adjustment based on external business signals. For instance, if inventory levels are high, the system could programmatically raise the tCPA to increase volume; if profitability drops, it can lower the tCPA to tighten efficiency.
* The "Cold Start" Constraint:
  Programmatic creation of tCPA campaigns for new accounts with zero conversion history often results in "throttle" behavior, where the campaign serves very few impressions because the algorithm lacks the confidence to bid. The architectural pattern to solve this involves a "warm-up" phase. The system should initially create the campaign with MAXIMIZE_CLICKS or MAXIMIZE_CONVERSIONS (with no target set) to gather data. Once the metrics.conversions counter crosses a threshold (typically 15-30), the system updates the campaign to apply the target_cpa_micros constraint.4

##### Model B: "Target ROAS" (Return on Ad Spend)

This model is the gold standard for e-commerce and value-based lead generation. It optimizes for the *value* of conversions rather than the count.

* API Implementation Mechanics:
  The correct bidding_strategy_type is MAXIMIZE_CONVERSION_VALUE. Similar to tCPA, the specific "Target ROAS" behavior is activated by populating the target_roas field within the maximize_conversion_value object.7
* Value Calculation and Data Types:
  Unlike CPA, which uses micros, target_roas is a double value representing the return ratio. A target of 500% ROAS is passed as 5.0. A target of 250% is 2.5. The API handles the calculation of (Conversion Value / Cost) internally.
* Prerequisites and Dependency Chains:
  The implementation of tROAS introduces a hard dependency on ConversionAction configuration. It strictly requires that conversion values are being passed back to Google Ads. If metrics.conversions_value reports zero, the tROAS algorithm will mathematically determine that the optimal bid is zero, effectively stalling the campaign. Therefore, the initialization logic for tROAS campaigns must include a "Value Health Check".10
* Volume Thresholds:
  The statistical threshold for effective tROAS is higher than tCPA. The documentation suggests a minimum of 15 conversions with valid values in the last 30 days, but empirical stability is often observed only above 50 conversions.4

##### Model C: "Maximize Clicks with CPC Cap"

This strategy is often utilized for "Tripwire" or "Growth" campaigns where the primary objective is traffic acquisition and list building rather than immediate arbitrage.

* Architectural Ambiguity:
  There is frequently confusion between MANUAL_CPC and MAXIMIZE_CLICKS. MANUAL_CPC requires the API user to calculate and set specific bids for every keyword. MAXIMIZE_CLICKS cedes control to Google to get the most volume within the budget. However, without a safety rail (CPC Cap), MAXIMIZE_CLICKS can sometimes bid exorbitantly high for a single click if the budget allows.
* v22 API Implementation (Critical Update):
  Historically, this strategy was configured using the TargetSpend object. In API v22, TargetSpend is deprecated. The correct implementation now involves setting the bidding_strategy_type to MAXIMIZE_CLICKS and configuring the cpc_bid_ceiling_micros field directly inside the maximize_clicks object on the Campaign resource.13 This instructs the algorithm to bid for maximum volume but never to exceed the specified micro amount for a single click auction.
* Optimization Use Case:
  This is the primary strategy for the "Growth Tier" campaigns (Task-024). It allows the system to force traffic into the funnel to establish LTV baselines. The cpc_bid_ceiling_micros can be dynamically adjusted (Task-033) based on the Impression Share metrics. If search_impression_share is low due to rank, the scaler can incrementally raise the ceiling.

### 1.2 Portfolio Bidding Strategies: The Cross-Campaign Architecture

For sophisticated architectures involving multiple "personas" or ad groups that share similar economic characteristics, Portfolio Bidding Strategies offer significant advantages over campaign-level settings.

* Resource Definition:
  The BiddingStrategy is an independent resource in the API, distinct from the Campaign. It possesses its own resource name (customers/{id}/biddingStrategies/{id}) and lifecycle.15
* Linking Mechanism:
  To implement a portfolio strategy, the system first creates the BiddingStrategy using the BiddingStrategyService. The resulting resource name is then stamped onto the bidding_strategy field of one or more Campaign objects during creation or update.
* Data Aggregation Benefits:
  The primary architectural advantage is data pooling. If an advertiser has 10 campaigns targeting different geographic regions but selling the same product, a campaign-level tCPA strategy would require each campaign to learn independently (15 conversions * 10 campaigns = 150 conversions needed). A Portfolio Strategy aggregates the conversion data across all 10 campaigns, allowing the algorithm to learn from the pooled 150 conversions immediately. This significantly reduces the "Learning Phase" duration.15
* Unified Control Plane:
  Portfolio strategies decouple the efficiency target from the budget. A unified tCPA of ₹500 can be set at the portfolio level, while individual campaigns maintain their own daily budgets (or share a budget). A single mutate operation on the BiddingStrategy resource propagates the new target to all linked campaigns instantly, ensuring operational consistency.
* Recommendation for Golden Ratio Scaler:
  For Task-032, using Portfolio Strategies is strongly recommended. It simplifies the logic: the scaler adjusts the budgets on individual campaigns to control pacing and exposure, while a separate optimization process adjusts the portfolio target to control efficiency.

### 1.3 Bidding Strategy Migration and the Learning Phase

Transitioning a live campaign from a traffic-focused strategy (Maximize Clicks) to a conversion-focused strategy (Target CPA) is a non-destructive but operationally impactful event.

* Transition Mechanism:
  The migration is executed via a CampaignOperation.update call. The operation must include a field_mask that clears the old strategy fields (e.g., setting maximize_clicks to null or simply overwriting the bidding_strategy_type).
* Data Continuity vs. Algorithmic Reset:
  It is crucial to understand that historical performance data (clicks, impressions, conversion counts) remains associated with the campaign ID. However, the bidding algorithm's internal predictive model effectively resets or enters a recalibration mode. The algorithm must now learn how to bid for conversions rather than clicks.6
* The Learning Phase:
  While the UI displays a "Learning" status, the API exposes this state via the Campaign.bidding_strategy_system_status field. This period typically lasts 7 days or until sufficient data is gathered.
  * **Volume Requirements** : 15+ conversions in 30 days for tCPA; 50+ for tROAS.
  * **Reset Triggers** : The "Golden Ratio Budget Scaler" must be designed to avoid triggering inadvertent learning resets. Significant changes—such as budget increases greater than 20-30% in a single day, or target changes greater than 20%—can force the algorithm back into learning mode, causing performance volatility.^5^
* Migration Guardrails:
  Automated migration logic should be gated by a "Data Sufficiency Check." Before switching a campaign to tCPA, the system should query campaign metrics for the LAST_30_DAYS. If metrics.conversions < 15, the migration should be blocked, or the campaign should be flagged for manual review.

### 1.4 Code Implementation Examples (Python)

The following sections provide concrete Python implementation patterns using the `google-ads` client library, specifically tailored for API v22.

#### 1.4.1 Configuration for "Maximize Conversions with Target CPA"

**Python**

```
from google.ads.googleads.client import GoogleAdsClient
from google.api_core import protobuf_helpers
import uuid

def create_tcpa_campaign(client, customer_id, budget_resource_name):
    """
    Creates a Search campaign with Maximize Conversions bidding strategy 
    and a specific Target CPA.
    """
    campaign_service = client.get_service("CampaignService")
    campaign_operation = client.get_type("CampaignOperation")
    campaign = campaign_operation.create

    # Basic Campaign Identity
    campaign.name = f"Growth Tier - tCPA - {uuid.uuid4()}"
    campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
    campaign.status = client.enums.CampaignStatusEnum.PAUSED
    campaign.campaign_budget = budget_resource_name
  
    # Bidding Strategy Configuration: Maximize Conversions with Target CPA
    campaign.bidding_strategy_type = client.enums.BiddingStrategyTypeEnum.MAXIMIZE_CONVERSIONS
    # Note: target_cpa_micros is a field ON the maximize_conversions object
    campaign.maximize_conversions.target_cpa_micros = 50000000  # 50.00 currency units (e.g., ₹50)
  
    # Network Settings (Search Network Only for higher intent)
    campaign.network_settings.target_google_search = True
    campaign.network_settings.target_search_network = True
    campaign.network_settings.target_content_network = False # Disable Display Expansion
    campaign.network_settings.target_partner_search_network = False
  
    # Issue Mutate Request
    try:
        response = campaign_service.mutate_campaigns(
            customer_id=customer_id, 
            operations=[campaign_operation]
        )
        return response.results.resource_name
    except Exception as ex:
        print(f"Campaign creation failed: {ex}")
        return None
```

#### 1.4.2 Configuration for "Maximize Clicks with CPC Cap" (v22 Spec)

**Python**

```
def create_max_clicks_campaign(client, customer_id, budget_resource_name):
    """
    Creates a campaign with Maximize Clicks strategy and a Bid Ceiling.
    Uses the v22 maximize_clicks object, replacing deprecated TargetSpend.
    """
    campaign_service = client.get_service("CampaignService")
    operation = client.get_type("CampaignOperation")
    campaign = operation.create
  
    campaign.name = f"Growth Tier - MaxClicks - {uuid.uuid4()}"
    campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
    campaign.status = client.enums.CampaignStatusEnum.PAUSED
    campaign.campaign_budget = budget_resource_name
  
    # Bidding Configuration
    campaign.bidding_strategy_type = client.enums.BiddingStrategyTypeEnum.MAXIMIZE_CLICKS
    # In v22, set the bid ceiling directly on the maximize_clicks object
    campaign.maximize_clicks.cpc_bid_ceiling_micros = 20000000 # 20.00 currency units (e.g., ₹20)
  
    # Network Settings
    campaign.network_settings.target_google_search = True
    campaign.network_settings.target_search_network = True
  
    try:
        response = campaign_service.mutate_campaigns(
            customer_id=customer_id, 
            operations=[operation]
        )
        return response.results.resource_name
    except Exception as ex:
        print(f"Max Clicks Campaign creation failed: {ex}")
        return None
```

#### 1.4.3 Portfolio Bidding Strategy Creation Pattern

**Python**

```
def create_portfolio_strategy(client, customer_id):
    """
    Creates a Portfolio Bidding Strategy (Shared Strategy) for Target ROAS.
    This resource can then be linked to multiple campaigns.
    """
    bs_service = client.get_service("BiddingStrategyService")
    operation = client.get_type("BiddingStrategyOperation")
  
    strategy = operation.create
    strategy.name = f"Portfolio tROAS Strategy - {uuid.uuid4()}"
    strategy.type_ = client.enums.BiddingStrategyTypeEnum.MAXIMIZE_CONVERSION_VALUE
    strategy.maximize_conversion_value.target_roas = 4.5 # 450% ROAS
  
    try:
        response = bs_service.mutate_bidding_strategies(
            customer_id=customer_id, 
            operations=[operation]
        )
        resource_name = response.results.resource_name
        print(f"Created Portfolio Strategy: {resource_name}")
        return resource_name
    except Exception as ex:
        print(f"Strategy creation failed: {ex}")
        return None
```

### 1.5 Field Mapping Summary Table

The following table summarizes the mapping between the Monetization Models required in REQ-3 and the specific Google Ads API v22 fields.

| **Monetization Model**     | **API Bidding Strategy Type** | **Configuration Object** | **Key Configuration Field** | **Value Format**    |
| -------------------------------- | ----------------------------------- | ------------------------------ | --------------------------------- | ------------------------- |
| **Max Conversions (tCPA)** | `MAXIMIZE_CONVERSIONS`            | `maximize_conversions`       | `target_cpa_micros`             | Integer (Micros)          |
| **Target ROAS**            | `MAXIMIZE_CONVERSION_VALUE`       | `maximize_conversion_value`  | `target_roas`                   | Double (Ratio, e.g., 5.0) |
| **Max Clicks (Cap)**       | `MAXIMIZE_CLICKS`                 | `maximize_clicks`            | `cpc_bid_ceiling_micros`        | Integer (Micros)          |
| **Manual CPC**             | `MANUAL_CPC`                      | `manual_cpc`                 | `enhanced_cpc_enabled`          | Boolean                   |

---

## Section 2: Budget Scaling & Pacing Architecture (RQ-013)

The "Golden Ratio Budget Scaler" (TASK-032) requires a highly responsive and safe mechanism to adjust campaign spend. The `BudgetService` and `CampaignBudget` resources serve as the control valve for the advertising engine, regulating the "fuel" supplied to the bidding algorithms.

### 2.1 Programmatic Budget Operations and Mutability

In the Google Ads API architecture, the `CampaignBudget` is a distinct resource separate from the `Campaign`. This separation allows for "Shared Budgets," where multiple campaigns draw from a single monetary pool, or standard 1:1 mappings.

* Update Mechanism:
  Budgets are modified using the CampaignBudgetService.mutate_campaign_budgets method. It is critical to note that you do not update the Campaign to change the budget amount; you update the Budget resource linked to the campaign.
* Latency and Freshness:
  Budget updates are near real-time regarding ad serving eligibility. If a campaign is capped and the budget is increased, ads will typically resume serving within 15-60 minutes. However, the reporting metrics (metrics.cost_micros) often have a latency of 3-24 hours. This creates a dangerous blind spot for automated scalers: a script might see "low spend" at 10:00 AM, increase the budget, and inadvertently cause overspend because the actual spend from 8:00 AM to 10:00 AM hadn't fully reported yet.
* Request Structure:
  The update operation utilizes a FieldMask to ensure that only the amount_micros field is modified, leaving other settings (like the budget name or delivery method) untouched.

### 2.2 The Deprecation of Accelerated Delivery

Historically, advertisers utilized "Accelerated" delivery to force the system to enter every eligible auction immediately, spending the budget as fast as possible. This was a key tactic for "Tripwire" campaigns aiming for rapid data gathering.

* Current Architectural State:
  Accelerated delivery has been deprecated and removed for Search, Shopping, and shared budgets in the API.18 All new budgets created via the API will default to STANDARD delivery. If an application attempts to set the delivery_method field to ACCELERATED, the API will return an OperationAccessDenied.ACTION_NOT_PERMITTED error.20
* Implication for Pacing Controls:
  Google's STANDARD delivery creates a "smooth" pacing curve, aiming to distribute ad impressions evenly throughout the 24-hour day. This runs counter to the objective of a "Tripwire" campaign that might need to spend ₹2,000 in the first hour to validate a concept.
  * **Workaround Strategy** : Since we cannot force "Accelerated" delivery via the Budget resource, "front-loading" spend must be simulated via  **bid aggression** . By using a `MAXIMIZE_CLICKS` strategy with a high `cpc_bid_ceiling_micros`, the campaign becomes competitive in a wider range of auctions. If the bid is high enough to win near 100% of eligible impressions (`search_impression_share` > 90%), the budget will naturally be consumed rapidly, effectively overriding the pacing smoothing algorithm by hitting the cap purely on volume velocity.

### 2.3 LTV:CAC Ratio Calculation Methodology

The "Golden Ratio" logic posits that budget should be increased only when the Unit Economics (LTV:CAC) are healthy. The API provides the cost data, but the "Value" data often requires synthesis.

* **CAC (Customer Acquisition Cost) Calculation** :
* **Formula** : `metrics.cost_micros / metrics.conversions`.
* **Granularity** : While the scaler operates on individual campaigns, the CAC calculation should ideally be evaluated at the **Portfolio** or **Ad Group** level to smooth out variance. A single expensive click shouldn't halt scaling if the overall trend is positive.
* **Time Window** : A 30-day rolling window (`segments.date DURING LAST_30_DAYS`) is the industry standard. It smooths out daily volatility (e.g., weekends vs. weekdays) while remaining responsive to recent trend shifts.
* LTV (Lifetime Value) Sourcing:
  The API does not natively store "LTV" unless sophisticated offline conversions are uploaded with predicted future values.
  * **Option A (Google Native)** : If conversion values are accurately passed (e.g., via `upload_enhanced_conversions_for_web`), `metrics.conversions_value` represents immediate revenue. LTV can be estimated as `conversions_value * recurring_multiplier`.
  * **Option B (External CRM - Recommended)** : The most robust architecture involves the application ingesting LTV cohorts from an external CRM or Data Warehouse. The application calculates the allowable CAC internally (`LTV / Target_Ratio`) and then queries the API to see if the current campaign performance meets this threshold.

### 2.4 Circuit Breaker Implementation and the Overdelivery Rule

The requirement for a "Circuit Breaker" (REQ-10: ₹2,000 max daily budget) acts as a fail-safe against runaway automation. However, Google's "Overdelivery" rule complicates this.

* The Overdelivery Nuance:
  Google Ads explicitly allows a campaign to overspend its daily budget by up to 2x on any given day, provided it does not exceed 30.4x the daily budget in a calendar month.21 This means a campaign with a ₹2,000 setting can technically spend ₹4,000 today.
* **Architectural Enforcement** :
* **Pre-Flight Check** : Before any scaling operation, the code must verify the current budget.
  **Python**

    ``    if current_daily_budget_micros >= 2000000000: # ₹2,000         return "MAX_LIMIT_REACHED"    ``

* **Intraday Monitoring** : To strictly enforce a ₹2,000 *spend* limit (counteracting the 2x Google allowance), a monitoring script must run frequently (e.g., hourly).
  1. Query `metrics.cost_micros` for `segments.date = 'TODAY'`.
  1. If `cost_micros > 2000000000 * 0.9` (90% threshold), the script must issue a `CampaignOperation` to set `status = PAUSED`.
* **Warning** : Frequent pausing and unpausing of campaigns disrupts the machine learning of Smart Bidding strategies. A more stable approach is to set the API daily budget to `Limit / 2` (i.e., ₹1,000) if the hard cap of ₹2,000 is an absolute financial constraint that cannot be breached even once.

### 2.5 Tripwire Model Exception and Tagging Strategy

Tripwire campaigns are exempt from standard pause rules due to their strategic nature (loss leaders). Programmatic identification is essential.

* LabelService Architecture:
  The Label resource provides a robust tagging mechanism. Relying on string matching in campaign names (e.g., "CAMPAIGN_TRIPWIRE_...") is fragile.
* **Implementation Steps** :

1. **Create Label** : Use `LabelService` to create a label with text "TRIPWIRE_EXEMPT".
2. **Attach Label** : Use `CampaignLabelService` to link this label to the specific Tripwire campaigns.
3. **Query Logic** : When the budget scaler runs, it should first fetch the list of exempt campaign IDs.
   **SQL**

    ``     SELECT campaign.id       FROM campaign_label       WHERE label.name = 'TRIPWIRE_EXEMPT'     ``

1. **Exemption Logic** : If a campaign ID exists in this set, the Circuit Breaker logic is bypassed or modified (e.g., allowing a higher cap).

### 2.6 Budget Update Code Example

**Python**

```
def update_budget(client, customer_id, budget_resource_id, new_amount_micros):
    """
    Updates the amount of an existing CampaignBudget.
    """
    budget_service = client.get_service("CampaignBudgetService")
    operation = client.get_type("CampaignBudgetOperation")
  
    # Identify budget by resource name
    operation.update.resource_name = f"customers/{customer_id}/campaignBudgets/{budget_resource_id}"
    operation.update.amount_micros = new_amount_micros
  
    # FieldMask is critical: Update ONLY the amount, touch nothing else.
    client.copy_from(operation.update_mask, protobuf_helpers.field_mask(None, operation.update))
  
    try:
        response = budget_service.mutate_campaign_budgets(
            customer_id=customer_id, 
            operations=[operation]
        )
        return response.results.resource_name
    except Exception as ex:
        print(f"Budget update failed: {ex}")
        return None
```

---

## Section 3: Conversion Tracking Setup & Validation (RQ-014)

Conversion tracking is the nervous system of the advertising setup. Without accurate signals, Smart Bidding (tCPA, tROAS) is blind. The API allows for the programmatic creation of the *container* (ConversionAction), but the *collection* (Tagging) typically requires a hybrid implementation.

### 3.1 API Capabilities vs. Manual Setup

* Container Creation (ConversionActionService):
  The API can fully instantiate ConversionAction resources. You can define the name, type (e.g., WEBPAGE, UPLOAD), value settings, counting type (One vs. Many), and attribution models programmatically.23 This ensures consistent naming conventions across hundreds of accounts.
* Tag Generation Limitation:
  The API cannot physically place the JavaScript tag on the advertiser's website. While the UI can generate the snippet, the API assumes the tagging infrastructure (Google Tag or GTM) is handled separately.
* **The Hybrid Workflow** :

1. **API** : Create the `ConversionAction` (e.g., "Lead Form Submit").
2. **API** : Retrieve the `conversion_action.id` and `conversion_action.tag_snippets` (if available in the specific API version context, though often retrieved via UI).
3. **Manual/GTM** : Configure Google Tag Manager to fire a Google Ads Conversion Tag using the Conversion ID and Conversion Label generated by the creation event.

### 3.2 Conversion Action Types and Use Cases

The choice of `ConversionActionType` dictates how Google interprets the signal.

| **Use Case**        | **Recommended Type**      | **Description**                                                                                                                |
| ------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **TRIPWIRE_UPSELL** | `WEBPAGE`                     | Tracks a page load (e.g., "Thank You" page) after purchase. Best implemented via GTM Event or Pageview trigger.                      |
| **LEAD_GEN**        | `WEBPAGE`or `UPLOAD_CLICKS` | `WEBPAGE`for immediate form confirmation.`UPLOAD_CLICKS`for qualified leads imported from CRM later (Offline Conversion Import). |
| **BOOK_CALL**       | `PHONE_CALL`                  | Specifically `CALLS_FROM_ADS`(Call Extensions) or `CALLS_FROM_WEBSITE`(Dynamic Number Insertion).                                |
| **App Install**     | `APP_INSTALL`                 | Requires linking Google Play or Firebase.                                                                                            |

* Enhanced Conversions:
  For the LEAD_GEN model, standard cookie tracking is deteriorating due to browser privacy controls (ITP). The API supports upload_enhanced_conversions_for_web. This allows the server to send hashed first-party data (email, phone) back to Google to match against signed-in users, recovering lost attribution.25

### 3.3 Cross-Domain Tracking Architecture

For funnels that span multiple domains (e.g., Landing Page `example.com` -> Checkout `payment-gateway.com`), the standard first-party cookie set on `example.com` cannot be read by `payment-gateway.com`. If the conversion happens on the gateway, attribution is lost.

* The "Linker" Parameter (_gl):
  Google solves this by passing the click ID and cookie data in the URL query parameter _gl.
* **Implementation Requirements** :

1. Auto-Linking: If using gtag.js, the linker parameter must be configured with all domains in the funnel:
   gtag('set', 'linker', {'domains': ['example.com', 'payment-gateway.com']});
2. **Conversion Linker (GTM)** : If using GTM, the "Conversion Linker" tag must be deployed on *all* pages of *all* domains. It automatically handles the appending and reading of the `_gl` parameter.
3. **Validation** : A manual test is required. Click a link from Domain A to Domain B. Inspect the URL in the browser bar on Domain B. It *must* contain `?_gl=1*...`. If missing, the tracking is broken.^27^

### 3.4 Offline Conversion Import (OCI) Pattern

For the "Lead Gen" model where the final sale occurs offline (e.g., via a call center), OCI is the only way to optimize for ROAS.

* The GCLID is Key:
  The Google Click ID (GCLID) acts as the primary key joining the ad click to the offline event.
* **Architectural Flow** :

1. **Capture** : User clicks ad -> URL contains `?gclid=AbC...123`.
2. **Store** : The landing page script parses the URL and stores the GCLID in a hidden field on the lead form.
3. **Persist** : When the form is submitted, the GCLID is saved into the CRM `Lead` record.
4. **Qualify** : Days later, the lead converts to a sale. The CRM status updates.
5. **Upload** : A nightly Python script queries the CRM for new sales. It uses the `OfflineConversionUploadService` to send the `gclid`, `conversion_action` (Resource Name), `conversion_date_time`, and `conversion_value` back to Google.

* Latency & Windows:
  Google matches the GCLID to the original click. The "Click-through conversion window" (configurable on the ConversionAction, usually 90 days) defines how far back Google will look. Conversions uploaded outside this window are discarded.

### 3.5 Validation Logic (GAQL)

To programmatically validate that tracking is active:

**SQL**

```
SELECT
  conversion_action.id,
  conversion_action.name,
  conversion_action.status,
  metrics.conversions,
  metrics.conversions_value
FROM conversion_action
WHERE conversion_action.status = 'ENABLED'
  AND metrics.conversions > 0
DURING LAST_30_DAYS
```

* **Logic** : If an enabled conversion action has `metrics.conversions = 0` for the last 7-30 days while the campaigns are active (`impressions > 0`), the system should trigger a "Tracking Broken" alert.

---

## Section 4: Negative Keyword Shared Sets (RQ-015)

Managing negative keywords at the individual campaign level is inefficient (O(N) complexity) and prone to error. The `SharedSet` architecture offers a scalable, object-oriented approach (O(1) complexity) for traffic filtering.

### 4.1 Shared Sets vs. Campaign-Level Negatives

* **Scalability** : A single `SharedSet` can be linked to thousands of campaigns. Adding a new negative keyword (e.g., "scam") to the Shared Set instantly propagates this exclusion to all linked campaigns.
* **Limits** :
* **Shared Sets** : Max 20 shared negative keyword lists per account.
* **Keywords per Set** : Max 5,000 keywords.^29^
* **Campaign Level** : A campaign can have up to 10,000 individual negative keywords *in addition* to the shared sets.
* **Strategic Usage** :
* Use **Shared Sets** for "Universal Negatives" (e.g., competitor names, "free", "torrent", "crack") that apply to the entire account.
* Use **Campaign-Level Negatives** for specific "Funnel Sculpting" (e.g., excluding the exact term "running shoes" from the "shoes - broad" campaign to force it into the "running shoes - exact" campaign).

### 4.2 Automated Funnel Sculpting

REQ-9 specifies "Tier 1 keywords negative in Tier 2." This is a classic "Alpha/Beta" or "Tiered" structure designed to force traffic to the highest-value, lowest-cost keyword match.

* **Automation Pattern** :

1. **Extraction** : The script queries `ad_group_criterion` to retrieve all `ENABLED` keywords from Tier 1 (Exact Match) campaigns.
   **SQL**

    ``     SELECT ad_group_criterion.keyword.text       FROM ad_group_criterion       WHERE ad_group_criterion.keyword.match_type = 'EXACT'       AND campaign.name LIKE '%Tier 1%'     ``

1. **Transformation** : The script creates a list of `SharedCriterionOperation` objects.
2. **Application** :
   * Create a specific Shared Set named "Tier 1 Exclusions".
   * Add the extracted keywords to this set as **Negative Exact** matches.
   * Link this Shared Set to all Tier 2 (Broad/Phrase) campaigns.
3. **Synchronization** : This script must run nightly. If a new keyword is added to Tier 1, it must be added to the exclusion list to prevent the Tier 2 campaign from "stealing" the impression due to a potentially higher bid or Quality Score quirk.

### 4.3 Match Type Nuances for Negatives

It is critical to note that **Negative Match Types** behave differently than positive ones.

* **Negative Broad** : Blocks the ad *only* if the entire negative phrase is present in the query, regardless of order. It does **NOT** expand to synonyms or close variants. If the negative is "running shoes", it blocks "shoes running" but *not* "blue running shoes" or "runing shoes" (misspelling).
* **Negative Phrase** : Blocks if the words appear in the exact order. "running shoes" blocks "blue running shoes" but not "shoes running".
* **Negative Exact** : Blocks only the exact query "running shoes". It does not block "blue running shoes".
* Recommendation:
  For "Universal Negatives" (Shared Sets), use Negative Broad for single-word concepts (e.g., "free") to cast a wide net. Use Negative Phrase for specific multi-word concepts to avoid blocking legitimate long-tail queries.

### 4.4 Shared Set Creation Code Example

**Python**

```
def create_negative_shared_set(client, customer_id, set_name, keywords):
    """
    Creates a Shared Set and populates it with negative keywords.
    """
    shared_set_service = client.get_service("SharedSetService")
    criterion_service = client.get_service("SharedCriterionService")
  
    # 1. Create the Container (Shared Set)
    ss_op = client.get_type("SharedSetOperation")
    ss_op.create.name = set_name
    ss_op.create.type_ = client.enums.SharedSetTypeEnum.NEGATIVE_KEYWORDS
  
    ss_response = shared_set_service.mutate_shared_sets(
        customer_id=customer_id, operations=[ss_op]
    )
    shared_set_resource = ss_response.results.resource_name
  
    # 2. Create Operations for each Keyword
    criteria_ops =
    for kw in keywords:
        op = client.get_type("SharedCriterionOperation")
        op.create.keyword.text = kw
        op.create.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
        op.create.shared_set = shared_set_resource
        criteria_ops.append(op)
      
    # 3. Add Keywords to Set (Batching recommended for large lists)
    criterion_service.mutate_shared_criteria(
        customer_id=customer_id, operations=criteria_ops
    )
  
    return shared_set_resource
```

---

## Section 5: Implementation & Operational Excellence

### 5.1 Error Handling and Rate Limiting

The Google Ads API is a shared multi-tenant environment. Robust implementations must handle:

* **Rate Limits** : The API limits the number of `Mutate` operations (e.g., 15,000 operations/day for Basic Access). The "Budget Scaler" must be efficient, batching updates where possible.
* **Concurrency** : The API follows a "Last Write Wins" model. If two scripts attempt to update the same budget simultaneously, the second one overwrites the first. Using a job queue or database lock is essential to prevent race conditions.
* **Partial Failures** : When sending a batch of 100 operations, 90 might succeed and 10 fail. The application must inspect the `partial_failure_error` field in the response to identify and retry specific failed items.

### 5.2 Conclusion

The transition to API v22 brings powerful capabilities but demands stricter architectural discipline. The deprecation of `TargetSpend` and `Accelerated Delivery` forces a reliance on sophisticated Bidding Strategy configurations to control pace and cost. The "Golden Ratio" budget scaler and "Funnel Sculpting" mechanisms move the complexity from manual management to code, requiring rigorous error handling and validation logic.

By implementing the `CampaignService` configurations for bidding, the `BudgetService` logic for safe scaling, and the `SharedSet` architecture for negative keywords, the system achieves the requirements of Phase 2 and Phase 3: a scalable, automated growth engine that optimizes for unit economics rather than vanity metrics. The provided Python patterns serve as the kernel for these services, ready for integration into the broader application ecosystem.
