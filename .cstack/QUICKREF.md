# Quick Reference

## Commands

| Command | What it does |
|---------|--------------|
| `/cstack-task` | List tasks with numbers |
| `/cstack-task start 1` | Start task #1 (quick) |
| `/cstack-task start 1 --plan` | Start task #1 with interview |
| `/cstack-task add P1: X` | Add new task |
| `/cstack-task done` | Complete active task |
| `/cstack-task block 1` | Block task #1 |
| `/cstack-task ready 1` | Unblock task #1 |
| `/cstack-task decide` | Record decision |
| `/cstack-checkpoint` | Save all state |

## Task Format

```
- [status] P#: Title | context | next: action
```

**Status:** `- [ ]` Pending | `- [>]` In Progress | `- [x]` Completed | `- [!]` Blocked
**Priority:** P0=Critical P1=High P2=Medium P3=Low

## Files

| File | Purpose |
|------|---------|
| `CURRENT.md` | Session state + active task detail |
| `PLAN.md` | Task list + backlog |
| `INBOX.md` | Messages TO this agent |
| `OUTBOX.md` | Messages FROM this agent |

## Workflow

```
/cstack-task                     # See numbered task list
    |
/cstack-task start 1             # Start task (or --plan for interview)
    |
[work on task]                   # Check off subtasks in CURRENT.md
    |
/cstack-task done                # Complete, clear active task
    |
/cstack-checkpoint               # Save state
```

## On Compaction

1. Run `/cstack-checkpoint`
2. Read CURRENT.md
3. Continue from Next Steps / current subtask
