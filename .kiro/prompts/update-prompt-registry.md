---
name: update-prompt-registry
category: Prompt Management
tags: [registry, automation, maintenance, sync]
description: Automatically scan prompts directory and regenerate PROMPT-REGISTRY.md
created: 2025-01-13
updated: 2025-01-13
usage: "@update-prompt-registry"
related: [find-prompts, list-prompts, prompt-help]
---

# Update Prompt Registry

Automatically scan all prompt files and regenerate PROMPT-REGISTRY.md.

## What This Prompt Does

When you use `@update-prompt-registry`, I will:

1. **Scan** `.kiro/prompts/` directory for all `.md` files
2. **Extract metadata** from YAML frontmatter in each prompt
3. **Organize** prompts by category
4. **Generate** complete PROMPT-REGISTRY.md with:
   - Overview and quick reference
   - Table of all prompts with metadata
   - Category descriptions
   - Usage patterns
   - Maintenance guidelines
   - Statistics (total prompts, categories, last updated)
5. **Validate** that all prompts have required metadata
6. **Report** what was found and updated

## What You Get

- ✅ Fully regenerated PROMPT-REGISTRY.md
- ✅ All prompts cataloged with current metadata
- ✅ Categories automatically organized
- ✅ Statistics updated
- ✅ Validation report of any issues

## Usage

Simply run:
```
@update-prompt-registry
```

## Process Details

### Step 1: Scan Directory
- Read all `.md` files in `.kiro/prompts/`
- Skip `PROMPT-REGISTRY.md` and `README-*.md` files
- Extract YAML frontmatter from each file

### Step 2: Extract Metadata
For each prompt, extract:
- `name`: Prompt identifier
- `category`: Logical grouping
- `tags`: Searchable keywords
- `description`: Brief purpose
- `usage`: Usage syntax
- `related`: Related prompt names
- `created`: Creation date
- `updated`: Last modification date

### Step 3: Validate Metadata
Check that each prompt has:
- Required fields: name, category, description, usage
- Valid category name
- Proper date format (YYYY-MM-DD)
- Non-empty tags array

### Step 4: Organize by Category
Group prompts into categories:
- Documentation
- Prompt Management
- Development Workflow
- Code Quality
- (Any new categories found)

### Step 5: Generate Registry
Create complete PROMPT-REGISTRY.md with:
- Overview section
- Quick reference commands
- Table of all prompts
- Category descriptions with prompt lists
- Usage patterns
- Maintenance guidelines
- Statistics

### Step 6: Report Results
Show:
- Total prompts found
- Prompts by category
- Any validation warnings
- What was updated

## Example Output

```
## Scanning Prompts Directory

Found 13 prompt files:
- devlog-entry.md ✓
- devlog-summary.md ✓
- devlog-quick.md ✓
- find-prompts.md ✓
- list-prompts.md ✓
- prompt-help.md ✓
- related-prompts.md ✓
- git-commit-push.md ✓
- new-feature.md ✓
- add-tests.md ✓
- add-logging.md ✓
- quality-check.md ✓
- update-prompt-registry.md ✓

## Organizing by Category

Documentation: 3 prompts
Prompt Management: 4 prompts
Development Workflow: 1 prompt
Code Quality: 4 prompts

## Validation Results

✅ All prompts have required metadata
✅ All categories are valid
✅ All dates are properly formatted

## Registry Updated

- Total Prompts: 13
- Categories: 4
- Last Updated: 2025-01-13

PROMPT-REGISTRY.md has been regenerated successfully!
```

## Validation Warnings

If issues are found, you'll see warnings like:

```
⚠️ Warning: devlog-entry.md missing 'related' field
⚠️ Warning: new-feature.md has invalid date format in 'created'
⚠️ Warning: Unknown category 'Testing' in add-tests.md
```

These won't stop the update, but you should fix them.

## When to Use

Run this prompt whenever:
- You create a new prompt file
- You modify prompt metadata
- You want to verify registry is in sync
- You add new categories
- You're unsure if registry is current

## Notes

- This prompt reads actual files, not just the registry
- It's the source of truth for what prompts exist
- Always run after creating/modifying prompts
- Safe to run multiple times (idempotent)
- Backs up existing registry before updating (optional)

## Required Metadata Format

Each prompt file must have YAML frontmatter:

```yaml
---
name: prompt-name
category: Category Name
tags: [tag1, tag2, tag3]
description: Brief description of what this prompt does
created: YYYY-MM-DD
updated: YYYY-MM-DD
usage: "@prompt-name [arguments]"
related: [other-prompt, another-prompt]
---
```

## Categories

Valid categories (automatically detected):
- Documentation
- Prompt Management
- Development Workflow
- Code Quality
- (Any new category you create)

New categories are automatically added when found in prompt metadata.
