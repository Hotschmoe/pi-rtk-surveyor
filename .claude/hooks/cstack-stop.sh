#!/bin/bash
# Hook: Remind to checkpoint before session ends
# Output is shown to Claude as a reminder

echo "=== CORTICAL STACK: SESSION ENDING ==="
echo ""
echo "IMPORTANT: Before this session ends, please save your state:"
echo ""
echo "1. Update .cstack/CURRENT.md with:"
echo "   - Current task progress"
echo "   - What you're focused on"
echo "   - Next steps for resumption"
echo ""
echo "2. Update .cstack/PLAN.md with:"
echo "   - Task status changes ([ ] -> [>] -> [x])"
echo "   - Any new tasks discovered"
echo ""
echo "Do this now to preserve context for the next session."
