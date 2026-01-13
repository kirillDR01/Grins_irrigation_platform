---
name: list-prompts
category: prompt-management
tags: [list, overview, catalog, all]
created: 2024-01-12
updated: 2024-01-12
usage: "@list-prompts [optional category]"
related: [find-prompts, prompt-help, related-prompts]
description: "Display all available prompts organized by category with descriptions and usage examples"
---

# List Prompts

Display a comprehensive overview of all available prompts in the system.

## Instructions

1. **Read the PROMPT-REGISTRY.md** to get current prompt information

2. **Organize prompts by category** for easy browsing:
   - Group related prompts together
   - Show category descriptions
   - Include prompt counts per category

3. **For each prompt, display**:
   - Name and usage syntax
   - Brief description
   - Key tags or keywords
   - When to use it

4. **Include helpful information**:
   - Total prompt count
   - Most recently added prompts
   - Usage patterns and workflows
   - Quick reference commands

5. **If category is specified**, filter to show only prompts in that category

## Examples

- `@list-prompts` - Show all prompts organized by category
- `@list-prompts documentation` - Show only documentation prompts
- `@list-prompts prompt-management` - Show prompt management tools

## Output Format

```
# Available Prompts ([X] total)

## [Category Name] ([X] prompts)
[Category description]

- **prompt-name**: [description] 
  Usage: [usage example]
  
[Additional prompts in category...]

## Quick Reference
- Use @find-prompts "keyword" to search
- Use @prompt-help "name" for detailed help
- Use @related-prompts "name" to find similar prompts

## Recent Additions
- [Recently added prompts with dates]
```