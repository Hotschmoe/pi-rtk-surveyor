# Cortical Stack Checkpoint

Save current state for session continuity and compaction recovery.

## When To Run
- End of session (auto-prompted by Stop hook)
- Before long operations that might hit context limits
- When switching tasks
- Every ~30 min during long sessions

## Steps

### 1. Update CURRENT.md

```markdown
> **Last Updated:** [NOW] | **Active Task:** [task name or _none_]

## Now
[What you're working on - 1-3 items]

## Next Steps
1. [Very next action]
2. [Then this]

## Active Task
**Task:** [name] | **Status:** [WIP/Planning] | **Started:** [date]

### Goal
[What done looks like]

### Subtasks
- [x] Completed step
- [ ] Current step  <-- you are here
- [ ] Next step

### Decisions
| Decision | Choice | Why | Date |
|----------|--------|-----|------|
| [topic] | [choice] | [reason] | [date] |

## Context
[Key files, blockers, critical info]

## Notes
[Scratch space]
```

### 2. Update PLAN.md

- Update task status: `- [ ]` -> `- [>]`
- Add any discovered bugs/debt/ideas to Backlog section

## On Compaction / Context Loss

If you notice you've lost context:

1. Read `.cstack/CURRENT.md` immediately
2. Check "Active Task" for goal and subtasks
3. Resume from "Next Steps" or `<-- you are here` marker
4. Read `PLAN.md` if you need broader context

**Signs:** You don't remember what you were working on, user references something unfamiliar, or unsure of task state.
