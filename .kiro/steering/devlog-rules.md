# Development Log Guidelines

## Purpose
The development log serves as a comprehensive record of project progress, decisions, and insights. It should be detailed enough for team members, future developers, or project stakeholders to understand the evolution of the project.

## Auto-Update Triggers
After completing any of these activities, update the DEVLOG.md with a comprehensive entry:

### Major Development Activities
- Implementing new features or major components
- Completing significant refactoring or architectural changes
- Resolving complex bugs or technical challenges
- Making important architectural or technology decisions
- Completing testing phases or implementing new testing strategies
- Setting up new tools, configurations, or development workflows
- Completing integration work or API implementations
- Performance optimizations or security improvements

### Planning and Design Activities
- Completing requirements gathering or specification updates
- Finishing design documents or architectural planning
- Completing user research or technical research
- Making technology stack decisions
- Completing project setup or environment configuration

### Collaboration and Process Activities
- Code reviews that result in significant changes
- Team meetings that result in important decisions
- Documentation updates or knowledge sharing sessions
- Process improvements or workflow optimizations

## Comprehensive Entry Format

Use this detailed format for all devlog entries:

```markdown
## [YYYY-MM-DD HH:MM] - [CATEGORY]: [Brief Title]

### What Was Accomplished
[Detailed description of what was completed, including:]
- Specific features implemented
- Problems solved
- Code written or modified
- Tools configured
- Tests created

### Technical Details
[Include relevant technical information:]
- Technologies/frameworks used
- Key algorithms or approaches implemented
- Database changes or API modifications
- Performance considerations
- Security implications

### Decision Rationale
[Explain the reasoning behind key decisions:]
- Why this approach was chosen over alternatives
- Trade-offs considered
- Constraints that influenced decisions
- Research or analysis that informed choices

### Challenges and Solutions
[Document any obstacles encountered:]
- Problems faced during implementation
- How issues were resolved
- Lessons learned
- What would be done differently

### Impact and Dependencies
[Describe the broader implications:]
- How this affects other parts of the system
- Dependencies created or resolved
- Breaking changes or compatibility considerations
- Impact on project timeline or scope

### Next Steps
[Clear action items and future work:]
- Immediate follow-up tasks
- Related work that should be prioritized
- Potential improvements or optimizations
- Areas that need further investigation

### Resources and References
[Include relevant links and references:]
- Documentation consulted
- Stack Overflow solutions used
- GitHub issues or PRs related
- External libraries or tools integrated
```

## Entry Categories

Use these categories to organize entries:

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

## Entry Ordering (CRITICAL)

**New entries MUST be added at the TOP of the DEVLOG.md file, immediately after the "## Recent Activity" header.**

- The DEVLOG is organized with newest entries first, oldest entries last
- When adding a new entry, insert it directly below the "## Recent Activity" line
- Do NOT append entries to the bottom of the file
- This ensures the most recent work is always visible first when opening the file

### Insertion Point
```markdown
# Development Log

## Project Overview
[Header content...]

## Recent Activity

## [NEW ENTRY GOES HERE] - [CATEGORY]: [Title]
...

## [Previous Entry] - [CATEGORY]: [Title]
...
```

---

## Quality Standards

### Comprehensive Coverage
- Include enough detail for someone unfamiliar with the project to understand the work
- Explain not just what was done, but why and how
- Document both successful approaches and failed attempts
- Include code snippets, commands, or configurations when relevant

### Technical Accuracy
- Use precise technical terminology
- Include version numbers for tools and libraries
- Document exact commands or procedures used
- Reference specific files, functions, or components modified

### Future Value
- Write entries that will be valuable weeks or months later
- Include context that might be forgotten over time
- Document workarounds and their reasons
- Note potential areas for future improvement

### Consistency
- Use consistent formatting and structure
- Maintain chronological order
- Use clear, professional language
- Include timestamps for all entries

## Integration with Development Workflow

### Automatic Updates
- Steering rules will remind agents to update the devlog after significant progress
- The devlog agent will analyze recent work and create comprehensive entries
- Updates should happen at natural breakpoints in development work

### Manual Updates
- Use dedicated prompts for quick manual entries
- Session summary prompts for comprehensive end-of-session updates
- Direct agent interaction for detailed custom entries

### Review and Maintenance
- Periodically review entries for completeness and accuracy
- Update entries with additional context as projects evolve
- Archive older entries to maintain readability

## Best Practices

1. **Be Specific**: Include concrete details rather than vague descriptions
2. **Include Context**: Explain the broader situation and constraints
3. **Document Failures**: Failed approaches are as valuable as successful ones
4. **Think Long-term**: Write for future team members and your future self
5. **Stay Current**: Update entries promptly while details are fresh
6. **Cross-reference**: Link related entries and external resources
7. **Maintain Flow**: Ensure entries build on each other logically