#!/bin/bash
# Hook: Inject context at session start
# Output is shown to Claude to provide context

echo "=== CORTICAL STACK: SESSION START ==="
echo ""
echo "Reading agent state from .cstack/..."
echo ""

if [ -f ".cstack/CURRENT.md" ]; then
    echo "--- CURRENT.md (active state) ---"
    cat ".cstack/CURRENT.md"
    echo ""
fi

if [ -f ".cstack/PLAN.md" ]; then
    echo "--- PLAN.md (task backlog) ---"
    cat ".cstack/PLAN.md"
    echo ""
fi

echo "=== Stack loaded. Ask the user what they'd like to work on. ==="
