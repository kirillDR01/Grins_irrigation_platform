# Prompt Registry

**Last Updated**: 2025-01-19  
**Total Prompts**: 37  
**Categories**: 10

## Overview

This registry catalogs all available prompts in the Kiro CLI environment. Prompts are organized by category and include metadata for easy discovery and usage.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `@list-prompts` | Browse all prompts by category |
| `@find-prompts "keyword"` | Search for prompts by keyword or category |
| `@prompt-help "name"` | Get detailed help for a specific prompt |
| `@related-prompts "name"` | Find related prompts |
| `@update-prompt-registry` | Regenerate this registry |

---

## All Prompts

| Name | Category | Description | Usage |
|------|----------|-------------|-------|
| add-logging | Code Quality | Add structured logging to existing code | `@add-logging [file or module]` |
| add-tests | Code Quality | Generate comprehensive test suite for existing code | `@add-tests [file or module to test]` |
| checkpoint | Workflow Automation | Save progress: run quality checks, update devlog, and commit | `@checkpoint [optional description]` |
| code-review | Code Review | Technical code review for quality and bugs that runs pre-commit | `@code-review` |
| code-review-fix | Code Review | Process to fix bugs found in manual/AI code review | `@code-review-fix` |
| code-review-hackathon | Code Review | Comprehensive hackathon submission review based on official judging criteria | `@code-review-hackathon` |
| create-prd | Documentation | Create a Product Requirements Document from conversation | `@create-prd [output-filename]` |
| devlog-entry | Documentation | Create comprehensive devlog entries with detailed technical information | `@devlog-entry [optional description]` |
| devlog-quick | Documentation | Create streamlined devlog entries for quick progress updates | `@devlog-quick "brief description"` |
| devlog-summary | Documentation | Analyze entire conversation and create comprehensive session summary | `@devlog-summary` |
| execute | Development Workflow | Execute an implementation plan | `@execute [path-to-plan]` |
| execution-report | Development Workflow | Generate implementation report for system review | `@execution-report` |
| feature-complete-check | Workflow Automation | Verify a feature meets Definition of Done before marking complete | `@feature-complete-check [feature-name]` |
| find-prompts | Prompt Management | Search for prompts by keyword, category, or purpose | `@find-prompts "keyword or category"` |
| git-commit-push | Development Workflow | Git workflow: staging, committing with structured messages, and pushing | `@git-commit-push` |
| hackathon-status | Hackathon | Generate comprehensive status report for hackathon submission | `@hackathon-status` |
| implement-api | Spec Implementation | Implement FastAPI endpoint following Grins Platform patterns | `@implement-api` |
| implement-exception | Spec Implementation | Implement custom exceptions following Grins Platform patterns | `@implement-exception` |
| implement-fix | Development Workflow | Implement fix from RCA document for GitHub issue | `@implement-fix [github-issue-id]` |
| implement-migration | Spec Implementation | Generate Alembic migration from design document schema | `@implement-migration [table-name]` |
| implement-pbt | Spec Implementation | Implement property-based test following Grins Platform patterns | `@implement-pbt` |
| implement-service | Spec Implementation | Implement service layer method following Grins Platform patterns | `@implement-service` |
| list-prompts | Prompt Management | Display all available prompts organized by category | `@list-prompts [optional category]` |
| new-feature | Development | Create a complete feature with automatic testing and logging | `@new-feature [feature description]` |
| next-task | Workflow Automation | Find and execute the next incomplete task from the active spec | `@next-task [optional spec-name]` |
| parallel-tasks | Analysis | Identify parallel task opportunities and dependencies | `@parallel-tasks` |
| plan-feature | Planning | Create comprehensive feature plan with deep codebase analysis | `@plan-feature [feature description]` |
| prime | Setup | Load Project Context and understand codebase | `@prime` |
| prompt-help | Prompt Management | Get detailed help and usage instructions for a specific prompt | `@prompt-help "prompt-name"` |
| quality-check | Code Quality | Run all quality checks and fix any issues found | `@quality-check [optional: specific file or directory]` |
| quickstart | Setup | Kiro CLI Quick Start Wizard | `@quickstart` |
| rca | Analysis | Analyze and document root cause for a GitHub issue | `@rca [github-issue-id]` |
| related-prompts | Prompt Management | Find prompts related to or work well with a specific prompt | `@related-prompts "prompt-name"` |
| system-review | Analysis | Analyze implementation against plan for process improvements | `@system-review` |
| task-progress | Analysis | Analyze current task progress and provide recommendations | `@task-progress` |
| update-prompt-registry | Prompt Management | Automatically scan prompts directory and regenerate PROMPT-REGISTRY.md | `@update-prompt-registry` |

---

## Categories

### Analysis (4 prompts)
Prompts for analyzing code, processes, tasks, and issues.

- **parallel-tasks**: Identify parallel task opportunities and dependencies
- **rca**: Analyze and document root cause for a GitHub issue
- **system-review**: Analyze implementation against plan for process improvements
- **task-progress**: Analyze current task progress and provide recommendations

### Code Quality (3 prompts)
Prompts for code quality, testing, and logging.

- **add-logging**: Add structured logging to existing code
- **add-tests**: Generate comprehensive test suite for existing code
- **quality-check**: Run all quality checks and fix any issues found

### Code Review (3 prompts)
Prompts for reviewing code quality, bugs, and standards.

- **code-review**: Technical code review for quality and bugs that runs pre-commit
- **code-review-fix**: Process to fix bugs found in manual/AI code review
- **code-review-hackathon**: Comprehensive hackathon submission review based on official judging criteria

### Development (1 prompt)
Prompts for feature development.

- **new-feature**: Create a complete feature with automatic testing and logging

### Development Workflow (4 prompts)
Prompts for managing development workflows and git operations.

- **execute**: Execute an implementation plan
- **execution-report**: Generate implementation report for system review
- **git-commit-push**: Git workflow: staging, committing with structured messages, and pushing
- **implement-fix**: Implement fix from RCA document for GitHub issue

### Documentation (4 prompts)
Prompts for creating and maintaining project documentation.

- **create-prd**: Create a Product Requirements Document from conversation
- **devlog-entry**: Create comprehensive devlog entries with detailed technical information
- **devlog-quick**: Create streamlined devlog entries for quick progress updates
- **devlog-summary**: Analyze entire conversation and create comprehensive session summary

### Hackathon (1 prompt)
Prompts for hackathon-specific workflows and status tracking.

- **hackathon-status**: Generate comprehensive status report for hackathon submission

### Planning (1 prompt)
Prompts for planning features and implementations.

- **plan-feature**: Create comprehensive feature plan with deep codebase analysis

### Prompt Management (5 prompts)
Prompts for discovering and managing other prompts.

- **find-prompts**: Search for prompts by keyword, category, or purpose
- **list-prompts**: Display all available prompts organized by category
- **prompt-help**: Get detailed help and usage instructions for a specific prompt
- **related-prompts**: Find prompts related to or work well with a specific prompt
- **update-prompt-registry**: Automatically scan prompts directory and regenerate PROMPT-REGISTRY.md

### Setup (2 prompts)
Prompts for initial project setup and configuration.

- **prime**: Load Project Context and understand codebase
- **quickstart**: Kiro CLI Quick Start Wizard

### Spec Implementation (5 prompts)
Prompts for implementing code from spec documents.

- **implement-api**: Implement FastAPI endpoint following Grins Platform patterns
- **implement-exception**: Implement custom exceptions following Grins Platform patterns
- **implement-migration**: Generate Alembic migration from design document schema
- **implement-pbt**: Implement property-based test following Grins Platform patterns
- **implement-service**: Implement service layer method following Grins Platform patterns

### Workflow Automation (3 prompts)
Prompts for automating development workflows and task management.

- **checkpoint**: Save progress: run quality checks, update devlog, and commit
- **feature-complete-check**: Verify a feature meets Definition of Done before marking complete
- **next-task**: Find and execute the next incomplete task from the active spec

---

## Usage Patterns

### Discovery Workflow
1. `@list-prompts` - Browse all available prompts
2. `@find-prompts "keyword"` - Search for specific functionality
3. `@prompt-help "name"` - Get detailed usage instructions
4. `@related-prompts "name"` - Find complementary prompts

### Development Workflow
1. `@plan-feature` - Plan new feature implementation
2. `@execute` - Execute the implementation plan
3. `@quality-check` - Validate code quality
4. `@git-commit-push` - Commit and push changes
5. `@devlog-entry` - Document the work

### Spec-Driven Workflow
1. `@next-task` - Find and start the next task from tasks.md
2. `@implement-migration` - Generate migration from design doc
3. `@implement-service` - Implement service layer
4. `@implement-api` - Implement API endpoints
5. `@implement-pbt` - Add property-based tests
6. `@checkpoint` - Save progress (quality + devlog + commit)
7. `@feature-complete-check` - Verify feature is done

### Quality Workflow
1. `@new-feature` - Create feature with built-in quality
2. `@add-tests` - Add comprehensive tests
3. `@add-logging` - Add structured logging
4. `@quality-check` - Run all quality checks

### Issue Resolution Workflow
1. `@rca` - Analyze root cause of issue
2. `@implement-fix` - Implement the fix
3. `@execution-report` - Document implementation
4. `@system-review` - Review process improvements

### Hackathon Workflow
1. `@hackathon-status` - Check progress against criteria
2. `@next-task` - Continue implementation
3. `@checkpoint` - Save progress regularly
4. `@feature-complete-check` - Verify features are done
5. `@code-review-hackathon` - Final submission review

---

## Maintenance

### Updating This Registry

Run `@update-prompt-registry` to automatically:
- Scan all prompt files in `.kiro/prompts/`
- Extract metadata from YAML frontmatter
- Organize prompts by category
- Regenerate this file with current information

### Adding New Prompts

1. Create new `.md` file in `.kiro/prompts/`
2. Include YAML frontmatter with required metadata:
   ```yaml
   ---
   name: prompt-name
   category: Category Name
   tags: [tag1, tag2, tag3]
   description: Brief description
   created: YYYY-MM-DD
   updated: YYYY-MM-DD
   usage: "@prompt-name [arguments]"
   related: [other-prompt, another-prompt]
   ---
   ```
3. Run `@update-prompt-registry` to update this file

---

## Statistics

- **Total Prompts**: 37
- **Categories**: 10
- **Most Common Category**: Prompt Management, Spec Implementation (5 prompts each)
- **Last Registry Update**: 2025-01-19

---

*This registry is automatically generated. Do not edit manually. Use `@update-prompt-registry` to update.*
