# Automatic Devlog Updates

## Development Progress Tracking

After completing any significant development work, you should update the project's DEVLOG.md file with a comprehensive entry documenting the progress made.

## When to Update the Devlog

Update the devlog automatically when you have completed:

### Implementation Work
- New features or components
- Bug fixes or issue resolution
- Code refactoring or improvements
- API implementations or integrations
- Database schema changes or migrations
- Performance optimizations
- Security implementations

### Configuration and Setup
- Development environment setup
- Tool configuration or installation
- CI/CD pipeline setup or modifications
- Deployment configuration changes
- Testing framework setup

### Planning and Design
- Requirements analysis or specification updates
- Architecture decisions or design documents
- Research completion or technology evaluations
- Project structure or organization changes

### Documentation and Process
- Significant documentation updates
- Process improvements or workflow changes
- Code review completion with major changes

## How to Update the Devlog

1. **Use the devlog agent** by calling `/agent swap devlog-agent` or referencing it in your response
2. **Follow the comprehensive format** specified in devlog-rules.md
3. **Be thorough and detailed** - include technical details, decisions, and context
4. **Focus on value** - document information that will be useful for future reference
5. **INSERT AT TOP** - New entries MUST be added at the top of the file, immediately after the "## Recent Activity" header (newest first, oldest last)

## Automatic Trigger Reminder

When you complete significant work in a session, remind yourself to update the devlog by including a note like:

"I should update the DEVLOG.md with details about this work. Let me create a comprehensive entry documenting what was accomplished."

Then proceed to create or update the devlog entry with thorough documentation of the progress made.

## Integration with Workflow

This automatic devlog updating should feel natural and integrated into the development workflow, not like an additional burden. The goal is to capture valuable progress and insights while they're fresh in memory.