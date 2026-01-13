---
name: "git-commit-push"
category: "Development Workflow"
tags: ["git", "commit", "push", "version-control", "workflow"]
created: "2024-01-12"
updated: "2024-01-12"
usage: "Use this prompt to perform a complete git add, commit, and push workflow with properly structured commit messages"
relations: ["devlog-entry", "devlog-summary"]
description: "Comprehensive git workflow prompt that handles staging, committing with structured messages, and pushing to origin with error handling"
---

# Git Commit and Push Workflow

Perform a complete git workflow: add all changes, create a structured commit message, and push to origin main branch.

## Instructions

1. **Stage all changes**: Run `git add .` to stage all modified, new, and deleted files

2. **Create structured commit message** using this format:
   ```
   <type>: <brief description (50-72 chars)>
   
   <blank line>
   - <detailed change 1>
   - <detailed change 2>
   - <detailed change 3>
   - <detailed change 4>
   - <detailed change 5>
   - <detailed change 6>
   ```

3. **Commit message guidelines**:
   - **Type**: Use conventional commit types (feat, fix, docs, style, refactor, test, chore, config)
   - **Brief description**: 50-72 characters, imperative mood, no period
   - **Details**: 4-6 bullet points describing specific changes
   - **Length**: Keep total message moderate (not too long to avoid shell issues)
   - **Content**: Focus on what was implemented, configured, or changed

4. **Handle commit issues**:
   - If commit fails due to message length, break into shorter message
   - Avoid including text that might be misinterpreted as commands (like "docker-compose")
   - Use descriptive but concise language

5. **Push to origin**: Run `git push origin main` after successful commit

## Example Commit Message Structure

```
feat: Add comprehensive MyPy type checking configuration

- Added MyPy as development dependency via uv
- Implemented strict mode configuration in pyproject.toml
- Created comprehensive test script with advanced type patterns
- Fixed all type errors and achieved zero MyPy violations
- Added per-module configuration for tests, examples, and scripts
- Optimized for AI-generated code patterns with balanced strictness
```

## Error Handling

- **If git add fails**: Check for file permission issues or repository status
- **If commit fails**: 
  - Shorten commit message if too long
  - Remove any text that might be interpreted as shell commands
  - Break complex messages into simpler format
- **If push fails**: Check network connection and authentication status

## Success Criteria

- All changes staged successfully
- Commit created with structured message
- Changes pushed to origin main branch
- No errors in the git workflow

## Usage Notes

- Use this prompt after completing significant development work
- Ensure you're in the correct repository directory
- Review staged changes before committing if needed
- This workflow assumes you want to push to the main branch

## Integration

This prompt works well with:
- `@devlog-entry` for documenting what was committed
- `@devlog-summary` for session-level documentation
- Development workflow after completing features or configurations