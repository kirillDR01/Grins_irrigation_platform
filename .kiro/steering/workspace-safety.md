# Workspace Safety Rules

## Purpose

This steering document enforces workspace boundaries for autonomous agent execution, particularly important when running in Autopilot mode or executing Ralph Wiggum-style autonomous loops.

## Workspace Boundaries (MANDATORY)

### File Operations

All file operations MUST be restricted to the current workspace:

1. **Use Relative Paths Only**
   - Always use paths relative to workspace root
   - Never use absolute paths starting with `/` or `~`
   - Example: `src/grins_platform/` NOT `/Users/username/project/src/`

2. **Never Write Outside Workspace**
   - All `fsWrite`, `strReplace`, `fsAppend` operations must target workspace files
   - Never create files in parent directories (`../`)
   - Never write to system directories

3. **Never Read Sensitive Files**
   - `~/.ssh/**` - SSH keys and config
   - `~/.aws/**` - AWS credentials
   - `~/.kiro/settings/**` - Global Kiro settings (read workspace `.kiro/` instead)
   - `~/.env` or any `.env` outside workspace
   - `/etc/**` - System configuration
   - Any file outside the workspace root

### Command Execution

1. **Allowed Commands**
   - Package managers: `uv`, `npm`, `pip` (within workspace)
   - Quality tools: `ruff`, `mypy`, `pyright`, `pytest`
   - Build tools: `vite`, `tsc`, `alembic`
   - Git: `git status`, `git diff`, `git add`, `git commit` (no push without permission)
   - Docker: `docker-compose up/down` for local development only

2. **Forbidden Commands**
   - `sudo` anything
   - `rm -rf /` or any destructive system commands
   - `chmod` on files outside workspace
   - `curl | bash` or piped execution from internet
   - Any command that modifies files outside workspace
   - `git push` without explicit user permission

3. **Command Working Directory**
   - Always execute commands from workspace root
   - Use `cwd` parameter to specify subdirectories within workspace
   - Never `cd` to directories outside workspace

### Network Operations

1. **Allowed**
   - Localhost connections (127.0.0.1, localhost)
   - Package registry fetches (npm, pypi)
   - Documentation lookups

2. **Restricted**
   - External API calls should be logged
   - No credential transmission without user awareness

## Autonomous Execution Safety

### Ralph Wiggum Loop Specific Rules

When executing autonomous loops:

1. **Scope Verification**
   - Before each task, verify target files are within workspace
   - Log all file modifications to activity.md
   - Never modify files outside `.kiro/specs/{feature}/` and `src/` directories

2. **Checkpoint Enforcement**
   - Always pause at checkpoint tasks
   - Allow user to review changes before continuing
   - Use `git status` to show modified files

3. **Rollback Capability**
   - All changes should be git-trackable
   - User can always `git checkout .` to revert
   - Never make changes that can't be undone

### Pre-Execution Checklist

Before any autonomous task:
- [ ] Target path is relative to workspace
- [ ] No sensitive files will be accessed
- [ ] No system files will be modified
- [ ] Command won't affect files outside workspace
- [ ] Changes are reversible via git

## Verification Commands

Use these to verify workspace safety:

```bash
# Check what files have been modified
git status

# Review all changes
git diff

# Verify no files outside workspace
git status --porcelain | grep -v "^??" | cut -c4-

# Revert all changes if needed
git checkout .
```

## Incident Response

If workspace boundaries are violated:

1. **Stop immediately** - Do not continue execution
2. **Report to user** - Explain what happened
3. **Assess damage** - List any files modified outside workspace
4. **Provide recovery steps** - How to undo the changes

## Integration with Other Steering

This document takes precedence over other steering documents when there's a conflict regarding file access or command execution. Safety boundaries are non-negotiable.
