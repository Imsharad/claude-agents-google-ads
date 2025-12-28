---
**FILE SUMMARY**: Production Deployment - Infrastructure, Testing & Observability
**RESEARCH QUESTIONS**: RQ-024 to RQ-030
**KEY TOPICS**: Containerized VM deployment (Docker on EC2/GCE), financial firewall middleware, testing strategies (VCR.py, LLM-as-Judge), OpenTelemetry observability, always-on vs cron scheduling, CI/CD patterns, secrets management
**CRITICAL PATTERNS**: t3.medium VM specs, persistent volume mapping, hourly circuit breaker watchdog, deterministic API replay testing
**USE THIS FOR**: Deploying autonomous agents to production, implementing safety systems, monitoring agent behavior
---

# Production System Design & Operations Report: Autonomous Google Ads Agent Deployment

## 1. Executive Summary

The transition of the Claude Agent SDK-based Google Ads management system from a development prototype to a production-grade autonomous operator (Phase 3) represents a critical inflection point in the engineering lifecycle. Unlike stateless Large Language Model (LLM) applications or simple chatbots, this system operates as a stateful, long-running agent capable of executing financial transactions through the Google Ads API. The operational risks—ranging from runaway ad spend to non-deterministic behavior—require a fundamental shift in architectural strategy, moving beyond standard web application patterns into the realm of autonomous system engineering.

This report provides an exhaustive technical analysis and design specification for the Phase 3 deployment. It addresses the core requirements of running a 7+ day autonomous monitoring cycle (TASK-031) by recommending a robust, containerized runtime environment hosted on dedicated cloud virtual machines. This decision is driven by the unique state persistence needs of the Claude Agent SDK, which are incompatible with the ephemeral nature of serverless functions.^1^

The proposed architecture introduces a "Financial Firewall"—a middleware layer designed to enforce strict budget caps and velocity limits on agent actions, acting as a deterministic safeguard against probabilistic model failures. Furthermore, the report details a comprehensive testing strategy utilizing VCR.py for deterministic replay of API interactions and "LLM-as-a-Judge" patterns for semantic validation of creative outputs. Observability is addressed through an OpenTelemetry-based pipeline using Arize Phoenix to provide deep visibility into the agent's cognitive loops and tool execution paths.

By adopting the architectural standards, security protocols, and operational practices detailed herein, the organization can confidently deploy the autonomous Google Ads agent, ensuring high availability, financial safety, and auditable performance.^3^

---

## 2. RQ-024: Agent Runtime Environment

### 2.1 Architectural Analysis of Runtime Options

The selection of a runtime environment for the Claude Agent SDK is the foundational decision that dictates system reliability, state management, and scalability. Unlike traditional REST APIs which are stateless and request-scoped, the Claude Agent SDK operates as a persistent process that maintains an interactive shell, manages a local working directory, and holds conversational state in memory over extended periods.^1^ This "long-running process" paradigm necessitates a re-evaluation of modern cloud deployment targets.

#### 2.1.1 Deployment Options Evaluation

The following analysis rigorously compares four primary deployment targets—Local Machine, Serverless Functions, Containerized VMs, and Kubernetes—against the specific constraints of an autonomous agent managing financial assets.

| **Feature Category**     | **Local Machine**                                           | **Serverless (Lambda/Cloud Run)**                                                                                         | **Containerized (Docker on EC2/GCE)**                                                  | **Kubernetes (K8s)**                                                          |
| ------------------------------ | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| **State Persistence**    | **Native:**Uses local disk; state persists until manual deletion. | **Poor:**Ephemeral filesystem (except /tmp); requires complex external hydration/dehydration to Redis/S3 per turn.              | **Excellent:**Persistent Volumes (EBS/PD) allow seamless state recovery across restarts.     | **Excellent:**StatefulSets provide stable storage and network identities.           |
| **Process Lifecycle**    | **Indefinite:**Runs as long as the machine is on.                 | **Strictly Limited:**AWS Lambda caps at 15 mins; Cloud Run at 60 mins. High risk of termination during complex reasoning loops. | **Indefinite:**Can run 24/7/365. Essential for holding open gRPC channels to Google Ads API. | **Indefinite:**Designed for always-on services.                                     |
| **Operational Overhead** | **None:**Zero config.                                             | **Low:**No server management, but high complexity in managing state externally.                                                 | **Medium:**Requires OS patching, monitoring agents, and capacity planning.                   | **High:**Requires managing control plane, ingress, and complex YAML configurations. |
| **Scalability**          | **Vertical Only:**Limited by laptop hardware.                     | **Horizontal:**Massive auto-scaling, but inappropriate for stateful singleton agents.                                           | **Vertical & Horizontal:**Can resize VMs or add more VMs for multi-tenancy.                  | **Massive Horizontal:**Ideal for thousands of agents, overkill for <50.             |
| **Cost Efficiency**      | **CapEx:**Sunk cost.                                              | **Variable:**Pay-per-ms. Expensive for long-running idle processes waiting on API rate limits.                                  | **Predictable:**Fixed hourly rate. High utilization efficiency for always-on agents.         | **High Overhead:**Control plane costs (~$70/mo) plus compute.                       |
| **Security Isolation**   | **None:**Agent has full access to developer environment.          | **High:**MicroVM isolation (Firecracker).                                                                                       | **Configurable:**Docker namespaces/cgroups. Can be hardened with gVisor.                     | **High:**Namespace isolation, but shared kernel risks exist without sandboxing.     |

**Detailed Analysis of Rejected Options:**

* **Serverless (Rejected):** The "Serverless" paradigm is fundamentally mismatched with the Claude Agent SDK's architecture.^2^ The SDK relies on a persistent shell session to execute sequential commands. In a serverless environment (e.g., AWS Lambda), the execution environment is frozen or destroyed between invocations. To support a multi-turn conversation, the system would need to serialize the entire agent memory, working directory, and shell history to external storage (S3/Redis) after every single tool call, and deserialize it on the next trigger.^6^ This introduces massive latency, complexity, and points of failure. Furthermore, the 15-minute execution limit on Lambda poses a critical risk: if the agent enters a deep reasoning loop or waits for a slow Google Ads API response, the process could be SIGKILL-ed mid-transaction, potentially leaving the ad account in an inconsistent state.
* **Kubernetes (Rejected):** While Kubernetes offers robust orchestration, the overhead of managing a cluster for a Phase 3 deployment (single agent or small fleet) is unjustifiable.^7^ The complexity of configuring StatefulSets, PersistentVolumeClaims, and Ingress controllers introduces unnecessary friction. Kubernetes is a valid upgrade path for Phase 5 (Enterprise Scale) but is premature for the current operational maturity level.
* **Local Machine (Rejected):** Relying on a developer's laptop creates a single point of failure. Network interruptions, power saving modes, or hardware failures would violate the 7+ day continuous operation requirement.

#### 2.1.2 Recommended Architecture: Containerized VM

The recommended architecture is  **Docker containers hosted on Managed Virtual Machines (AWS EC2 or GCP Compute Engine)** . This approach aligns perfectly with Anthropic's guidance for production environments, which emphasizes container-based sandboxing for security and isolation while maintaining the persistence required for the agent's cognitive loop.^1^

**Architecture Specification:**

1. **Host Infrastructure:**
   * **Provider:** AWS EC2 (Instance Type: `t3.medium`) or GCP Compute Engine (`e2-standard-2`).
   * **OS:** Ubuntu 22.04 LTS (Minimal, Server Edition).
   * **Justification:** The Claude Agent SDK recommends 1GB RAM and 1 CPU.^1^ However, production reality requires overhead. The Google Ads API Python client utilizes gRPC, which can be memory-intensive when handling large schema objects. Additionally, the observability sidecar (OpenTelemetry collector) and the "Financial Firewall" middleware consume resources. A `t3.medium` (2 vCPU, 4GB RAM) provides sufficient headroom to prevent OOM (Out of Memory) kills during intensive campaign generation tasks.
2. **Containerization Strategy:**
   * **Base Image:** `python:3.11-slim-bookworm` (Balance of size and compatibility).
   * **Runtime User:** Non-root user (`agent_user`) to enforce least privilege.
   * **Volume Mapping:**
     * `/app/data`: Mapped to an EBS/Persistent Disk volume. Stores SQLite state DB and the Agent's working directory.
     * `/app/logs`: Mapped to a separate log volume for rotation.
     * `/tmp`: Ephemeral scratch space.
3. **Network Security:**
   * **Egress Only:** The agent does not need to accept inbound HTTP requests from the public internet. It polls for tasks or runs on a schedule.
   * **Firewall Rules:** Block all inbound ports except SSH (22) from the corporate VPN IP. Allow outbound traffic *only* to:
     * `api.anthropic.com` (443) – LLM Inference.
     * `googleads.googleapis.com` (443) – Ads API.
     * `oauth2.googleapis.com` (443) – Authentication.
     * `telemetry.arize.com` (443) – Observability.^1^

### 2.2 Execution Pattern: Scheduled vs. Always-On

A critical design decision is determining whether the agent process should run continuously (Always-On) or be triggered episodically (Cron).

#### 2.2.1 The Case for Always-On with Internal Scheduling

For the specific use case of daily campaign monitoring (TASK-031), an **Always-On Container with an Internal Scheduler** is technically superior to external Cron triggers for several distinct reasons.

1. Context & Connection Pooling:

The Google Ads API utilizes gRPC, which requires establishing a secure channel. Establishing this connection, performing the OAuth 2.0 handshake, and loading the initial client configuration can take several seconds.8 In a Cron-based model, this expensive initialization occurs every time the job runs. An always-on process maintains a "warm" connection pool, significantly reducing latency for the initial check. Furthermore, the Claude Agent SDK allows for session resumption. By keeping the process active, the agent can maintain a "memory" of the previous day's context (e.g., "Yesterday I lowered the bid on Keyword X, let me check if that worked") in local RAM or a fast local cache, rather than reloading it from a cold database.9

2. Failure Recovery & Watchdogs:

External Cron jobs are "fire and forget." If a Cron job fails silently (e.g., due to a syntax error in the crontab or a transient environmental issue), detection relies on external monitoring of log absence, which is often delayed. In contrast, an always-on process managed by a supervisor (like systemd or Docker's restart policy) enables immediate, automated recovery. If the agent crashes, the supervisor restarts it instantly, ensuring high availability.3

3. Real-time Responsiveness:

While the current requirement is daily monitoring, future phases may require reaction to real-time events (e.g., a budget exhaustion alert sent via webhook). An always-on architecture is forward-compatible with event-driven patterns, whereas a Cron-based architecture is strictly bound to time intervals.

#### 2.2.2 Implementation Strategy

The agent entry point should be a Python script that implements a robust scheduling loop, rather than a simple pass-through.

**Python**

```
# Conceptual Implementation of Always-On Internal Scheduler
import schedule
import time
from claude_agent_sdk import Agent
from monitoring import check_campaigns

def run_daily_job():
    print("Starting daily monitoring cycle...")
    try:
        agent = Agent.resume_session(session_id="persistent_daily_session")
        check_campaigns(agent)
    except Exception as e:
        log_error(e)
        # Trigger PagerDuty alert here

# Schedule the job
schedule.every().day.at("09:00").do(run_daily_job)

while True:
    schedule.run_pending()
    time.sleep(60) # Sleep to conserve CPU cycles
```

### 2.3 Resource Requirements Specification

Based on benchmarks of the Claude Agent SDK and the Google Ads API Python client, the following resource allocations are specified for the Phase 3 production environment.

| **Resource**     | **Requirement**                 | **Context & Justification**                                                                                                                                                                                                                                                                          |
| ---------------------- | ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Memory (RAM)** | **4 GB**                        | The SDK core is lightweight (~500MB), but the Google Ads API client loads large Protobuf schemas into memory. Concurrent processing of campaign data and the overhead of the Python Global Interpreter Lock (GIL) necessitate a buffer. 2GB is the absolute minimum; 4GB is recommended for stability..^1^ |
| **CPU**          | **2 vCPUs**                     | Agent operations are often I/O bound (waiting for LLM or API), but JSON parsing, schema validation, and OpenTelemetry instrumentation create significant CPU bursts. Single-core performance is important for Python.                                                                                      |
| **Disk Storage** | **20 GB**                       | **Partitioning:** ``- 10 GB: Container Image & OS overhead.``- 5 GB: Persistent State (SQLite DB, Agent Working Directory).^1^``- 5 GB: Logs (Managed with `logrotate`to prevent overflow).                                                                                   |
| **Network**      | **Low Bandwidth / Low Latency** | Throughput is negligible (<1 GB/day), but latency to `api.anthropic.com`is critical for agent responsiveness. Place the VM in a region with low latency to the Anthropic API endpoint (typically US East/West).                                                                                          |

### 2.4 Failure Recovery and Self-Healing

In a 7+ day autonomous run, transient failures are guaranteed. The system must be resilient to VM reboots, process crashes, and network blips.

**Implementation Guide:**

1. **Process Level (Docker):**
   * Use the Docker restart policy: `restart: unless-stopped`. This ensures that if the Python process crashes due to an unhandled exception, Docker immediately respawns it.
2. **VM Level (Systemd):**
   * Register the Docker service with `systemd` to ensure the container starts automatically if the EC2/GCE instance reboots due to maintenance or failure.
3. **Application Level (State Resumption):**
   * The agent must implement a "Checkpoint" pattern. Before every major action (e.g., calling the Google Ads API), the agent writes its `session_id` and current `task_state` to a JSON file on the persistent volume.
   * On startup, the application checks for the existence of `checkpoint.json`. If found, it calls `claude.Agent.resume(session_id)` to restore the conversation history and context, rather than starting from scratch.^1^

### 2.5 Multi-Tenancy Patterns

For an agency managing multiple clients, isolation is a non-negotiable security requirement.

* **Pattern:**  **Container-per-Client** .
* **Description:** Each client account is assigned a dedicated Docker container instance.
* **Justification:** This provides process-level isolation. If Agent A (managing Client A) enters a hallucination loop and consumes 100% CPU or crashes, Agent B (Client B) remains unaffected. It also simplifies data governance; Client A's data exists only in Container A's volume.^1^
* **Resource Implications:** While this increases memory overhead (multiple OS/Python runtimes), modern VMs can easily host 10-20 such lightweight containers. The cost of a slightly larger VM is negligible compared to the risk of cross-client data leakage or cascading failures.^10^

---

## 3. RQ-029: Security Architecture & Financial Governance

Security for an autonomous agent with the authority to spend money differs fundamentally from standard application security. The primary adversary is not just an external hacker, but the agent itself—specifically, the risk of non-deterministic behavior leading to unintended financial consequences.

### 3.1 The Financial Firewall (Circuit Breaker) Pattern

A critical vulnerability in autonomous agents is the "Logic Loop," where an agent gets stuck repeating an action (e.g., increasing a bid) indefinitely, draining budgets in minutes.^11^ To mitigate this, a **Financial Firewall** middleware must be implemented at the application layer, wrapping the Google Ads API client.

**Architecture of the Financial Firewall:**

1. **Velocity Limiter:**
   * **Mechanism:** Token Bucket Algorithm.
   * **Rule:** The agent is allocated a "Mutation Budget" of operations (e.g., 5 changes per hour). Every `create`, `update`, or `remove` operation consumes a token. If the bucket is empty, the API call is blocked, and the agent receives a `RATE_LIMIT_EXCEEDED` error from the middleware.
   * **Impact:** Prevents "Runaway" agents from making hundreds of changes in a short period.^11^
2. **Hard Budget Caps:**
   * **Mechanism:** Local Spend Accumulator.
   * **Rule:** The agent tracks a local variable `daily_spend_authorized`. Before calling `campaign.create` with a budget of $100, it checks: `current_spend + new_budget <= GLOBAL_HARD_CAP` (e.g., $500/day).
   * **Fail-Safe:** This check is independent of Google Ads' own daily budgets, acting as a second line of defense against "Fat Finger" hallucinations (e.g., setting a budget of $20,000 instead of $200).^11^
3. **Anomaly Detection Heuristics:**
   * **Mechanism:** Semantic Pattern Matching.
   * **Rule:** If the agent attempts to call the same tool with the exact same arguments more than 3 times in a single session, the Firewall triggers a "Loop Detected" event and terminates the session.^11^

### 3.2 Principles of Least Privilege & Credentials

The `google-ads.yaml` file contains the "keys to the kingdom" (Refresh Token, Developer Token). Its protection is P0.

**Secrets Management Implementation:**

1. **Storage:** Never store `google-ads.yaml` in the Git repository or Docker image. Use **AWS Secrets Manager** or  **GCP Secret Manager** .
2. **Runtime Injection:**
   * At container startup, an entrypoint script uses the cloud provider's Identity (IAM Role attached to the EC2 instance) to authenticate with Secrets Manager.
   * It retrieves the secret payload and writes it to a **RAM Disk** (`tmpfs`) at `/app/secrets/google-ads.yaml`.
   * **Security Benefit:** If the container is stopped or the host is powered down, the RAM disk is wiped. The credentials never persist on the disk storage.^12^

Tool-Level Permissions:

While Google Ads API tokens are broad, the Agent's Tool Definitions act as a functional permission boundary.

* **Observer Role:** If an agent is intended only for monitoring, it is initialized with a Tool Set containing *only* `get_campaigns`, `get_metrics`. It physically lacks the code to execute a mutation, enforcing read-only access regardless of the underlying API token's privileges.^4^

### 3.3 Audit Trails and Immutable Logging

Every autonomous decision must be traceable for compliance and debugging.

* **Structured Decision Logging:**
  * Before executing any tool, the agent must emit a structured log entry containing:
    * `SessionID`: UUID of the conversation.
    * `Trigger`: The specific observation that prompted the action (e.g., "CTR < 1%").
    * `Reasoning`: The Chain-of-Thought text generated by the LLM.
    * `Action`: The exact API payload.
* **Immutable Storage:** These logs are shipped immediately to **AWS CloudWatch Logs** or **S3 Object Lock** (WORM compliance). This ensures that even if an attacker compromises the container, they cannot erase the history of the agent's actions.^14^

---

## 4. RQ-027: Testing Strategy for Agent Systems

Testing non-deterministic agents requires a paradigm shift from traditional "Exact Match" assertions to "Property-Based" and "Semantic" testing. The testing strategy must validate that the agent behaves *safely* and  *rationally* , even if it doesn't behave exactly the same way twice.

### 4.1 Unit Testing: Mocking the Unpredictable

Unit tests must isolate the deterministic code (Tool logic, Data parsing) from the non-deterministic component (the LLM).

**Strategy:**

1. **Mocking the SDK:** Use `unittest.mock` to mock the `anthropic.Client`. We do not test *if* Claude calls the tool, but *what happens* when the tool is called.
2. **Tool Verification:** Create tests for each Tool function (e.g., `create_campaign`).
   * *Input:* Valid JSON payload matching the tool schema.
   * *Assertion:* Verify that the tool correctly transforms this JSON into a valid `GoogleAdsService` protobuf object.
   * *Error Handling:* Verify that the tool catches specific API errors (e.g., `RESOURCE_EXHAUSTED`) and returns a readable error message to the agent, rather than crashing.^16^

### 4.2 Integration Testing: VCR.py and Deterministic Replay

Testing against the real Google Ads API is slow, expensive, and flaky due to network issues. **VCR.py** is the industry standard solution for this challenge.^18^

**VCR.py Workflow:**

1. **Recording Phase:** Developers run the test suite once against a live  **Google Ads Test Account** .^20^ VCR.py intercepts all HTTP requests and responses (OAuth, REST, gRPC) and saves them to a YAML "cassette" file.
2. **Replay Phase:** In CI/CD pipelines, VCR.py is switched to replay mode. It intercepts outgoing requests and instantly returns the recorded responses from the cassette.
3. **Benefits:**
   * **Speed:** Tests run in milliseconds instead of seconds.
   * **Determinism:** The API response is always identical, eliminating flakiness.
   * **Cost:** Zero API calls are made during CI runs.
4. **Handling Non-Determinism:** Since the agent might generate slightly different ad copy (e.g., "Best Dentist" vs. "Top Dentist"), the exact API request might not match the recording. VCR.py must be configured with **custom matchers** that match on the *structure* of the request (Endpoint, Method) while ignoring specific body fields like `headline_part_1`.^21^

### 4.3 Semantic Testing: LLM-as-a-Judge

Traditional assertions cannot verify if a generated Persona is "high quality." For this, we use  **LLM-as-a-Judge** .

**Methodology:**

* **The Subject:** The Output of the Agent (e.g., a generated Ad Persona).
* **The Judge:** A separate, highly capable model (e.g., Claude 3.5 Sonnet) configured with a strict scoring rubric.
* **The Prompt:**
  > "You are an expert marketing auditor. Review the following Ad Persona for a Dentist client. Evaluate it on three criteria: 1. Relevance to Dentistry. 2. Professional Tone. 3. Completeness. Assign a score from 1-5 and provide a justification."
  >
* **The Assertion:** The test passes if `score >= 4`.^22^

### 4.4 End-to-End (E2E) Testing in Sandbox

E2E tests must validate the entire loop: `User Intent -> Agent Plan -> Tool Execution -> API Success`.

* **Environment:** Dedicated  **Google Ads Test Account** . This environment simulates the production API but does not serve ads or charge money.^20^
* **Data Cleanup:** E2E tests must implement a strict `teardown` fixture. After the test runs, the fixture queries the API for all entities created during the session (by tag or name prefix) and deletes/pauses them to maintain a clean state for the next run.^20^

---

## 5. RQ-028: Observability & Reliability Engineering

"If you can't measure it, you can't manage it." For autonomous financial agents, observability is not just about uptime; it's about understanding the "Cognitive Loop" and monitoring "Financial Velocity."

### 5.1 OpenTelemetry (OTel) Pipeline

The monitoring architecture leverages  **OpenTelemetry (OTel)** , the industry standard for distributed tracing. This allows us to trace a "thought" through the entire system.^23^

Trace Structure:

A single "Trace" corresponds to one Agent Session or Task. It contains hierarchical "Spans":

1. **Root Span:** "Daily Monitoring Job".
2. **Child Span:** "Agent Reasoning" (Captures the System Prompt and User Prompt).
3. **Child Span:** "LLM Inference" (Captures Token Usage, Latency, Model Name).
4. **Child Span:** "Tool Execution: search_campaigns" (Captures Tool Arguments).
5. **Child Span:** "External API: Google Ads" (Captures API Latency, HTTP Status Code).

**Instrumentation:** The Claude Agent SDK and the Google Ads Client are instrumented to emit these spans automatically to an OTel Collector running as a sidecar in the Docker container.^25^

### 5.2 Tooling Selection: Arize Phoenix

While generic APM tools (Datadog, CloudWatch) are useful for infrastructure, they lack the context for LLM agents. **Arize Phoenix** is selected as the primary observability platform.^26^

**Justification for Arize Phoenix:**

* **Open Source:** Can be self-hosted within the same VPC, addressing data privacy concerns (no sending sensitive ad data to a SaaS vendor).
* **LLM-Specific Features:** Native support for visualizing "Chains of Thought," embedding analysis (for RAG), and "Hallucination Detection" metrics.
* **Evaluation Integration:** It integrates tightly with the testing strategy, allowing offline evaluation of traces collected in production.^26^

### 5.3 Key Metrics Dashboard

The dashboard must provide a holistic view of Agent Health and Business Impact.

| **Metric Category** | **Specific Metric**       | **Definition**                                                                  | **Criticality** |
| ------------------------- | ------------------------------- | ------------------------------------------------------------------------------------- | --------------------- |
| **Reliability**     | **Hallucination Rate**    | % of Tool Calls resulting in `SchemaValidationError`or `InvalidArgument`.         | 🔴**High**      |
| **Reliability**     | **Loop Count**            | Number of times an agent repeats the same tool call with identical args in a session. | 🔴**High**      |
| **Operational**     | **API Quota Utilization** | Operations consumed / 15,000 daily limit.                                             | 🔴**High**      |
| **Financial**       | **Token Velocity**        | Tokens/minute. Spikes indicate a runaway loop.                                        | 🟡 Medium             |
| **Business**        | **Campaigns Optimized**   | Count of campaigns successfully mutated.                                              | 🟢 Low (Lagging)      |

### 5.4 Alerting Rules and Incident Response

* **P0 Severity (Wake up Operator):**
  * **Condition:** `API_Error_Rate > 50%` (Google Ads API is down or credentials revoked).
  * **Condition:** `Financial_Circuit_Breaker_Tripped` (Agent attempted to exceed spend limit).
  * **Channel:** PagerDuty / Urgent Slack Notification.
* **P1 Severity (Next Business Day):**
  * **Condition:** `Hallucination_Rate > 10%` (Indicates model degradation or prompt drift).
  * **Condition:** `Job_Duration > 30 mins` (Agent is stuck or slow).
  * **Channel:** Email / Jira Ticket.

---

## 6. RQ-026: Data Strategy & Persistence

To support the agent's long-term memory and the "Golden Ratio" optimization algorithms, the system requires a robust data persistence layer. Relying solely on the Google Ads API for historical data is inefficient due to rate limits.

### 6.1 Schema Design: Relational vs. NoSQL

A hybrid approach is recommended. **PostgreSQL** is the primary store for structured metadata, while **JSON/Blob Storage** is used for unstructured agent state.

Relational Schema (PostgreSQL):

Google Ads data is highly hierarchical and structured (Campaigns -> AdGroups -> Ads -> Keywords). A relational database guarantees data integrity.

**SQL**

```
-- Campaigns Table: Stores the "Source of Truth" configuration
CREATE TABLE campaigns (
    id SERIAL PRIMARY KEY,
    google_id BIGINT UNIQUE NOT NULL,
    account_id BIGINT NOT NULL,
    name VARCHAR(255),
    status VARCHAR(50), -- ENABLED, PAUSED
    budget_micros BIGINT,
    last_synced_at TIMESTAMP DEFAULT NOW()
);

-- Performance Metrics: Time-series data for optimization algorithms
CREATE TABLE daily_metrics (
    campaign_id INT REFERENCES campaigns(id),
    date DATE NOT NULL,
    impressions INT DEFAULT 0,
    clicks INT DEFAULT 0,
    cost_micros BIGINT DEFAULT 0,
    conversions INT DEFAULT 0,
    ctr DECIMAL(5,4), -- Computed metric
    PRIMARY KEY (campaign_id, date)
);
-- Note: Use TimescaleDB extension for efficient time-series querying if volume grows.[28]
```

**Unstructured Storage (Agent Memory):**

* **Session State:** The Claude Agent SDK's session object (containing the conversation history) is serialized to JSON and stored in the persistent volume or S3. This allows the agent to "Resume" a conversation after a restart.^1^
* **Decision Logs:** The "Reasoning" logs (Why did I raise the bid?) are stored as JSONB in Postgres or as flat files in S3 for auditing.

### 6.2 Data Retention and BigQuery Export

For Phase 3, the local PostgreSQL instance is sufficient. However, to support Phase 4 (Advanced Analytics), the data architecture must be "Analytics Ready."

* **Strategy:** Implement the **Google Ads API Transfer Service** for BigQuery if available for the client. Alternatively, a nightly Python ETL job should export the `daily_metrics` table to CSV and upload it to a BigQuery dataset. This decoupling ensures that heavy analytical queries (e.g., "Show me year-over-year trends") do not degrade the performance of the operational database used by the agent.^29^

---

## 7. RQ-030: Economic Analysis & FinOps

Validating the business case requires a rigorous analysis of the Total Cost of Ownership (TCO), factoring in both infrastructure and variable LLM costs.

### 7.1 Component Pricing Analysis

**1. Claude 3.5 Sonnet Costs:**

* **Pricing:** $3.00 (Input) / $15.00 (Output) per 1 Million tokens.^30^
* **Agent Overhead:** Agents are verbose. The "ReAct" loop involves sending the entire conversation history plus the Tool Result (often a large JSON from Google Ads) back to the model for every step.
* **Estimated Usage:**
  * *Daily Check (No Action):* ~2,000 tokens (Input) + 200 (Output) = ~$0.009/run.
  * *Campaign Creation (Heavy):* ~15,000 tokens (Input) + 2,000 (Output).
    * Calculation: `(15,000/1M * $3) + (2,000/1M * $15)` = `$0.045 + $0.030` =  **~$0.075 per campaign** .

**2. Google Ads API Costs:**

* **Monetary:** Free.
* **Quota Opportunity Cost:** The "Basic Access" token limits the developer to  **15,000 operations per day** .^31^
  * *Impact:* An "Operation" is granular (e.g., adding 1 keyword = 1 op). A complex campaign setup could consume 500 ops.
  * *Constraint:* A single agent instance can theoretically manage ~30 full campaign setups per day before hitting the global rate limit. This is the primary scaling bottleneck, not cost.

**3. Infrastructure Costs:**

* **Compute (e2-standard-2):** ~$50/month.
* **Storage:** ~$2/month.
* **Observability (Self-hosted):** $0 (included in compute).

### 7.2 Total Cost of Ownership (TCO) & Profitability

**Scenario:** A managed service monitoring  **50 Client Accounts** .

* **Daily Usage:** 50 accounts * 30 days = 1,500 runs/month.
* **LLM Cost:**
  * Monitoring (90% of runs): 1,350 runs * $0.009 = $12.15.
  * Optimization/Creation (10% of runs): 150 runs * $0.075 = $11.25.
  * **Total LLM:** ~$23.40 / month.
* **Infrastructure Cost:** ~$52.00 / month.
* **Total OpEx:**  **~$75.40 / month** .

ROI Analysis:

If the agency charges a standard management fee (e.g., $500/month per client or a % of spend):

* **Revenue:** 50 clients * $500 = $25,000/month.
* **Cost:** $75.40/month.
* **Margin:** >99%.
* **Conclusion:** The automation is extremely profitable. The cost of the agent is negligible compared to the human labor it replaces.

---

## 8. RQ-025: Advanced Orchestration (Phase 4 Future Proofing)

As the system scales, a single agent managing complex strategy and execution becomes inefficient. The **Planner-Worker-Evaluator** pattern is recommended for Phase 4.^32^

### 8.1 Pattern Implementation

1. **The Planner (Claude 3.5 Sonnet):**
   * **Role:** High-level strategist. Analyzes the user request ("Reduce CPA by 20%") and breaks it down into a dependency graph of tasks.
   * **Output:** A JSON plan passed to the Worker.
2. **The Worker (Claude Haiku):**
   * **Role:** Execution. Receives a specific task ("Pause keywords with CTR < 1%").
   * **Justification:** Claude Haiku is significantly cheaper ($0.25/1M input) and faster.^34^ Using it for the repetitive, low-level tool execution reduces the TCO for high-volume tasks.
3. **The Evaluator (Claude 3.5 Sonnet):**
   * **Role:** Quality Assurance. Reviews the Worker's proposed changes *before* they are committed to the API.
   * **Logic:** Acts as a sophisticated "linter" for business logic, catching hallucinations that the simpler Worker might miss.

### 8.2 Orchestration Mechanics

The Claude Agent SDK supports "Sub-agents".^35^

* **Implementation:** The Planner instantiates a `ClaudeAgent` object (the Worker) with a restricted toolset. It invokes the Worker with a prompt, waits for the result, and then passes the result to the Evaluator.
* **State Sharing:** Context is passed explicitly via the `messages` history. The Planner maintains the global state, while the Worker operates in an ephemeral context, ensuring cleaner reasoning boundaries.

---

## 9. Implementation Roadmap

To achieve the Phase 3 exit criteria, the following implementation sequence is recommended:

1. **Week 1: Foundation.** Provision the AWS/GCP VM and configure the Docker environment with the "Financial Firewall" middleware.
2. **Week 2: Testing Pipeline.** Implement the VCR.py recording workflow and the LLM-as-a-Judge semantic tests. Achieve 80% coverage on the Tool Logic.
3. **Week 3: Observability.** Deploy Arize Phoenix and instrument the agent traces. Define P0 alerts in PagerDuty.
4. **Week 4: Dry Run.** Run the agent in "Shadow Mode" (Read-Only) against production accounts for 7 days. Validate logs and decisions without executing mutations.
5. **Go-Live.** Enable mutation tools with a $50/day hard cap and monitor closely.

This structured approach minimizes risk while establishing a scalable foundation for the autonomous agency.
