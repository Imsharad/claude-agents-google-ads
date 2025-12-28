# Task Orchestrator System

## Overview
This orchestrator manages parallel task execution via Jules MCP server. It tracks dependencies, monitors session status, and auto-launches new tasks when blockers complete.

## How to Run

### Option 1: Manual Orchestration (Claude Code)
Ask Claude Code to run: `/orchestrate` or say "run orchestration cycle"

### Option 2: Continuous Mode
Say: "run continuous orchestration" - Claude will poll every 60 seconds

## Orchestration Cycle

Each cycle performs:
1. **Poll** - Check status of all in_progress Jules sessions
2. **Update** - Mark completed tasks in task_state.json
3. **Resolve** - Find newly unblocked tasks
4. **Launch** - Start up to MAX_PARALLEL new tasks
5. **Report** - Show status summary

## Files

| File | Purpose |
|------|---------|
| `task_state.json` | Current status of all tasks |
| `dependencies.json` | Task dependency graph |
| `task_prompts.json` | Jules prompts for each task |

## Task States

- `pending` - Not started, waiting for dependencies
- `ready` - Dependencies met, can be launched
- `in_progress` - Jules session running
- `completed` - PR created successfully
- `failed` - Needs manual intervention

## Commands for Claude Code

```
# Run one orchestration cycle
"orchestrate" or "run orchestration"

# Check specific session
"check session <session_id>"

# Launch specific task
"launch TASK-XXX"

# Show dependency graph
"show task dependencies"

# Force complete a task (manual override)
"mark TASK-XXX as completed"
```

## Concurrency Rules

- Max 5 parallel Jules sessions
- Phase 0 tasks can all run in parallel (no deps)
- Phase 1+ tasks respect dependency chains
- Cross-phase dependencies are enforced

## Example Flow

```
Cycle 1:
  - TASK-010, TASK-016 running (Phase 1, no deps)
  - Launch: TASK-000 to TASK-007 (Phase 0, no deps) [5 max]

Cycle 2:
  - TASK-010 completes
  - TASK-001 completes (from Phase 0)
  - TASK-011 now unblocked (needs TASK-001 + TASK-010)
  - Launch: TASK-011

Cycle 3:
  - TASK-011 completes
  - TASK-012 now unblocked
  - Launch: TASK-012

... and so on
```

## Recovery

If a task fails:
1. Check Jules activities: `jules_get_activities <session_id>`
2. Fix issue manually or adjust prompt
3. Re-launch: `launch TASK-XXX --force`
