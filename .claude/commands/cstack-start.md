# Cortical Stack Start

Read context and show task list.

## Steps

1. **Read CURRENT.md** - Check active task, next steps
2. **Read PLAN.md** - Get task list

## Output

Show status summary:
```
Active: [task name] - [current subtask]
   or: No active task

Tasks:
1. [P1] Task name | context
2. [P2] Another task | context
...

What would you like to work on?
```

If there's an active task, ask if user wants to continue or switch.

## On Context Loss

If you're resuming after compaction or session restart:

1. Read `.cstack/CURRENT.md` first
2. Look for the `<-- you are here` marker in subtasks
3. Check "Next Steps" section for ordered actions
4. Read PLAN.md for broader context if needed

**Signs you need recovery:** You don't remember what you were working on, the user references something unfamiliar, or you're unsure of the current task state.
