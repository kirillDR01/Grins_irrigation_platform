# Prompt Registry

## Overview
This registry catalogs all custom prompts available in this project. Each prompt includes metadata for easy discovery and usage guidance.

## Quick Reference Commands
- `@find-prompts "keyword"` - Search for prompts by keyword or category
- `@prompt-help "prompt-name"` - Get detailed help for a specific prompt
- `@list-prompts` - List all available prompts with descriptions
- `@related-prompts "prompt-name"` - Find prompts related to a specific one

## Available Prompts

| Name | Category | Purpose | Usage | Tags |
|------|----------|---------|-------|------|
| `devlog-entry` | Documentation | Create comprehensive manual devlog entries | `@devlog-entry [description]` | devlog, manual, comprehensive |
| `devlog-summary` | Documentation | Generate complete session analysis and summary | `@devlog-summary` | devlog, automatic, session, analysis |
| `devlog-quick` | Documentation | Create streamlined devlog updates | `@devlog-quick "brief description"` | devlog, quick, update |
| `find-prompts` | Prompt Management | Search for prompts by keyword or category | `@find-prompts "keyword"` | search, discovery, find |
| `list-prompts` | Prompt Management | Display all available prompts by category | `@list-prompts [category]` | list, overview, catalog |
| `prompt-help` | Prompt Management | Get detailed help for specific prompts | `@prompt-help "prompt-name"` | help, usage, instructions |
| `related-prompts` | Prompt Management | Find prompts related to a specific prompt | `@related-prompts "prompt-name"` | related, similar, workflow |

## Categories

### Documentation
Prompts for creating, updating, and managing project documentation.
- **devlog-entry**: Detailed manual documentation entries
- **devlog-summary**: Comprehensive session summaries
- **devlog-quick**: Quick progress updates

### Prompt Management
Prompts for discovering, managing, and getting help with the prompt system itself.
- **find-prompts**: Search and discover prompts by criteria
- **list-prompts**: Browse all available prompts
- **prompt-help**: Get detailed usage instructions
- **related-prompts**: Find connected and workflow-related prompts

## Usage Patterns

### Devlog Workflow
1. **During development**: Use `@devlog-quick` for brief updates
2. **After major work**: Use `@devlog-entry` for comprehensive documentation
3. **End of session**: Use `@devlog-summary` for complete analysis

### Discovery Workflow
1. **Find prompts**: `@find-prompts "documentation"` to find all doc-related prompts
2. **Get help**: `@prompt-help "devlog-entry"` for detailed usage instructions
3. **Explore related**: `@related-prompts "devlog-entry"` to find similar prompts
4. **Browse all**: `@list-prompts` to see complete catalog

### Prompt Management Workflow
1. **Discover**: Use `@find-prompts` to search by keyword or category
2. **Learn**: Use `@prompt-help` to understand specific prompts
3. **Connect**: Use `@related-prompts` to find workflow connections
4. **Browse**: Use `@list-prompts` for comprehensive overview

## Maintenance

### Adding New Prompts
1. Create prompt file with standardized metadata header
2. Update this registry with new entry
3. Test prompt functionality
4. Document in devlog

### Metadata Standards
All prompts should include:
- `name`: Prompt identifier
- `category`: Logical grouping
- `tags`: Searchable keywords
- `created`: Creation date
- `updated`: Last modification date
- `usage`: Example usage syntax
- `related`: Related prompt names

## Statistics
- **Total Prompts**: 7
- **Categories**: 2 (Documentation, Prompt Management)
- **Last Updated**: 2024-01-12

---

*This registry is maintained automatically and manually. Use the prompt-manager agent for interactive discovery and management.*