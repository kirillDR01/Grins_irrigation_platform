---
name: find-prompts
category: prompt-management
tags: [search, discovery, find, prompts]
created: 2024-01-12
updated: 2024-01-12
usage: "@find-prompts \"keyword or category\""
related: [list-prompts, prompt-help, related-prompts]
description: "Search for prompts by keyword, category, or purpose with intelligent matching"
---

# Find Prompts

Search the prompt library for prompts matching your criteria.

## Instructions

1. **Parse the search query** to understand what the user is looking for:
   - Category names (documentation, code-review, testing, etc.)
   - Keywords or tags (devlog, quick, comprehensive, etc.)
   - Purpose descriptions (logging, analysis, updates, etc.)

2. **Search through available prompts** by:
   - Reading PROMPT-REGISTRY.md for overview
   - Checking metadata headers in prompt files
   - Matching against names, categories, tags, and descriptions

3. **Present results** in a clear format:
   - Prompt name and category
   - Brief description
   - Usage example
   - Related prompts

4. **Provide usage guidance**:
   - How to use the found prompts
   - When each prompt is most appropriate
   - Suggest combinations or workflows

## Examples

- `@find-prompts "devlog"` - Find all devlog-related prompts
- `@find-prompts "documentation"` - Find all documentation prompts
- `@find-prompts "quick"` - Find prompts for quick updates
- `@find-prompts "analysis"` - Find analytical or summary prompts

## Output Format

```
Found [X] prompts matching "[search term]":

**prompt-name** (Category)
Description: [brief description]
Usage: [usage example]
Related: [related prompts]

[Additional prompts...]

**Suggestions:**
- [Usage recommendations]
- [Workflow suggestions]
```