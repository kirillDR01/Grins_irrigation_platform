---
name: prompt-help
category: prompt-management
tags: [help, usage, instructions, details]
created: 2024-01-12
updated: 2024-01-12
usage: "@prompt-help \"prompt-name\""
related: [find-prompts, list-prompts, related-prompts]
description: "Get detailed help and usage instructions for a specific prompt"
---

# Prompt Help

Get comprehensive help and usage instructions for a specific prompt.

## Instructions

1. **Identify the requested prompt** from the prompt name provided

2. **Read the prompt file** to get complete information:
   - Parse metadata header for structured information
   - Read full prompt content and instructions
   - Understand the prompt's purpose and capabilities

3. **Provide comprehensive help** including:
   - What the prompt does (purpose and capabilities)
   - How to use it (syntax and examples)
   - When to use it (appropriate scenarios)
   - What to expect (typical outputs or behaviors)
   - Related prompts that might be useful

4. **Include practical examples**:
   - Basic usage examples
   - Advanced usage patterns
   - Common use cases
   - Integration with workflows

5. **If prompt doesn't exist**, suggest similar prompts or help find what they're looking for

## Examples

- `@prompt-help "devlog-entry"` - Get detailed help for devlog-entry prompt
- `@prompt-help "find-prompts"` - Learn how to search for prompts
- `@prompt-help "nonexistent"` - Get suggestions for similar prompts

## Output Format

```
# Help: [prompt-name]

## Purpose
[What this prompt does and why it's useful]

## Usage
**Basic Syntax:** [usage syntax]
**Examples:**
- [example 1]
- [example 2]

## When to Use
- [scenario 1]
- [scenario 2]

## What to Expect
[Description of typical outputs or behaviors]

## Related Prompts
- **[related-prompt]**: [brief description]

## Tips
- [usage tip 1]
- [usage tip 2]
```