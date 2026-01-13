# Prompt Management System Documentation

## Overview

This repository includes a comprehensive prompt management system that combines centralized cataloging, standardized metadata, and interactive discovery tools to help you track, organize, and effectively use custom prompts as your library grows.

## System Architecture

### Three-Component Hybrid Approach

#### 1. **Central Registry** (Option 1)
- **File**: `.kiro/prompts/PROMPT-REGISTRY.md`
- **Purpose**: Single source of truth for all prompts
- **Features**: Searchable table format, categories, usage examples, statistics

#### 2. **Standardized Metadata** (Option 5)
- **Location**: Frontmatter headers in each prompt file
- **Purpose**: Machine-readable prompt information
- **Features**: Tags, relationships, usage patterns, version tracking

#### 3. **Interactive Management** (Option 4)
- **Agent**: `prompt-manager-agent` for intelligent prompt assistance
- **Prompts**: Discovery and help prompts for interactive usage
- **Features**: Smart search, contextual help, relationship mapping

## File Structure

```
.kiro/prompts/
├── PROMPT-REGISTRY.md           # Central catalog and overview
├── README-prompt-management.md  # This documentation
│
├── # Core Documentation Prompts
├── devlog-entry.md             # Comprehensive manual devlog entries
├── devlog-summary.md           # Session analysis and summaries
├── devlog-quick.md             # Quick progress updates
│
├── # Prompt Management Tools
├── find-prompts.md             # Search prompts by criteria
├── list-prompts.md             # Browse all available prompts
├── prompt-help.md              # Get detailed prompt help
└── related-prompts.md          # Find related prompts

.kiro/agents/
└── prompt-manager-agent.json   # Specialized prompt management agent
```

## Metadata Schema

Every prompt includes standardized frontmatter:

```yaml
---
name: prompt-identifier          # Unique prompt name
category: category-name          # Logical grouping
tags: [tag1, tag2, tag3]        # Searchable keywords
created: YYYY-MM-DD             # Creation date
updated: YYYY-MM-DD             # Last modification
usage: "@prompt-name [args]"     # Usage syntax
related: [prompt1, prompt2]      # Related prompt names
description: "Brief description" # Purpose and capabilities
---
```

## Usage Guide

### Discovery Commands

#### Find Prompts by Criteria
```
@find-prompts "devlog"           # Find devlog-related prompts
@find-prompts "documentation"    # Find documentation prompts
@find-prompts "quick"           # Find prompts for quick updates
```

#### Browse All Prompts
```
@list-prompts                   # Show all prompts by category
@list-prompts documentation     # Show only documentation prompts
@list-prompts prompt-management # Show prompt management tools
```

#### Get Detailed Help
```
@prompt-help "devlog-entry"     # Detailed help for specific prompt
@prompt-help "find-prompts"     # Learn how to search prompts
```

#### Find Related Prompts
```
@related-prompts "devlog-entry" # Find prompts related to devlog-entry
@related-prompts "list-prompts" # Find other management tools
```

### Direct Agent Interaction
```
/agent swap prompt-manager-agent
> Help me find prompts for documentation
> What's the best prompt for quick updates?
> Show me all prompts related to devlog workflows
```

## Workflow Patterns

### New User Discovery
1. `@list-prompts` - Get overview of all available prompts
2. `@find-prompts "category"` - Find prompts for specific needs
3. `@prompt-help "prompt-name"` - Learn how to use specific prompts
4. `@related-prompts "prompt-name"` - Discover workflow connections

### Daily Usage
1. Use prompts directly: `@devlog-quick "completed feature X"`
2. Find alternatives: `@find-prompts "quick update"`
3. Get help when needed: `@prompt-help "devlog-summary"`

### Prompt Development
1. Create new prompt with metadata header
2. Update PROMPT-REGISTRY.md with new entry
3. Test functionality and relationships
4. Document in devlog using `@devlog-entry`

## Categories and Organization

### Current Categories

#### Documentation
- **Purpose**: Creating, updating, and managing project documentation
- **Prompts**: devlog-entry, devlog-summary, devlog-quick
- **Use Cases**: Progress tracking, session summaries, quick updates

#### Prompt Management
- **Purpose**: Discovering, managing, and getting help with prompts
- **Prompts**: find-prompts, list-prompts, prompt-help, related-prompts
- **Use Cases**: Prompt discovery, usage help, relationship mapping

### Future Categories (Examples)
- **Code Review**: Prompts for code analysis and review processes
- **Testing**: Prompts for test creation and validation
- **Project Management**: Prompts for planning and task management
- **Research**: Prompts for investigation and analysis work

## Maintenance and Evolution

### Adding New Prompts

1. **Create prompt file** with standardized metadata header
2. **Update PROMPT-REGISTRY.md** with new entry in appropriate category
3. **Test prompt functionality** to ensure it works as expected
4. **Update related prompts** if there are workflow connections
5. **Document in devlog** using comprehensive entry format

### Updating Existing Prompts

1. **Modify prompt content** as needed
2. **Update metadata header** (especially `updated` date and `related` field)
3. **Update PROMPT-REGISTRY.md** if description or usage changes
4. **Test functionality** to ensure changes work correctly
5. **Document changes** in devlog

### Organizing Categories

1. **Review prompt usage patterns** to identify natural groupings
2. **Create new categories** when you have 3+ related prompts
3. **Update PROMPT-REGISTRY.md** with new category descriptions
4. **Consider workflow connections** when organizing prompts

## Best Practices

### For Prompt Creation
1. **Use descriptive names** that clearly indicate purpose
2. **Include comprehensive metadata** for discoverability
3. **Write clear usage instructions** with examples
4. **Test thoroughly** before adding to registry
5. **Document relationships** with existing prompts

### For Discovery and Usage
1. **Start with `@list-prompts`** to get familiar with available options
2. **Use `@find-prompts`** when looking for specific functionality
3. **Get help with `@prompt-help`** when unsure about usage
4. **Explore `@related-prompts`** to discover workflow patterns
5. **Use the prompt-manager-agent** for complex queries

### For Maintenance
1. **Keep metadata current** when modifying prompts
2. **Update registry** when adding or removing prompts
3. **Review relationships** periodically to ensure accuracy
4. **Archive unused prompts** rather than deleting them
5. **Document changes** in devlog for tracking evolution

## Integration with Development Workflow

### With Devlog System
- Prompt management activities are automatically documented
- New prompts are tracked in devlog entries
- Usage patterns are recorded for optimization

### With Kiro CLI and IDE
- All prompts work in both CLI and IDE environments
- Agent switching available in both contexts
- Consistent experience across development tools

### With Team Collaboration
- Shared prompt library in version control
- Consistent metadata standards for team usage
- Documentation supports onboarding new team members

## Troubleshooting

### Common Issues

#### Prompt Not Found
- Check spelling in prompt name
- Use `@list-prompts` to see available options
- Use `@find-prompts` to search by keyword

#### Unclear Usage
- Use `@prompt-help "prompt-name"` for detailed instructions
- Check PROMPT-REGISTRY.md for quick reference
- Try `@related-prompts` to find similar options

#### Missing Relationships
- Update metadata headers with `related` field
- Update PROMPT-REGISTRY.md with connections
- Use prompt-manager-agent for relationship analysis

### Getting Help
- Use `@prompt-help` for specific prompt assistance
- Use `/agent swap prompt-manager-agent` for complex queries
- Check PROMPT-REGISTRY.md for quick reference
- Review this documentation for system understanding

## Future Enhancements

### Potential Improvements
- **Usage analytics**: Track which prompts are used most frequently
- **Auto-generation**: Scripts to automatically update registry
- **Version control integration**: Git hooks for prompt management
- **Template system**: Standardized templates for new prompt creation
- **Export capabilities**: Generate documentation from metadata

### Scalability Considerations
- **Subdirectory organization**: Organize prompts into subdirectories by category
- **Advanced search**: More sophisticated search and filtering capabilities
- **Workflow automation**: Automated prompt relationship detection
- **Integration APIs**: Programmatic access to prompt metadata

This system is designed to grow with your prompt library and provide comprehensive management capabilities as your custom prompt ecosystem evolves.