# Hook: Remind to checkpoint before session ends
# Output is shown to Claude as a reminder

Write-Output "=== CORTICAL STACK: SESSION ENDING ==="
Write-Output ""
Write-Output "IMPORTANT: Before this session ends, please save your state:"
Write-Output ""
Write-Output "1. Update .cstack/CURRENT.md with:"
Write-Output "   - Current task progress"
Write-Output "   - What you're focused on"
Write-Output "   - Next steps for resumption"
Write-Output ""
Write-Output "2. Update .cstack/PLAN.md with:"
Write-Output "   - Task status changes ([ ] -> [>] -> [x])"
Write-Output "   - Any new tasks discovered"
Write-Output ""
Write-Output "Do this now to preserve context for the next session."
