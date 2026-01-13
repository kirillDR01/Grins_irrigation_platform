---
name: related-prompts
category: prompt-management
tags: [related, similar, connections, workflow]
created: 2024-01-12
updated: 2024-01-12
usage: "@related-prompts \"prompt-name\""
related: [find-prompts, prompt-help, list-prompts]
description: "Find prompts related to a specific prompt, showing connections and workflow patterns"
---

# Related Prompts

Find prompts that are related to or work well with a specific prompt.

## Instructions

1. **Identify the base prompt** from the name provided

2. **Find relationships** by analyzing:
   - Metadata "related" field in prompt headers
   - Same category prompts
   - Similar tags or keywords
   - Complementary functionality
   - Workflow connections

3. **Categorize relationships**:
   - **Direct Relations**: Explicitly listed in metadata
   - **Same Category**: Prompts in the same functional area
   - **Workflow Partners**: Prompts commonly used together
   - **Alternatives**: Different approaches to similar goals

4. **Provide usage context**:
   - How prompts work together
   - Typical workflow patterns
   - When to use each related prompt
   - Sequence recommendations

5. **If no relations found**, suggest prompts in the same category or with similar purposes

## Examples

- `@related-prompts "devlog-entry"` - Find prompts related to devlog-entry
- `@related-prompts "find-prompts"` - Find other prompt management tools
- `@related-prompts "unknown-prompt"` - Get suggestions for similar functionality

## Output Format

```
# Related to: [prompt-name]

## Direct Relations
- **[prompt-name]**: [description and relationship]

## Same Category ([category-name])
- **[prompt-name]**: [description]

## Workflow Partners
- **[prompt-name]**: [how they work together]

## Alternatives
- **[prompt-name]**: [different approach to similar goal]

## Suggested Workflows
1. **[workflow-name]**: [prompt1] → [prompt2] → [prompt3]
2. **[workflow-name]**: [description of usage pattern]

## Tips
- [tip about using related prompts together]
- [workflow optimization suggestions]
```