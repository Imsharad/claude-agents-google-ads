---
**FILE SUMMARY**: Claude Agent SDK - Core Architecture & Integration Patterns
**RESEARCH QUESTIONS**: RQ-001 to RQ-007
**KEY TOPICS**: Agent loop mechanics, permission systems (3-tier safety), MCP server architecture (in-process vs subprocess), state management (daily session pattern), OAuth integration, custom callbacks, tool execution safeguards
**CRITICAL PATTERNS**: Permission callback implementation, session resumption, financial mutation safety, context window management
**USE THIS FOR**: Understanding how to build autonomous agents with Claude SDK for Google Ads automation
---

# Comprehensive Architectural Analysis of the Claude Agent SDK for Autonomous Google Ads Management

## 1. Executive Summary and Strategic Architectural Alignment

The evolution of automated systems from scripted automation to autonomous agents represents a fundamental shift in software engineering paradigms. In the context of digital advertising—specifically Google Ads management—this shift promises to move operations from rigid, rule-based bid adjustments to dynamic, context-aware campaign orchestration. The Claude Agent SDK emerges as the critical runtime environment for this transition, offering a scaffolding that transforms the stochastic capabilities of Large Language Models (LLMs) into deterministic, executable workflows. This report provides an exhaustive technical analysis of the SDK's capabilities, limitations, and integration patterns, specifically tailored to the high-stakes requirements of financial mutation within advertising accounts.

The research indicates that the Claude Agent SDK is not merely a client wrapper for the Anthropic API but a stateful runtime that manages an "agent loop"—a recursive cycle of observation, reasoning, and action. While this runtime provides powerful abstractions for tool use and context management, it introduces significant complexity regarding state persistence, permission granularity, and operational observability. The analysis confirms that a "Phase 2" implementation of a Google Ads Agent requires a hybrid architectural approach: leveraging the SDK’s in-process capabilities for shared authentication state while externalizing persistence layers to mitigate the SDK's ephemeral session handling. Furthermore, the Model Context Protocol (MCP) serves as the indispensable bridge between the agent's cognitive core and the rigid API structures of Google Ads, necessitating a custom server implementation to handle mutation logic safely.

Critical findings highlight the existence of a "permissions gap" in the default configuration modes, which necessitates the implementation of custom callback logic (`can_use_tool`) to achieve the requisite safety for budget-impacting operations. Additionally, the "invisible history" phenomenon—where resumed sessions maintain cognitive context but lack programmatic message history—mandates a sidecar database architecture for any user-facing interface. This report details the theoretical underpinnings and practical implementation strategies for these components, ensuring a robust foundation for the autonomous agent.

## 2. The Agent Runtime Environment: Core Mechanics and Lifecycle

To engineer a resilient Google Ads agent, one must first understand the substrate upon which it operates. The Claude Agent SDK provides a specialized runtime distinct from standard stateless LLM interactions. This section dissects the agent loop, client instantiation patterns, and the underlying transport mechanisms that govern execution.

### 2.1 The Recursive Agent Loop

At the heart of the SDK lies the agent loop, a recursive control structure that manages the interaction between the model's reasoning capabilities and the external world. Unlike a standard request-response cycle, the agent loop is autonomous and stateful. When a directive is issued—for example, "Optimize the CPC for the Summer Sale campaign"—the runtime initiates a sequence of events that persists until the objective is met or a termination condition is triggered.

The loop follows a distinct **Gather-Reason-Act-Verify** cycle.^1^ Initially, the runtime ingests the user's prompt and appends it to the current context window. The model then evaluates the available tool definitions—standard tools provided by the SDK and custom tools injected via MCP—to determine if external data is required. In a Google Ads context, this often manifests as a need to inspect current performance metrics before making a decision. The model emits a tool call (e.g., `GetCampaignMetrics`), which the runtime intercepts.

Crucially, the runtime does not blindly execute this request. It passes the request through a permission layer—a critical checkpoint for financial safety—before dispatching it to the appropriate MCP server. The result of the operation is captured as an "observation" and fed back into the context window. This recursive process allows the agent to perform multi-step reasoning, such as querying data, analyzing a trend, formulating a hypothesis, adjusting a bid, and verifying the change, all within a single high-level user interaction.^1^

### 2.2 Client Instantiation Patterns

The SDK offers two primary interfaces for interacting with this runtime: the stateless `query()` function and the stateful `ClaudeSDKClient` class. Understanding the distinction is vital for architectural decisions regarding session management and resource utilization.

#### 2.2.1 Stateless Execution: The `query()` Interface

The `query()` function represents a functional approach to agent orchestration. It is designed for ephemeral, atomic tasks where maintaining history across interactions is unnecessary or undesirable. When invoked, `query()` spins up a new session, executes the prompt until completion (or until `max_turns` is reached), and then tears down the environment.^2^

For a Google Ads agent, this pattern is generally insufficient for core management tasks. Campaign optimization is inherently conversational and iterative; the agent must remember previous insights (e.g., "We paused this keyword yesterday because of low CTR") to make informed decisions today. Using `query()` would result in a fragmented memory model where the agent lacks historical context, leading to repetitive or contradictory actions. However, `query()` finds its utility in isolated utility sub-routines, such as a quick sanity check on a policy compliance rule where the broader campaign history is irrelevant.^2^

#### 2.2.2 Stateful Persistence: The `ClaudeSDKClient`

The `ClaudeSDKClient` is the foundational object for the autonomous agent. It establishes a persistent connection to the agent runtime, maintaining the session state, conversation history, and tool configurations across multiple user interactions.^2^ This client manages the lifecycle of the connection, supporting explicit `connect()` and `disconnect()` operations, as well as the ability to interrupt running execution loops—a safety feature discussed later in this report.

The `ClaudeSDKClient` operates using an asynchronous context manager pattern, ensuring that resources are properly initialized and released. This is particularly important when integrating with MCP servers that may hold open connections to the Google Ads API or local database handles. The architecture for the Google Ads agent must wrap this client in a robust service layer that manages re-connection logic and error boundaries, ensuring the agent remains responsive over long-duration monitoring tasks.^4^

### 2.3 Transport Protocols and The Bundled CLI

A nuanced but critical detail of the SDK's architecture is its reliance on a transport layer. The Python SDK, in many configurations, acts as a controller for a "bundled CLI" binary or communicates via a control protocol. This architecture decouples the Python application logic from the core agentic reasoning engine, potentially allowing for cross-language compatibility but introducing a dependency on the underlying runtime environment.^4^

When the `ClaudeSDKClient` is initialized, it negotiates a transport connection. In the default subprocess mode, it launches the Claude Code CLI as a child process and communicates via standard input/output (stdio). This has implications for deployment: the container environment must have the necessary Node.js runtime (required for the CLI) and the CLI binary installed.^6^ For the Google Ads agent, which likely runs in a containerized cloud environment (e.g., Kubernetes or Cloud Run), the build pipeline must ensure these dependencies are present to avoid runtime initialization failures.

## 3. Security and Permission Architectures (RQ-001)

In the domain of autonomous financial agents, security is not a non-functional requirement; it is the primary constraint. An agent with the capability to modify bids, pause campaigns, or create ads possesses the ability to inflict significant financial damage if left unchecked. The Claude Agent SDK implements a multi-layered permission system designed to mitigate these risks. This section analyzes the permission modes and details the implementation of a "Human-in-the-Loop" workflow for mutation operations.

### 3.1 Global Permission Modes

The SDK exposes a `PermissionMode` configuration option that sets the baseline behavioral policy for tool execution. These modes represent a trade-off spectrum between autonomy and safety.^8^

| **Permission Mode**       | **Description and Operational Behavior**                                                                                                                                                                                                                                                                                                       | **Suitability for Google Ads Agent**                                                                                                        |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`default`**           | **Standard Safety:**This is the baseline mode. It blocks execution of "dangerous" tools (typically those involving file writes, shell execution, or designated API mutations) and triggers a user confirmation request. Read-only operations (like `Grep`or `Read`) may be permitted automatically depending on the specific tool configuration. | **Moderate:**Useful for development but may be too chatty for a production monitoring system if it prompts for benign read operations.            |
| **`acceptEdits`**       | **Development Acceleration:**Designed for coding assistants, this mode automatically approves file modification tools (`Edit`,`Write`). It assumes the user is monitoring the output in an IDE and can revert changes via version control.                                                                                                       | **Low:**Unsuitable for a production financial agent. Automatic approval of mutations without specific logic creates an unacceptable risk profile. |
| **`bypassPermissions`** | **Full Autonomy:**This mode disables the safety interlocks entirely. The agent executes any tool it deems necessary immediately. Utilizing this mode requires setting the `allow_dangerously_skip_permissions: true`flag, emphasizing its risk.                                                                                                    | **Critical Risk:**Only acceptable in a strictly sandboxed environment or for read-only sub-agents. Never for the core mutation loop.              |
| **`plan`**              | **Simulation:**An experimental mode where the agent generates a plan of action but is strictly forbidden from executing side-effect-inducing tools.                                                                                                                                                                                                  | **High (for Pre-computation):**Excellent for a "Dry Run" mode where the agent proposes changes for human review without applying them.            |
| **`dontAsk`**           | **Headless Safety:**Automatically denies any permission request that would otherwise trigger a prompt. This prevents the agent from hanging indefinitely in headless environments waiting for user input that will never come.                                                                                                                       | **High (for Background Tasks):**Essential for autonomous monitoring loops to ensure the system fails safe rather than stalling.                   |

For the Google Ads agent, the requirement is nuanced: we need high autonomy for information gathering (read operations) but strict oversight for state changes (mutations). None of the global modes perfectly satisfy this "Read = Auto, Write = Ask" requirement out of the box. `default` is too restrictive, and `bypassPermissions` is too dangerous.

### 3.2 Granular Control: The `can_use_tool` Callback

To bridge the gap between global policies and specific business requirements, the SDK provides the `can_use_tool` callback mechanism. This allows developers to inject custom logic into the permission decision loop, inspecting the tool name and its arguments before execution is authorized.^2^

#### 3.2.1 Mechanism of Interception

When the model constructs a tool call, the runtime halts execution and invokes the registered `can_use_tool` function. This function receives a payload describing the intent—specifically the tool name and the input dictionary. The return value of this function dictates the runtime's next step: it can allow the execution, deny it with a reason, or presumably trigger a user interaction flow.^11^

This callback is the architectural lynchpin for the Google Ads agent. It enables the implementation of policy-based access control. For instance, an operation to `GetCampaignCost` can be whitelisted based on its prefix or name, while `UpdateCampaignBudget` can trigger a secondary verification step or be outright denied if it exceeds a certain threshold defined in the agent's configuration.

#### 3.2.2 The Signature Trap

Research into the SDK's implementation details reveals a critical pitfall: the function signature for `can_use_tool` has been a source of significant confusion within the developer community, with discrepancies between documentation and actual library behavior.^11^ The correct implementation requires returning a specific `PermissionResult` object (either `PermissionResultAllow` or `PermissionResultDeny`) rather than a simple boolean. Returning a boolean or an incorrect object structure can cause the agent loop to crash or enter an infinite retry loop, interpreting the invalid return value as a system error rather than a policy decision.

Implementation Strategy:

The callback must be robust. It should import PermissionResultAllow and PermissionResultDeny from claude_agent_sdk. The logic should default to "Deny" (fail-safe) and explicitly whitelist known safe tools.

**Python**

```
# Conceptual Implementation of Selective Permissions
from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

async def policy_enforcement_callback(tool_name: str, tool_input: dict):
    # Safe List: Read-only operations
    if tool_name.startswith("mcp__google_ads__read") or tool_name in:
        return PermissionResultAllow()

    # Mutation List: Requires Check
    if tool_name.startswith("mcp__google_ads__mutate"):
        # Business Logic: Auto-approve small bid changes
        if tool_name == "update_bid" and tool_input.get("amount", 0) < 5.00:
             return PermissionResultAllow()
      
        # Deny large changes, requiring human intervention via a different workflow
        return PermissionResultDeny(
            message="Budget changes over $5.00 require human approval via the dashboard."
        )

    # Default Deny
    return PermissionResultDeny(message="Tool execution not authorized by policy.")
```

### 3.3 Managing the "Ask" Workflow in Headless Environments

The PRD specifies a `permission_mode='ask'` behavior. In a CLI environment, the SDK handles this by pausing and printing a prompt to the terminal. However, the Google Ads agent will likely run as a background service (headless). In this context, a CLI prompt is useless; it halts the thread waiting for input that can never arrive via `stdin`.

To implement "Ask" in a headless environment, the architecture must effectively "pause and persist." When the `can_use_tool` callback encounters a sensitive action that requires approval (and isn't auto-approved by logic), it should:

1. **Deny the immediate execution** via `PermissionResultDeny`.
2. **Trigger a Notification:** Send a structured event to the application database or notification service (e.g., "Approval Request: Campaign Update").
3. **Instruct the Agent:** The denial message returned to the agent should be instructional: "I have paused this mutation request. It has been queued for human approval. Please proceed to other tasks or wait."
4. **Resumption:** Once the human approves the action via a web interface, the system must reinvoke the agent (potentially in a new session or by resuming the existing one) with the instruction to retry the tool call.

This decouples the synchronous agent loop from the asynchronous human decision process, preventing timeout failures.

### 3.4 Handling Denials and Timeouts

When a permission is denied, the agent receives this as an observation. It effectively "sees" that its attempt failed. The agent's cognitive capabilities allow it to reason about this. It might try a different tool or simply report the blockage to the user.^13^

If the system were to use the built-in synchronous `ask` mode in a CLI, a timeout is enforced. The default timeout (often configurable via `timeout_ms` in `ClaudeAgentOptions`) prevents the agent from hanging indefinitely.^14^ If the timeout expires, it is treated as a denial. For the Google Ads agent, relying on synchronous timeouts is fragile; the asynchronous "Deny and Queue" pattern described above is robust against network latency and human delay.

## 4. Model Context Protocol (MCP) Integration (RQ-002)

The Claude Agent SDK uses the Model Context Protocol (MCP) as the standardized interface for all external tool interactions. This protocol abstracts the complexity of API connections, creating a uniform "socket" for the agent to plug into data sources. For the Google Ads integration, distinct architectural decisions regarding server topology and tool registration are required.

### 4.1 MCP Server Topology: Subprocess vs. In-Process

The MCP specification supports multiple transport layers, leading to two primary deployment topologies within the Claude Agent SDK: the Subprocess (stdio) model and the In-Process (SDK-based) model.

#### 4.1.1 Subprocess Topology (stdio)

In this configuration, the MCP server runs as a completely independent process, launched and managed by the SDK via standard input/output pipes.^15^ The SDK spawns the server (e.g., `python mcp_server.py`) and communicates via JSON-RPC messages over stdout/stdin.

* **Advantages:** This offers strong process isolation. If the MCP server crashes due to a segfault or unhandled exception, it does not necessarily bring down the main agent process. It also allows for polyglot architectures; the agent could be Python while the MCP server is written in Node.js or Go.
* **Disadvantages:** It introduces Inter-Process Communication (IPC) overhead, which involves serialization and deserialization of every message. More critically for this use case, it makes sharing state—specifically complex authentication objects like an authorized `GoogleAdsClient` instance—extremely difficult. Credentials must be passed via environment variables, and the server must re-authenticate independently.

#### 4.1.2 In-Process Topology (SDK-based)

The SDK allows developers to define MCP servers programmatically within the same memory space as the agent application using the `create_sdk_mcp_server` factory.^17^

* **Advantages:** This eliminates IPC overhead, reducing latency. Most importantly, it allows for shared state. The main application can handle the OAuth handshake, refresh tokens, and initialize the `GoogleAdsClient` object, then pass this live object directly to the tool functions. This simplifies the architecture significantly and centralizes secret management.
* **Recommendation:** For the Google Ads Agent, the **In-Process Topology** is the superior choice. It aligns with the need for a tightly integrated, high-performance monitoring loop and simplifies the complexity of managing OAuth contexts across boundaries.

### 4.2 Tool Registration and The Decorator Pattern

Tools are the functional units of the MCP server. In the Python SDK, tools are registered using a decorator pattern that abstracts the JSON schema generation required by the LLM. The `@tool` decorator inspects the Python function's type hints and docstrings to automatically generate the tool definition (name, description, argument schema).^18^

**Registration Workflow:**

1. **Define:** Create a Python function with precise type hints (`str`, `int`, etc.) and a descriptive docstring. The docstring is the "prompt" for the tool; it tells the model *when* and *why* to use it.
2. **Decorate:** Apply `@tool` or pass the function list to `create_sdk_mcp_server`.
3. **Configure:** Add the server instance to the `mcp_servers` dictionary in `ClaudeAgentOptions`.
4. **Allow:** Explicitly whitelist the tool in the `allowed_tools` list using the namespaced format `mcp__{server_name}__{tool_name}`.

Concurrency Considerations:

In the In-Process model, tools are executed as asynchronous (async def) functions within the agent's event loop. This allows the agent to handle multiple operations concurrently without blocking. However, the Google Ads API has rate limits. The tool implementation must handle 429 Too Many Requests errors. Since multiple agent sessions might share the same underlying MCP server instance (in a multi-tenant server architecture), the rate limiter should be global or synchronized.17

### 4.3 Google Ads Integration Pattern

A major finding is the existence of an official, albeit experimental, Google Ads MCP server (`googleads/google-ads-mcp`).^19^ However, its current capability is strictly  **read-only** , focusing on GAQL (Google Ads Query Language) execution. It does not support mutations (writing changes).

This necessitates a **Hybrid Integration Pattern** for Phase 2:

1. **Read Layer:** Utilize the logic from the official `google-ads-mcp` repository to handle the complexity of GAQL parsing and reporting. This can be integrated as a library or a parallel MCP server.
2. **Mutation Layer:** Develop a custom, in-process MCP server specifically for the required mutation tools (`PauseCampaign`, `UpdateBid`, `CreateAd`).
3. **Unified Interface:** Present both sets of tools to the agent. The agent does not distinguish between sources; it simply sees a suite of capabilities like `google_ads_search` and `google_ads_update_campaign`.

### 4.4 Failure Handling and Resilience

The MCP architecture must assume failure. If the Google Ads API returns a 500 error or a network timeout occurs:

* **Error Propagation:** The tool should catch the exception and return a structured error string to the model (e.g., "Error: API Connection Timeout"). It should *not* raise an unhandled exception that crashes the agent process.
* **Agent Recovery:** Upon receiving the error string, the agent's reasoning loop (if prompted correctly) can decide to retry the operation or degrade gracefully (e.g., "I could not fetch the latest data, so I will skip optimization for this cycle").
* **Auto-Restart:** In the subprocess model, the SDK handles some lifecycle management, but in the in-process model, the application is responsible. Standard Python `try...except` blocks around the agent loop are essential.

## 5. State Management and Long-Running Resilience (RQ-003)

The PRD requires the agent to operate autonomously for 7+ days. This duration exceeds the lifespan of typical ephemeral processes, making state persistence and session recovery critical architectural pillars. The research uncovers a significant dichotomy between "LLM Context Persistence" and "Application History Persistence."

### 5.1 The Persistence Mechanism: Session IDs

The Claude Agent SDK utilizes a session-based architecture. When a `ClaudeSDKClient` initializes a conversation, it generates or receives a `session_id`. This ID is the key to the agent's short-term memory.^20^

* **Mechanism:** The session state (the sliding window of context tokens) is maintained by the SDK runtime.
* **Storage:** In local deployments, this state is often serialized to disk (typically `~/.claude/projects/...` in JSONL format). In a cloud deployment, relying on local ephemeral disk storage is precarious.
* **Resumption:** To resume a conversation after a process restart, the application initializes `ClaudeAgentOptions` with the `resume="session-uuid"` parameter. This instructs the runtime to reload the context associated with that ID, effectively putting the agent "back in the room" with the memory of what happened previously.^2^

### 5.2 The "Invisible History" Problem

A critical limitation identified in the SDK's current implementation is the lack of programmatic access to historical messages upon resumption. When `resume="id"` is used, the LLM correctly recalls the context, but the `ClaudeSDKClient` does **not** re-emit the past message events to the application.^21^

Implications for Google Ads Agent:

If the agent runs for 3 days and then restarts, the dashboard viewing the agent's logs would appear blank upon reconnection, even though the agent internally "knows" what it did. The user loses visibility into the narrative history of actions.

### 5.3 The Sidecar Persistence Pattern

To solve the "Invisible History" problem and ensure robust auditing, a **Sidecar Persistence Pattern** is recommended. This involves decoupling the UI/Log history from the SDK's internal state.

1. **Event Interception:** The application wrapper around `ClaudeSDKClient` must listen to every message event yielded by the generator (`UserMessage`, `AssistantMessage`, `ToolUse`, `ToolResult`).
2. **External Storage:** As events occur, they are immediately written to a durable external database (e.g., PostgreSQL or DynamoDB), independent of the SDK's internal JSONL files.
3. **Reconstruction:** When the dashboard loads or the agent restarts, the application fetches the history from the database to populate the UI. The SDK is initialized with `resume` solely to restore the *cognitive* context for the LLM.

### 5.4 Long-Running Agent Patterns

For a 7-day autonomous mission, continuously keeping a single session open is risky due to "Context Drift" (the model getting confused by too much history) and token cost accumulation.

Recommended Pattern: The Daily Session Strategy

Instead of one monolithic 7-day session, the agent should operate in discrete units, likely aligned with the daily reporting cycle of Google Ads.

* **Daily Sessions:** Start a new session (`session_id`) for each day's optimization cycle.
* **Context Carryover:** At the start of a new day, the agent reads a summary of the previous day's performance (generated by the previous session) and injects it into the new session's context.
* **Benefits:** This keeps the context window clean, reduces token costs (by not reprocessing 6 days of chat history), and isolates failures (a crash on Day 4 doesn't corrupt the history of Day 1-3).
* **Checkpointing:** The SDK supports `enable_file_checkpointing`, which tracks filesystem changes.^20^ While less relevant for API-only agents, explicit "state checkpoints" (saving the campaign configuration to a file or DB) allow the agent to rollback changes if an optimization strategy fails.

## 6. Cognitive Architecture and System Prompt Engineering (RQ-004)

The System Prompt is the agent's "operating system." It defines the persona, the boundaries, and the fundamental rules of engagement. For a Google Ads agent, the prompt must be engineered to balance token efficiency with rigorous behavioral constraints.

### 6.1 Constraints and Configuration

The SDK consolidates system prompt configuration into the `system_prompt` field of `ClaudeAgentOptions`.^22^ While modern models support massive context windows (200k+ tokens), loading the prompt with excessive static data (like the entire Google Ads API documentation) is inefficient and costly.

* **Token Budget:** The system prompt should ideally remain under 2,000 tokens. It should focus on *how to think* rather than  *what to know* .
* **Knowledge Retrieval:** Instead of hardcoding API schemas in the prompt, the agent should be instructed to use introspection tools (like `list_tools` or a documentation lookup tool) to find the right tool for the job.

### 6.2 Dynamic Context Injection

A static system prompt cannot capture the dynamic state of the ad account. The agent needs to know the "State of the World" at runtime.

* **Strategy:** Inject dynamic context into the  **User Message** , not the System Prompt.
  * **Mechanism:** When the loop starts, the application programmatically constructs the first user message:
    > "Current Status: Date=2025-10-27. Account=123-456. Active Campaigns=3. Budget Utilization=85%. Critical Alerts: None. Please review the 'Summer' campaign."
    >
* **Placement:** Placing this in the user message ensures it is treated as "fresh" information to be acted upon, whereas system prompt instructions are treated as background rules.

### 6.3 Behavior Constraints and Guardrails

Prompt engineering alone is insufficient for safety ("Prompt Injection" or "Hallucination" risks). Constraints must be enforced via a "Defense in Depth" strategy.

1. **Prompt Layer:** "You are a conservative optimization agent. You must never delete campaigns. You must obtain approval for budget increases > 10%."
2. **Code Layer:** The `can_use_tool` callback (discussed in Section 3) acts as the hard guardrail. Even if the agent hallucinates and tries to call `DeleteCampaign`, the code layer must physically block it. The prompt serves to guide the agent away from trying, while the code ensures it cannot succeed if it tries.

### 6.4 Multi-Mode Prompting

Different phases of the agent's lifecycle require different cognitive postures.

* **Setup Mode:** "You are a creative strategist. Focus on ad copy generation and keyword expansion." (High creativity, lower safety).
* **Monitoring Mode:** "You are a strict analyst. Focus on anomaly detection and cost control. Do not make changes unless metrics deviate by 20%." (Low creativity, high safety).
* **Implementation:** The application can switch prompts by starting a new session with a different `system_prompt` configuration when the user switches modes in the UI.

## 7. Operational Dynamics: Turn Management and Optimization (RQ-005)

The `max_turns` parameter defines the endurance of the agent's reasoning loop. A "turn" consists of one Model Output + One User/Tool Input. Understanding and optimizing these turns is crucial for performance and cost control.

### 7.1 Turn Dynamics in Google Ads Workflows

A typical optimization workflow is multi-step:

1. **Turn 1:** Agent decides to query performance (Tool Call: `GetMetrics`).
2. **Turn 2:** Agent analyzes metrics, hypothesizes a bid change (Tool Call: `GetKeywordStats`).
3. **Turn 3:** Agent refines hypothesis (Tool Call: `UpdateBid`).
4. **Turn 4:** Agent verifies change (Tool Call: `GetBid`).
5. **Turn 5:** Agent reports success to user (Text Response).

This implies a minimum of 5 turns for a simple task. Complex workflows involving multiple campaigns can easily exceed 20 turns.

* **Recommendation:** Set `max_turns=30` for complex optimization tasks to prevent premature truncation. For simple status checks, `max_turns=5` is sufficient.

### 7.2 Stopping Criteria and Handling Limits

The agent stops when it emits a final text response without a tool call. If `max_turns` is reached before this happens, the SDK halts execution.

* **Behavior:** The agent does not "crash"; it simply stops processing. The last message might be a tool result that the agent never got to analyze.^23^
* **Recovery:** If the limit is hit, the application can theoretically "resume" the session with a higher limit, picking up where it left off, provided the session ID is preserved.

### 7.3 Optimization Strategies

Reducing turn count saves money and reduces latency.

* **Tool Batching:** The most effective optimization is to allow the agent to call multiple tools in a single turn. The prompt should explicitly encourage this: "If you need metrics for multiple campaigns, request them all in parallel." The SDK supports parallel tool execution if the model generates multiple tool blocks in one response.
* **Rich Observations:** Ensure the MCP tools return comprehensive data. Instead of returning just a campaign ID, return the ID, Name, Status, and Budget in one go. This prevents the agent from wasting a turn asking for details it could have received initially.

### 7.4 Cost Analysis

The cost model is driven by input tokens. In a long-running session, the context window grows with every turn.

* **Cost Accumulation:** Turn 1 costs **$X$**. Turn 10 costs **$X + (History of 1-9)$**.
* **Mitigation:** The SDK's context compaction features (beta) attempt to summarize history. Additionally, using the "Daily Session" pattern (resetting context daily) is the most effective cost control measure. The "Prompt Caching" feature of Claude (if supported by the SDK version) can also dramatically reduce the cost of repetitive system prompts and tool definitions.^24^

## 8. Observability, Debugging, and Error Handling (RQ-007)

Autonomous agents can be opaque. When an agent fails to optimize a campaign, distinguishing between a logic error (bad prompt), a capability error (missing tool), or an external error (API down) requires robust observability.

### 8.1 Debugging Tools

* **Verbose Logging:** The SDK's `verbose=True` option (or `--verbose` flag) is the first line of defense. It exposes the raw "Chain of Thought" (CoT)—the internal monologue where the agent plans its moves before executing them.^8^ Capturing these logs is essential for tuning the system prompt.
* **Tracing:** Native integration with **LangSmith** is supported and highly recommended.^26^ LangSmith visualizes the trace tree, showing the latency of every step. This allows developers to see if a delay is due to the model "thinking" (generation latency) or the Google Ads API "fetching" (network latency).

### 8.2 Decision Transparency and Partial Failures

Transparency is achieved by capturing the model's reasoning trace. The agent usually outputs a "Thinking" block before a "Tool Use" block. This thinking block explains *why* it is choosing a tool.

* **Partial Failure:** In a batch operation (e.g., updating 5 keywords), 3 might succeed and 2 might fail due to policy violations.
* **Transactional Logic:** The agent should be prompted to check the results of *all* operations. "Check the status of every update. If any failed, report them specifically." The MCP tool should return a structured result: `{"success": ["id1", "id2"], "failed":}`. This allows the agent to reason about the partial failure and retry only the failed items.

### 8.3 Human-in-the-Loop Intervention

Sometimes an agent goes off the rails—looping on an error or pursuing a suboptimal strategy.

* **Intervention:** The `ClaudeSDKClient` supports an `interrupt()` method. A monitoring system (or a human watcher) can trigger this to pause the loop.
* **Correction:** Once paused, a "Teacher" message can be injected: "You are stuck in a loop trying to update a paused campaign. Stop and check the campaign status first." This guides the agent back to a correct path without killing the session.^3^

## 9. Implementation Roadmap

Based on this deep research, the implementation of the Phase 2 Google Ads Agent should proceed with the following architectural specifications:

1. **Runtime:** Deploy `ClaudeSDKClient` within a containerized Python service. Ensure Node.js dependencies are present for the transport layer.
2. **MCP Topology:** Utilize the **In-Process** topology. Create a custom SDK-based MCP server that wraps the `GoogleAdsClient`. Implement `can_use_tool` with strict, logic-based allow-lists for mutation tools.
3. **State Layer:** Implement the **Sidecar Persistence** pattern. Write all message events to a PostgreSQL database to drive the UI. Use the SDK's session ID only for LLM context resumption.
4. **Operational Cycle:** Adopt the **Daily Session** pattern. Spin up a new session every 24 hours, injecting a summary of the previous day's state to maintain continuity while managing token costs.
5. **Safety:** Enforce a `max_turns=30` limit and a rigorous `can_use_tool` policy that defaults to "Deny" for all unknown tools.

This architecture balances the autonomy required for effective management with the safety and observability required for financial operations.
