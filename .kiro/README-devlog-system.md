# Devlog System Documentation

## Overview

This repository includes a comprehensive automated devlog system that combines Kiro agent specialization with steering rules to provide both automatic and manual development logging capabilities.

## System Components

### 1. Devlog Agent (`.kiro/agents/devlog-agent.json`)
- Specialized agent for creating comprehensive development log entries
- Uses Claude Sonnet 4 for superior analysis and writing capabilities
- Has access to project files and devlog guidelines
- Focuses on technical details, decisions, and long-term value

### 2. Steering Rules
- **`devlog-rules.md`**: Comprehensive formatting and quality guidelines
- **`auto-devlog.md`**: Automatic trigger reminders for progress updates

### 3. Prompt System
- **`@devlog-entry`**: Comprehensive manual entries with detailed format
- **`@devlog-summary`**: Complete session analysis and summary
- **`@devlog-quick`**: Streamlined updates for minor progress

## Usage Guide

### Automatic Updates
The system automatically reminds agents to update the devlog after significant progress through steering rules. When this happens, a comprehensive entry is created documenting:
- What was accomplished
- Technical details and approaches
- Decision rationale
- Challenges and solutions
- Impact and dependencies
- Next steps

### Manual Updates

#### Quick Entry
```
@devlog-quick Fixed authentication bug in login flow
```

#### Comprehensive Entry
```
@devlog-entry
```
Then provide details about what was accomplished.

#### Session Summary
```
@devlog-summary
```
Analyzes the entire conversation and creates a comprehensive summary.

#### Direct Agent Interaction
```
/agent swap devlog-agent
Please document the API integration work we just completed.
```

## Entry Format

All entries follow a comprehensive format including:

```markdown
## [YYYY-MM-DD HH:MM] - [CATEGORY]: [Brief Title]

### What Was Accomplished
[Detailed description of work completed]

### Technical Details
[Technologies, approaches, implementations]

### Decision Rationale
[Why decisions were made, alternatives considered]

### Challenges and Solutions
[Problems encountered and how they were resolved]

### Impact and Dependencies
[Effects on project, dependencies created/resolved]

### Next Steps
[Follow-up tasks and priorities]

### Resources and References
[Links, documentation, external resources]
```

## Categories

- **FEATURE**: New functionality implementation
- **BUGFIX**: Issue resolution and debugging
- **REFACTOR**: Code improvement and restructuring
- **CONFIG**: Setup, configuration, and tooling
- **DOCS**: Documentation creation and updates
- **TESTING**: Test implementation and validation
- **RESEARCH**: Investigation and analysis work
- **PLANNING**: Requirements and design work
- **INTEGRATION**: API integration and external services
- **PERFORMANCE**: Optimization and performance work
- **SECURITY**: Security implementation and improvements
- **DEPLOYMENT**: Release and deployment activities

## Best Practices

### For Comprehensive Documentation
1. **Be Specific**: Include concrete technical details
2. **Explain Decisions**: Document why choices were made
3. **Include Context**: Provide background and constraints
4. **Document Failures**: Failed approaches are valuable learning
5. **Think Long-term**: Write for future team members
6. **Stay Current**: Update promptly while details are fresh

### For Team Collaboration
1. **Use Consistent Format**: Follow the established structure
2. **Cross-reference**: Link related entries and resources
3. **Include Dependencies**: Note how work affects other areas
4. **Provide Next Steps**: Clear action items for follow-up

## Integration with Development Workflow

### With Kiro CLI
```bash
# Use devlog prompts
kiro-cli
> @devlog-summary

# Switch to devlog agent
kiro-cli --agent devlog-agent
```

### With Kiro IDE
- Prompts available in prompt panel
- Agent switching through UI
- Automatic steering rule integration

### With Git Workflow
- Devlog entries complement commit messages
- Provide higher-level context than individual commits
- Document decision-making process behind changes

## Maintenance

### Regular Review
- Periodically review entries for completeness
- Update entries with additional context as needed
- Archive older entries to maintain readability

### System Updates
- Refine prompts based on usage patterns
- Update steering rules as workflow evolves
- Enhance agent capabilities as needed

## Troubleshooting

### Common Issues
- **Entries too brief**: Use `@devlog-entry` instead of `@devlog-quick`
- **Missing technical details**: Reference devlog-rules.md for format
- **Inconsistent formatting**: Use the devlog agent for standardization

### Getting Help
- Review `devlog-rules.md` for detailed guidelines
- Use `/agent swap devlog-agent` for direct assistance
- Check existing entries in DEVLOG.md for examples

This system is designed to grow with your project and provide valuable documentation that serves both current development and future maintenance needs.