# Cortical Stack Task

Task operations and planning.

## Usage
```
/cstack-task                      # List all tasks (default)
/cstack-task start 1              # Start task #1 (quick, no interview)
/cstack-task start 1 --plan       # Start task #1 with full interview
/cstack-task add P1: Title | ctx  # Add new task
/cstack-task done                 # Complete active task
/cstack-task block 1 | reason     # Block task #1
/cstack-task ready 1              # Unblock task #1
/cstack-task decide "Topic" | choice | reason
```

---

## List Tasks (Default)

When user runs `/cstack-task` with no arguments:

1. Read PLAN.md Tasks section
2. Display numbered list with priority:
```
Tasks:
1. [P1] User auth | JWT approach | next: session mgmt
2. [P2] Fix navbar | responsive issue
3. [P3] Add tests
4. [BLOCKED] Payments | waiting: API keys

Active: #1 User auth (WIP)
```
3. Show which task is active (if any)

---

## Start Task

### Quick Start (default): `/cstack-task start 1`

1. Find task #1 in PLAN.md
2. Update CURRENT.md Active Task section:
```markdown
## Active Task

**Task:** User auth | **Status:** WIP | **Started:** 2026-01-19

### Goal
[Copied from task context in PLAN.md, or "Complete this task"]

### Scope
**In:** [From task line context]
**Out:** _Not defined_

### Constraints
_None identified._

### Subtasks
- [ ] [From "next:" in task line, or first step]

### Decisions
| Decision | Choice | Why | Date |
|----------|--------|-----|------|
```
3. Update PLAN.md: `- [ ]` -> `- [>]`
4. Tell user: "Started #1: User auth. First step: [next action]. Go?"

### With Interview: `/cstack-task start 1 --plan`

1. Find task #1 in PLAN.md
2. Run interview (ask user):
   - **Goal:** What does "done" look like?
   - **Scope:** What's in? What's explicitly out?
   - **Constraints:** Tech limits, dependencies, blockers?
   - **Steps:** Main steps to complete this?
   - **First action:** What's the very first concrete step?
3. Populate CURRENT.md Active Task with answers
4. Update PLAN.md: `- [ ]` -> `- [>]`
5. Confirm: "Ready. First step: [X]. Proceed?"

---

## Add Task

`/cstack-task add P1: Title | context | next: action`

Add to PLAN.md Tasks section:
```markdown
- [ ] P1: Title | context | next: action
```

---

## Complete Task

`/cstack-task done`

1. Remove active task from PLAN.md (task is complete, no need to track)
2. Clear CURRENT.md Active Task section:
```markdown
## Active Task

**Task:** _none_ | **Status:** -- | **Started:** --

### Goal
_Not yet defined._

### Scope
**In:** _items_
**Out:** _items_

### Constraints
_None identified._

### Subtasks
- [ ] _subtask_

### Decisions
| Decision | Choice | Why | Date |
|----------|--------|-----|------|
```

---

## Block / Ready

`/cstack-task block 1 | reason` - Block task #1:
```markdown
- [!] P1: Task | blocked: reason
```

`/cstack-task ready 1` - Unblock task #1:
```markdown
- [ ] P1: Task | context
```

---

## Record Decision

`/cstack-task decide "Topic" | choice | reason`

Add to CURRENT.md Decisions table:
```markdown
| Topic | choice | reason | 2026-01-19 |
```

---

## Discovered Work

Add to PLAN.md Backlog section:
```markdown
### Bugs
- [!] P2: Description | file:line | details

### Debt
- [ ] P3: Description | why | impact

### Ideas
- [ ] Description | value
```
