# Quality Reminder Hook

This hook displays quality standards at the start of each agent session.

## Configuration

To enable this hook, add to your agent configuration or use Kiro's hook UI.

## Trigger
- **Event**: Agent Spawn (when a new session starts)

## Action
Display the following reminder:

```
╔══════════════════════════════════════════════════════════════╗
║                    QUALITY STANDARDS                         ║
╠══════════════════════════════════════════════════════════════╣
║  Every task MUST include:                                    ║
║                                                              ║
║  1. LOGGING                                                  ║
║     • LoggerMixin for classes                                ║
║     • log_started, log_completed, log_failed                 ║
║     • Pattern: {domain}.{component}.{action}_{state}         ║
║                                                              ║
║  2. TESTING                                                  ║
║     • Unit tests for public methods                          ║
║     • Integration tests for workflows                        ║
║     • Tests in tests/test_{module}.py                        ║
║                                                              ║
║  3. QUALITY CHECKS                                           ║
║     • uv run ruff check --fix src/                           ║
║     • uv run mypy src/                                       ║
║     • uv run pyright src/                                    ║
║     • uv run pytest -v                                       ║
║                                                              ║
║  Task is NOT complete until all checks pass with zero errors ║
╚══════════════════════════════════════════════════════════════╝
```

## Purpose

This reminder ensures that quality standards are top-of-mind at the start of every development session. It reinforces the "Quality by Default" philosophy.

## Notes

- This is a passive reminder, not an enforcement mechanism
- The actual enforcement comes from the steering files and workflow
- Consider this a "gentle nudge" to follow best practices
