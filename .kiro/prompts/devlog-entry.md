---
name: devlog-entry
category: documentation
tags: [devlog, manual, comprehensive, detailed]
created: 2024-01-12
updated: 2024-01-12
usage: "@devlog-entry [optional description]"
related: [devlog-summary, devlog-quick]
description: "Create comprehensive devlog entries with detailed technical information, decision rationale, and impact analysis"
---

# Manual Devlog Entry

Create a comprehensive devlog entry in DEVLOG.md following the detailed format specified in the devlog-rules.md steering file.

## Instructions

1. **If no specific details are provided**, ask me for the following information:
   - What specific work was accomplished?
   - What technical approaches or technologies were used?
   - What decisions were made and why?
   - Were there any challenges or obstacles encountered?
   - What is the impact on the project?
   - What are the next steps or follow-up tasks?

2. **Use the comprehensive entry format** from devlog-rules.md including:
   - What Was Accomplished
   - Technical Details
   - Decision Rationale
   - Challenges and Solutions
   - Impact and Dependencies
   - Next Steps
   - Resources and References

3. **Be thorough and detailed** - include enough information for future reference and team members

4. **Choose the appropriate category** from the predefined list (FEATURE, BUGFIX, REFACTOR, etc.)

5. **Add the entry to DEVLOG.md** with proper timestamp and formatting

## Usage Examples

- `@devlog-entry` - I'll ask you for details to create a comprehensive entry
- `@devlog-entry Implemented user authentication with JWT tokens` - I'll create an entry and ask for additional details as needed
- `@devlog-entry BUGFIX: Fixed memory leak in data processing pipeline` - I'll create a detailed bugfix entry