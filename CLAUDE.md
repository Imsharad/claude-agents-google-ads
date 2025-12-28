# Claude Code Instructions for Growth-Tier Ads Protocol Agent

## Project Overview
Building an autonomous Google Ads management agent using Claude Agent SDK.

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
| TASK-000 | sessions/13535533309531173281 | PRD SDK Architecture |
| TASK-001 | sessions/16019360090854142714 | Google Ads API Spec |
| TASK-004 | sessions/14129617969833698085 | Agent Loop Pattern |
| TASK-010 | sessions/16721566770188284192 | Python Environment |
| TASK-016 | sessions/13756300551230697280 | Testing Framework |

## Priority Order for Launches
When slots open, prioritize by:
1. Tasks that unblock the most other tasks
2. Lower task numbers (earlier phases)
3. P0 > P1 > P2 priority

## Dependency Unlocks
When these complete, these unlock:
- TASK-000 complete → unlocks nothing immediate (Phase 2 deps)
- TASK-001 complete → TASK-011 gets closer (needs TASK-010 too)
- TASK-004 complete → unlocks nothing immediate (Phase 2 deps)
- TASK-010 complete → TASK-011 gets closer (needs TASK-001 too)
- TASK-016 complete → nothing blocked by it

**Critical Path**: TASK-010 + TASK-001 → TASK-011 → TASK-012 → TASK-013/14/15
