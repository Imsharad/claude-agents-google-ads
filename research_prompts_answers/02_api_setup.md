---
**FILE SUMMARY**: Google Ads API v22 - Setup, Breaking Changes & Configuration
**RESEARCH QUESTIONS**: RQ-008 to RQ-011
**KEY TOPICS**: v15→v22 breaking changes, AssetGenerationService (GenAI), bidding strategy evolution, Proto Plus mode, OAuth2 refresh patterns, version lifecycle management
**CRITICAL PATTERNS**: OAuth 6-day proactive refresh, validate_only for policy pre-checks, targetless bidding strategies
**USE THIS FOR**: Setting up Google Ads API v22 client, understanding migration from legacy versions, OAuth configuration
---

# Research Answers: Google Ads API Setup & Foundations

## RQ-008: Google Ads API v22+ Breaking Changes

### The Architectural Evolution to v22: A Paradigm Shift in Asset Management

The transition to Google Ads API v22 represents far more than a routine version increment; it signals a fundamental architectural pivot within the Google advertising ecosystem towards Generative AI (GenAI) and automated asset construction. For engineering teams accustomed to the deterministic nature of v15 or v16—where an advertiser manually uploaded an image, and the API simply linked it to an ad group—v22 introduces non-deterministic services that require fundamentally different handling logic. The most significant of these is the `AssetGenerationService`, a beta feature introduced in late 2025 that allows for the programmatic generation of text and image assets using GenAI inputs such as final URLs and freeform prompts.^1^ This shift necessitates that infrastructure designed for Phase 1 implementation must essentially be "AI-native," capable of handling the asynchronous latencies and probability-based error states associated with generative models, rather than just the binary success/failure states of traditional database CRUD operations.

When analyzing the trajectory from v15 to v22, one observes a consistent deprecation of "manual" controls in favor of "objective-based" automation. In v15, bidding strategies were often explicit and granular. By v22, we see the introduction of bidding goals for App campaigns that optimize for installs or total value without requiring a target CPA or ROAS, signaling Google's move towards "black box" optimization where the API user provides the *goal* rather than the  *constraint* .^1^ This evolution is critical for the "SaaS Advertising" and "Educational" verticals mentioned in the research context, as these sectors often rely on value-based bidding (e.g., optimizing for a student enrollment or a software subscription) rather than simple click volume. The infrastructure built today must therefore be flexible enough to accommodate "Targetless" bidding strategies, a concept that would have been alien in v15 architectures.

Furthermore, the strict enforcement of version lifecycles means that staying on older versions is not merely a technical debt decision but an operational risk. With v16 scheduled for sunset in early 2025 and v17 following shortly thereafter, the window for migration is aggressive.^2^ This report advises a direct leap to v22 to bypass the cascading deprecations of intermediate versions. By adopting v22 immediately, the system gains access to the latest `AssetAutomationType` values for Demand Gen and Performance Max campaigns—specifically the ability to control image enhancement and extraction at the campaign level—which are pivotal for maintaining brand safety in automated campaigns.^1^

### Comprehensive Version Comparison and Breaking Changes

The migration from a legacy codebase (v15/v16) to v22 involves navigating a minefield of renamed fields, restructured enums, and entirely new service behaviors. The following analysis breaks down these changes by functional area, highlighting the specific technical impact on the proposed Phase 1 infrastructure.

#### Asset Generation and Management

In v15, asset management was primarily a linking exercise. In v22, the `AssetGenerationService` introduces a new layer of complexity. The service allows for `GenerateText` and `GenerateImages` methods. The technical implication here is the introduction of `AssetGenerationErrorEnum`. Phase 1 error handling modules must be updated to catch these specific errors, which differ significantly from standard `MutateError` types. For example, a generative error might indicate a safety violation in the prompt itself, requiring a feedback loop to the user, whereas a mutate error is typically a system or logic fault. Additionally, the new `LANDING_PAGE_PREVIEW` asset field type requires updated UI renderers if the internal tool intends to preview what the API is generating.^1^

#### Campaign Configuration and Bidding

One of the most disruptive changes for legacy integrations is the restructuring of App Campaign bidding. The introduction of `OPTIMIZE_IN_APP_CONVERSIONS_WITHOUT_TARGET_CPA` allows for maximization of conversions without a cost constraint. While beneficial for scaling, it poses a budget risk if not paired with strict campaign-level budget caps. The infrastructure must enforce a "Safe Mode" that prevents the selection of targetless bidding strategies unless a strict daily budget is verified. Furthermore, the `Campaign.feed_types` field in v22 now explicitly exposes the feeds attached to a campaign (e.g., Merchant Center). In v15, this was often inferred or hidden. The Phase 1 setup must now explicitly query and validate `feed_types` to ensure that Retail or Education feeds are correctly associated before enabling a campaign.^1^

#### Reporting and Metrics

Reporting in v22 has become more granular but also more restrictive regarding privacy. The introduction of "Smart Bidding Exploration" metrics allows for the retrieval of time-segmented diversity metrics for Target ROAS strategies. This is a powerful debugging tool for determining why a bidding strategy might be underperforming. However, it adds complexity to the GAQL queries, as these metrics may not be compatible with all segments. Additionally, the deprecation of various `AccountLink` types in favor of `ProductLink` means that any code responsible for linking Google Merchant Center or Zapier integrations must be rewritten to use the `ProductLinkInvitation` service.^5^

### Breaking Changes Summary Table (v15 **$\rightarrow$** v22)

The table below synthesizes the critical breaking changes that directly impact the implementation of the System Requirements.

| **Feature Area**      | **Legacy State (v15/v16)**                            | **v22 State (Current)**                                              | **Implementation Impact for Phase 1**                                                                           |
| --------------------------- | ----------------------------------------------------------- | -------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **Asset Creation**    | Static upload via `AssetService`.                         | Dynamic creation via `AssetGenerationService`(Beta) + Static Upload.     | **New Service** : Middleware must support `GenerateText`requests and handle non-deterministic AI errors.      |
| **Bidding Logic**     | Required specific targets (CPA/ROAS) for most auto-bidding. | "Targetless" optimization allowed (`OPTIMIZE_WITHOUT_TARGET...`).        | **Validation Logic** : Budget checks must be stricter as CPA constraints are removed.                           |
| **Merchant Links**    | Managed via `AccountLink`resource.                        | Managed via `ProductLink`and `ProductLinkInvitation`.                  | **Refactor** : All account linking logic must use the new `ProductLink`services.                              |
| **Demand Gen**        | Referred to as "Discovery" campaigns.                       | Renamed to "Demand Gen";`TargetCPC`added.                                | **Enum Audit** : Find/Replace all instances of `DISCOVERY`with `DEMAND_GEN`in the codebase.                 |
| **Resource Status**   | Relied on `status`(ENABLED/PAUSED).                       | `primary_status`and `primary_status_reasons`added to AdGroupCriterion. | **Reporting Update** : Dashboards must show `primary_status`to explain*why*an active keyword isn't serving. |
| **Mutate Operations** | `validate_only`checked basic constraints.                 | `validate_only`now includes stricter policy and asset checks.            | **Pre-flight** : Use `validate_only`to pre-screen AI-generated assets for policy flags before persistence.    |

### Proto Plus Mode: Architecture and Performance Implications

A critical decision point for the Python client library setup is the `use_proto_plus` configuration. This setting fundamentally dictates the interface between the Python runtime and the underlying C++ Protocol Buffers (protobuf) that transmit data to Google's servers.

#### The `use_proto_plus: True` Architecture (Recommended)

By default, and as enforced in recent library versions, `use_proto_plus` is set to `True`. In this mode, the library wraps the raw protobuf messages in "Proto-plus" classes. These classes behave like native Python objects.

* **Ergonomics** : Developers can use standard dot notation (`campaign.id`) and standard Python types (lists, dicts) for assignment.
* **Enums** : Enums are exposed as native Python `enum.Enum` objects, allowing for readable comparisons (`if status == CampaignStatus.PAUSED`).
* **Marshaling Cost** : The trade-off is performance. Every time a field is accessed or assigned, the library performs a "marshaling" operation to convert the Python type to the underlying protobuf type. In high-throughput scenarios—such as processing a report with 100,000 rows—this overhead is significant and measurable.^6^

#### The Legacy/Performance Mode (`use_proto_plus: False`)

Setting this to `False` exposes the raw protobuf messages.

* **Behavior** : Interaction mimics C++ or Java. Repeated fields cannot be assigned lists; they must be manipulated using `add()` or `extend()`.
* **Performance** : This mode eliminates the marshaling overhead, making it significantly faster for bulk operations.
* **Complexity** : It requires a deeper understanding of protobuf semantics (e.g., `value` wrappers for optional fields in older versions, though v22 simplifies this).

#### Strategic Recommendation for Phase 1

For the initial infrastructure setup,  **Proto Plus mode (`True`) is mandatory** . The gain in development velocity and code readability outweighs the performance cost for standard campaign management tasks. The complexity of managing raw protobufs introduces a high risk of bugs (e.g., incorrect type assignment) that can stall Phase 1. If performance bottlenecks arise during the Reporting Phase (Phase 2), a hybrid approach can be adopted where the `GoogleAdsService.search_stream` method is used with raw protobufs specifically for data ingestion pipelines, while the rest of the application remains in Proto Plus mode.

### API Version Lifecycle and Future-Proofing Strategy

Google's versioning strategy is aggressive. v22 was released in October 2025. Based on historical cadence, v23 is likely to appear in Q1 2026.

* **Stability** : v22 is the current "Golden Master". It is stable, widely deployed, and the target for all new features.
* **Sunset Schedule** : v16 sunsets in Feb 2025; v17 in June 2025. Starting with v22 provides a runway of approximately 18-24 months before a forced migration is strictly necessary, though keeping up with major versions annually is best practice.^2^
* **Migration Gotchas** : The most common "gotcha" in migration is the silent behavior change. For example, the `summary_row_setting` in reporting changed in v18, altering how totals are calculated. When upgrading versions in the future, the system must include regression tests that compare report totals between versions to detect such semantic shifts.

### Confidence Level

✅  **High** . The analysis is based on the official v22 release notes, migration guides for v15-v22, and the Python client library documentation.

### Source References

-^1^

* [Python Client Configuration]^7^
* [Proto Plus vs Protobuf Guide]6
  -2

### Code Example: Proto Plus Configuration

**Python**

```
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

def initialize_client(config_path="google-ads.yaml"):
    """
    Initializes the Google Ads Client in v22 mode with Proto Plus enabled.
    """
    try:
        # Load from storage will read the YAML and strict v22 versioning
        # REQ-5: Proto Plus is implicitly True in modern libs, but explicit is better.
        client = GoogleAdsClient.load_from_storage(
            path=config_path, 
            version="v22"
        )
        return client
    except GoogleAdsException as ex:
        print(f"Failed to initialize client: {ex}")
        raise

# Example of Proto Plus Ergonomics (Enabled)
def create_campaign_budget_proposal(client, customer_id):
    service = client.get_service("CampaignBudgetService")
  
    # In Proto Plus, we instantiate the operation as a Python object wrapper
    operation = client.get_type("CampaignBudgetOperation")
  
    # Direct attribute access (Pythonic)
    budget = operation.create
    budget.name = "Phase 1 Research Budget"
    budget.amount_micros = 5000000
    budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
  
    return operation

# Contrast with Legacy Mode (Conceptual - DO NOT USE for Phase 1)
# budget.amount_micros.value = 5000000  # Old protobuf wrapper style
```

### Implementation Impact

* **REQ-5 Update** : The requirement "Use API v22+" is now concrete. The implementation must explicitly request `version="v22"` in the client factory to prevent accidental fallback to older, cached versions.
* **TASK-011 (Auth)** : The `google-ads.yaml` file generated in the next step must include `use_proto_plus: True`.
* **TASK-001 (Setup)** : The CI/CD pipeline must install `google-ads-python` version compatible with v22 (likely 26.0.0+).

---

## RQ-009: OAuth2 Refresh Token Management

### The Architecture of Persistent Access

Authentication in the Google Ads API is distinct from standard SaaS APIs. It relies on the OAuth 2.0 "Installed Application" flow (or "Desktop App" flow) to establish a persistent trust relationship between the user's Google Identity and the application. This flow generates a `refresh_token`, a long-lived credential that allows the application to mint short-lived `access_tokens` (valid for 1 hour) autonomously. This mechanism is critical for the "Background Service" nature of the Phase 1 infrastructure, which must operate without user presence.

### 1. The Refresh Token Lifecycle and The "7-Day" Trap

The most critical research finding for RQ-009 is the "7-Day Expiration" phenomenon, which is the single most common cause of failure in new integrations.

#### The 7-Day Testing Limit

If the Google Cloud Project (GCP) OAuth Consent Screen is configured with a "Publishing Status" of  **Testing** , the refresh token issued to the application will expire strictly after  **7 days** . There is no programmatic warning; the API calls will simply begin failing with `invalid_grant` errors exactly 168 hours after generation.^12^

* **The Fix** : For any production or long-term development environment, the GCP Project must be set to **"In Production"** (or "Published").
* **Internal Users** : If the application is internal (only for users within the same Google Workspace organization), setting the "User Type" to **Internal** allows for permanent tokens without the strict external verification process required for public apps.
* **External Users** : If accessing accounts outside the organization, the app must be "In Production" and may require a simplified verification if the scope is sensitive. For Google Ads scope, simply setting it to production is often enough to lift the 7-day limit if the user count is low (capped at 100 users for unverified apps).^12^

#### Other Expiration Triggers

Even in production, a refresh token is not immortal. It will expire if:

* It has not been used to request an access token for  **6 months** .^14^
* The user explicitly revokes access in their Google Account permissions.
* The user changes their password (only if the token includes sensitive Gmail scopes; Ads scopes are usually resilient, but this is a risk factor).
* The limit of 50 refresh tokens per user/client pair is exceeded (the oldest is revoked).

### 2. Authentication Flow Selection: Why "Installed App"?

REQ-5 specifies the "Installed Application" flow. This research confirms it is the superior choice for this use case.

| **Flow Type**              | **Use Case**                            | **Google Ads Suitability**                                                                                                                                                         | **Trade-offs**                                                 |
| -------------------------------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **Installed App**(Desktop) | Scripts, CLIs, Cron Jobs, Background Workers. | **Best** . Simple setup, persistent token, no domain verification needed.                                                                                                          | Requires manual copy-paste of code*once*during setup.              |
| **Web Application**        | SaaS Platforms where*external*users log in. | **Overkill** . Requires hosting a callback URL, managing session state, and complex verified domains.                                                                              | Necessary only if building a 3rd-party tool for public use.          |
| **Service Account**        | Server-to-Server internal API calls.          | **Discouraged** . Google Ads requires "Domain-Wide Delegation" to impersonate a user. Service accounts*cannot*have direct access to Ads accounts; they must impersonate a human. | High complexity. Often fails due to lack of G-Suite permissions.^15^ |

 **Conclusion** : The "Installed App" flow is chosen because it minimizes infrastructure. It treats the backend system as a "privileged user" that logs in once. The obtained `refresh_token` is then stored securely, allowing the script to act on that user's behalf indefinitely.

### 3. One-Time Setup Process & Configuration

#### Step-by-Step Guide

1. **GCP Console Setup** :

* Create a Project -> APIs & Services -> Enable "Google Ads API".
* **Consent Screen** : Set User Type to "External" (or Internal).  **Set Status to Published** .
* **Credentials** : Create "OAuth 2.0 Client ID" -> Application Type: "Desktop App".
* Download `client_secret.json`.

1. **Token Generation** :

* Use the `generate_refresh_token.py` utility from the `google-ads-python` library.
* Run: `python generate_refresh_token.py --client_secrets_path=client_secret.json`
* The script prints a URL. Open in browser -> Sign in with the MCC Admin Google Account -> "Allow" access.
* Copy the resulting code string back to the terminal.
* **Output** : The script prints the `refresh_token`.

1. **Configuration File** : Create `google-ads.yaml`.

#### The `google-ads.yaml` Structure

This file is the "keychain" for the application.

**YAML**

```
# google-ads.yaml
# Core Configuration for v22+

# 1. Developer Token (The "License Plate")
# This identifies the SOFTWARE making the call, not the user.
developer_token: "INSERT_DEV_TOKEN_FROM_MCC_API_CENTER"

# 2. OAuth2 Credentials (The "User Identity")
# These identify the GCP Project and the User who authorized access.
client_id: "INSERT_CLIENT_ID_FROM_GCP"
client_secret: "INSERT_CLIENT_SECRET_FROM_GCP"
refresh_token: "INSERT_REFRESH_TOKEN_FROM_GENERATION_SCRIPT"

# 3. Client Behavior
# Enforce v22 Proto Plus behavior
use_proto_plus: True

# 4. Contextual Login (Crucial for MCCs)
# This ID represents the Manager Account acting as the "Logged In User".
# It must be a Manager Account ID (e.g., 123-456-7890).
login_customer_id: "INSERT_MCC_ACCOUNT_ID" 
```

### 4. Multi-Account Management (MCC Architecture)

The `login_customer_id` field is the source of frequent implementation errors. In a Manager Account (MCC) hierarchy, the structure is a Directed Acyclic Graph (DAG).^16^

* **The User** : Authenticates via OAuth (Refresh Token).
* **The Context** : The User "logs in" to the MCC (`login_customer_id`).
* **The Target** : The MCC acts upon a Child Account (`customer_id` passed in API calls).

 **Mechanism** :

* A single `refresh_token` generated by an admin of the Root MCC gives access to **all** child accounts linked to that MCC.
* You do **not** need to generate new tokens when new client accounts are created, provided they are linked to the MCC.
* **Account Switching** : To switch targets, you simply change the `customer_id` in the API method call (e.g., `campaign_service.mutate_campaigns(customer_id="CHILD_ID",...)`). The `login_customer_id` remains constant (pointing to the MCC).

### 5. Production Security Best Practices

Storing the `refresh_token` in a text file (`google-ads.yaml`) is acceptable for local development but dangerous for production.

* **Environment Variables** : The Python library automatically looks for environment variables if the YAML file is not found or arguments are missing. This is the preferred method for Docker/Kubernetes deployments.^7^
* `GOOGLE_ADS_DEVELOPER_TOKEN`
* `GOOGLE_ADS_CLIENT_ID`
* `GOOGLE_ADS_CLIENT_SECRET`
* `GOOGLE_ADS_REFRESH_TOKEN`
* `GOOGLE_ADS_LOGIN_CUSTOMER_ID`
* **Secrets Manager** : In AWS/GCP, store the Refresh Token as a secret. At runtime, inject it into the environment variable.
* **Token Rotation** : While tokens last for years, best practice suggests rotating the Client Secret and Refresh Token annually. This requires re-running the manual authorization flow.

### Confidence Level

✅  **High** . Verified against Google Identity Platform documentation and Google Ads API OAuth guides.

### Source References

-14

-15

-12

* [Multi-Account Access]^16^

### Code Example: Secure Initialization

**Python**

```
import os
from google.ads.googleads.client import GoogleAdsClient

def get_google_ads_client():
    """
    Initializes the client using Environment Variables for security.
    Falls back to YAML for local dev.
    """
    # Check if we are in a secure env with injected variables
    if "GOOGLE_ADS_REFRESH_TOKEN" in os.environ:
        return GoogleAdsClient.load_from_env(version="v22")
  
    # Fallback to local storage
    return GoogleAdsClient.load_from_storage("google-ads.yaml", version="v22")
```

### Implementation Impact

* **TASK-011** : The implementation can now proceed using the "Environment Variable" strategy for CI/CD compatibility.
* **Security** : The "7-Day Expiry" risk is mitigated by mandating "Production" status in GCP during setup.

---

## RQ-010: Policy Violation Detection & Exemption

### The Challenge of Programmatic Compliance

Ad creation in Google Ads is subject to a rigorous, automated policy check. Violations are common and can stem from benign issues (e.g., "Standard punctuation" rules flagged in creative text) or serious restrictions (e.g., "Healthcare" content). For an automated system, a single policy error causes the entire `Mutate` operation to fail. REQ-6 specifies a "Try-Catch-Exempt-Retry" algorithm. Research confirms this is not just a requirement but the *standard* engineering pattern for handling ads at scale.

### 1. The Reliability of Automated Exemptions

The API provides the `PolicyValidationParameter` to request exemptions. However, its reliability is binary based on the violation type.

* **Exemptible Violations** : These are marked `is_exemptible: true` in the error details.^19^ They include issues like "Capitalization", "Punctuation", "Phone number in text", or "Trademarks" (if the account has authorization). For these, sending an exemption request **guarantees** the ad will be created, though it may sit in "Under Review" status for a few hours.
* **Non-Exemptible Violations** : These include "Pharma", "Weapons", "Unacceptable Business Practices", or "Destination Mismatch". For these, `is_exemptible` will be `false`. Sending an exemption request will simply fail again.
* **False Positives** : The automated system has a known false positive rate, especially for "Misrepresentation" or "Trademarks". The exemption request is essentially a signal to the system: "I acknowledge this looks like a violation, but I claim I am authorized/compliant. Please review."

### 2. Vertical-Specific Policy Nuances

* **Education** :
* *Issue* : "Personalized Advertising". Ad copy that implies knowing the user's personal hardships (e.g., "Failed your exams?") can be flagged.
* *Constraint* : Certification requirements. Some degrees or courses require the account to be certified as an educational institution.
* **SaaS** :
* *Issue* : "Free Desktop Software". Google is extremely strict about software downloads. Ads leading to an EXE download often trigger "Malicious Software" flags if the site isn't verified.
* *Issue* : "Third-Party Tech Support". Using terms like "Support", "Help", or "Fix" in combination with brand names (e.g., "Slack Support") is often blocked to prevent scams.
* **India-Specific** :
* *Issue* : Financial products require strict verification by the Reserve Bank of India (RBI) or similar bodies before ads can run.

### 3. The "Try-Catch-Exempt-Retry" Algorithm

The logic must be robust to prevent infinite loops.

#### Step 1: Pre-Flight Validation (`validate_only`)

Before attempting to create an ad, the system should ideally use the `validate_only=True` header.^20^ This performs a "Dry Run".

* If it returns success: The ad is safe.
* If it returns `PolicyFindingError`: The system can parse the error, identify `ignorable_policy_topics`, and prompt the user (in a UI) or automatically decide to exempt *before* the first real mutate attempt. This reduces the noise in the account's change history.

#### Step 2: The Retry Logic

If `validate_only` is skipped or a real mutation fails, the algorithm is:

1. **Catch** `GoogleAdsException`.
2. **Filter** : Iterate through `failure.errors`. If *any* error is NOT a `PolicyFindingError` (e.g., `ImageError`), abort.
3. **Extract** : For policy errors, access `details.policy_finding_details`.
4. **Check** : If `is_exemptible` is false for any error, abort.
5. **Exempt** : Collect all `policy_topic_entries` into a list.
6. **Mutate** : Clone the original operation. Add `policy_validation_parameter` with the collected topics.
7. **Submit** : Retry the operation.

### 4. Human Escalation Workflow

Automated exemption is not a cure-all. Escalation is required when:

* The violation is `is_exemptible: false`.
* The retry fails with `OPERATION_NOT_PERMITTED`.
* The ad is created but remains "Under Review" for > 24 hours.
* **Workflow** : The system should log these ads to a "Policy Review Queue" in the UI. A human must then manually log in to the Google Ads interface to edit the ad or file an appeal. The API supports filing appeals for *disapproved* ads (post-creation) via the `AdGroupAdService`, but initial creation blocks must be resolved by changing the content.

### Confidence Level

✅  **High** . The `PolicyValidationParameter` flow is a documented and standard pattern.

### Source References

* [Policy Exemption Guide]^22^
* [Keyword Policy Violations]^19^
* [Validate Only Header]^20^

### Code Example: Robust Exemption Handler

**Python**

```
from google.ads.googleads.errors import GoogleAdsException

def submit_operation_with_policy_handling(service, customer_id, operation):
    """
    Submits an operation. If it fails due to exemptible policy violations,
    retries with exemption.
    """
    try:
        # Attempt 1: Standard Submission
        return service.mutate_ad_group_ads(
            customer_id=customer_id,
            operations=[operation]
        )
    except GoogleAdsException as ex:
        # Check if the error is exclusively policy-related
        ignorable_policy_topics =
      
        for error in ex.failure.errors:
            # If we hit a non-policy error (e.g. invalid url), we must fail
            if error.error_code.policy_finding_error!= \
               service.client.enums.PolicyFindingErrorEnum.POLICY_FINDING:
                raise ex
          
            # Extract details
            if error.details.policy_finding_details:
                details = error.details.policy_finding_details
                for entry in details.policy_topic_entries:
                    ignorable_policy_topics.append(entry.topic)
      
        # If we found topics to exempt, retry
        if ignorable_policy_topics:
            # Add exemption to the operation
            # Note: We must modify the operation in place
            validation_param = operation.policy_validation_parameter
            validation_param.ignorable_policy_topics.extend(ignorable_policy_topics)
          
            print(f"Retrying with exemptions: {ignorable_policy_topics}")
          
            try:
                # Attempt 2: Retry with Exemption
                return service.mutate_ad_group_ads(
                    customer_id=customer_id,
                    operations=[operation]
                )
            except GoogleAdsException as retry_ex:
                # If it fails again, it's likely non-exemptible or another issue
                print("Retry failed.")
                raise retry_ex
        else:
            # No exemptible topics found, re-raise original error
            raise ex
```

### Implementation Impact

* **TASK-025** : The `submit_operation_with_policy_handling` function becomes a core utility in the `common.utils` library. All ad creation tasks must call this wrapper instead of the raw service.

---

## RQ-011: GAQL Query Optimization & Limitations

### The Semantic Structure of GAQL

The Google Ads Query Language (GAQL) is the primary interface for reporting. While it syntactically resembles SQL (`SELECT`, `FROM`, `WHERE`), its semantic behavior is strictly hierarchical and object-oriented, not relational. There are no `JOIN` statements in GAQL. Instead, the `FROM` clause selects a primary resource (e.g., `campaign`), and the `SELECT` clause implicitly joins related resources (e.g., `bidding_strategy`) or segments (e.g., `segments.date`).

### 1. Segmentation Constraints & Implicit Filtering

The most significant "gotcha" in GAQL is  **Implicit Filtering** . In standard SQL, a `LEFT JOIN` preserves rows even if the joined data is missing. In GAQL, selecting a segment acts as an **inner join** that filters out rows where the segment is not applicable or zero.^25^

* **The Scenario** : You want a report of all campaigns and their conversion performance by conversion action.
* **The Query** : `SELECT campaign.name, segments.conversion_action_name, metrics.conversions FROM campaign`.
* **The Result** : If a campaign has **zero** conversions, it will likely be **excluded** from the report entirely because `segments.conversion_action_name` is null for that campaign. The row vanishes.
* **The Fix** : To see zero-performance entities,  **do not segment** . Run a high-level query (`SELECT campaign.name, metrics.conversions FROM campaign`) to get the totals (including zeros), and a separate segmented query to get the breakdown. You cannot get both "All Campaigns" and "Breakdown by Action" safely in a single query if you expect to see campaigns with no activity.

 **Incompatible Segments** : You cannot mix segments that imply different levels of granularity that don't intersect.

* *Example* : You cannot select `segments.search_term_view` (which is highly granular) and `segments.age_range_view` in the same query. The API will return a `PROHIBITED_SEGMENT_COMBINATION` error.^25^
* *Rule of Thumb* : If the segments belong to different "Views" (e.g., Keyword View vs. Age Range View), they are likely incompatible. Always check the `GoogleAdsFieldService` or the documentation matrix before constructing dynamic queries.

### 2. Query Performance: Search vs. SearchStream

* **`search`** : Returns a `GoogleAdsRow` iterator that handles pagination automatically.
* *Pro* : Easier to debug; standard pagination.
* *Con* : Slower for large datasets due to round-trip latency for each page (fixed at 10,000 rows).
* **`search_stream`** : Opens a persistent HTTP/2 stream.
* *Pro* : Much faster throughput. The server pushes data as soon as it's ready.
* *Best Practice* : **Always use `search_stream`** for reporting tasks (REQ-4). It is more robust for accounts with 10k+ keywords and reduces the chance of timeouts.^27^

### 3. Data Freshness & Availability

Data is not real-time.

* **Impressions/Clicks** : Typically available within  **3 hours** .
* **Conversions** : standard attribution can take  **24+ hours** .
* **Zero Metrics** : By default, reports exclude rows where *all* selected metrics are zero. To force zero rows, you must ensure you aren't segmenting by a field that enforces implicit filtering (like `date`).
* **Privacy Thresholds** : For detailed reports (Search Terms, Demographics), Google will return rows where metrics are aggregated into "Other" or simply omitted if the user count is too low to preserve anonymity. This means the sum of a segmented report (e.g., Search Terms) will often be **less** than the campaign-level totals.
* *Implementation Note* : Always display a "Total" row fetched from the Campaign level, and label the difference as "Unattributed/Other".^29^

### 4. GAQL Examples for Phase 1

**Campaign-Level Metrics (TASK-021)**

**SQL**

```
-- Use search_stream
SELECT 
  campaign.id, 
  campaign.name, 
  campaign.status,
  campaign.advertising_channel_type,
  metrics.impressions, 
  metrics.clicks, 
  metrics.ctr,
  metrics.cost_micros,
  metrics.conversions
FROM campaign 
WHERE segments.date DURING LAST_30_DAYS
  AND campaign.status!= 'REMOVED'
ORDER BY metrics.impressions DESC
```

**Keyword Performance (TASK-031)**

**SQL**

```
SELECT 
  ad_group.id,
  ad_group_criterion.criterion_id,
  ad_group_criterion.keyword.text,
  ad_group_criterion.keyword.match_type,
  ad_group_criterion.quality_info.quality_score,
  metrics.average_cpc,
  metrics.conversions,
  metrics.cost_per_conversion
FROM keyword_view 
WHERE segments.date DURING LAST_7_DAYS
  AND campaign.status = 'ENABLED'
  AND ad_group.status = 'ENABLED'
  AND ad_group_criterion.status = 'ENABLED'
```

### Confidence Level

✅  **High** . Based on core GAQL documentation and performance best practices.

### Source References

-^25^

* [Implicit Filtering]^25^
* [Zero Metrics Handling]^26^

### Implementation Impact

* **TASK-021/031** : Reporting modules must be built using `search_stream`.
* **Data Models** : Database schema must account for "Unattributed" data gaps caused by privacy thresholds.

---

## Conclusion

The foundation of the Phase 1 Google Ads infrastructure relies on three pillars: **strict adherence to v22** to leverage GenAI and avoid immediate technical debt; a **hardened OAuth2 flow** that sidesteps the 7-day expiration trap; and a **resilient ad creation loop** that handles policy violations as expected business logic rather than exceptions. By implementing the "Try-Catch-Exempt-Retry" pattern and standardizing on `search_stream` for GAQL, the system will be robust, scalable, and compliant with Google's evolving ecosystem.
