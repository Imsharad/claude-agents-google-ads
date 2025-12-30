# Claude Code Instructions for Growth-Tier Ads Protocol Agent

## Project Overview
Building an autonomous Google Ads management agent using Claude Agent SDK.

**Status (Dec 30, 2025):** Phases 0-2 complete (100%), Phase 3 at 83% with TASK-033 in progress. 30/31 tasks done, 29 PRs merged.

## Orchestration System

### Commands
When the user says any of these, run an orchestration cycle:
- "orchestrate"
- "run orchestration"
- "check tasks"
- "task status"

### Orchestration Cycle Steps

1. **Poll Active Sessions**
   ```
   For each session_id in orchestrator/task_state.json where status="in_progress":
     - Call mcp__jules__jules_get_session_status(session_id)
     - If state="COMPLETED" or state="DONE": mark task as completed
     - If state="FAILED": mark as failed and alert user
   ```

2. **Update State**
   - Write updated statuses to orchestrator/task_state.json
   - Count active_sessions

3. **Find Unblocked Tasks**
   ```python
   for task in pending_tasks:
     deps = dependencies.json[task]["depends_on"]
     if all(task_state[dep]["status"] == "completed" for dep in deps):
       task is READY to launch
   ```

4. **Launch New Tasks**
   - Calculate slots: max_parallel (5) - active_sessions
   - For each ready task (up to slots available):
     - Load prompt from orchestrator/task_prompts.json
     - Call mcp__jules__jules_start_session()
     - Update task_state.json

5. **Report Status**
   Show table:
   ```
   | Task | Status | Session | PR |
   |------|--------|---------|-----|
   ```

### Key Files
- `orchestrator/task_state.json` - Current task statuses and session IDs
- `orchestrator/dependencies.json` - Task dependency graph
- `orchestrator/task_prompts.json` - Jules prompts for each task
- `tasks.json` - Full task definitions

### Session States
- `unknown` / `IN_PROGRESS` - Still running
- `COMPLETED` / `DONE` - Finished, check for PR
- `FAILED` - Needs intervention

### Repository
- GitHub: https://github.com/Imsharad/claude-agents-google-ads
- Jules source: sources/github/Imsharad/claude-agents-google-ads

## Current Active Sessions

| Task | Session ID | Description |
|------|------------|-------------|
| TASK-033 | sessions/16558981767423115949 | Automated Optimization Logic |

## Next Steps
- Complete TASK-033 to finish Phase 3
- Phase 4 (Advanced Features) available: Custom Audiences, Keyword Forecasting, Multi-Agent Orchestration
