---
inclusion: fileMatch
fileMatchPattern: '*specs*{requirements,design,tasks}*'
---

# Spec Quality Gates

When creating or updating requirements.md or design.md for any spec, the following sections MUST be included. These are mandatory project standards that apply to every feature.

## Requirements Document Must Include

Every requirements.md MUST include requirements for:

1. **Code Quality Gates** — Ruff linting (zero violations), Ruff formatting (88 char lines), MyPy (zero errors), Pyright (zero errors), type hints on all functions, PEP 8 via Ruff, Google-style docstrings
2. **Structured Logging** — LoggerMixin with DOMAIN for services/repositories, get_logger() for utilities, DomainLogger.api_event() with request_id correlation for API endpoints, event naming pattern `{domain}.{component}.{action}_{state}`, never log secrets/tokens/PII
3. **Three-Tier Testing** — Unit tests in `tests/unit/` with `@pytest.mark.unit` (all mocked), functional tests in `tests/functional/` with `@pytest.mark.functional` (real DB), integration tests in `tests/integration/` with `@pytest.mark.integration` (full system), test naming conventions, shared fixtures in conftest.py
4. **Frontend Testing and data-testid Conventions** — data-testid attributes following `{feature}-page`, `{feature}-table`, `{feature}-row`, `{action}-{feature}-btn`, `nav-{feature}`, `status-{value}` convention; co-located test files; coverage targets (Components 80%+, Hooks 85%+, Utils 90%+); Vitest + React Testing Library with QueryProvider wrapper
5. **Agent-Browser E2E Validation** — Validation scripts for key user workflows using agent-browser commands (open, wait, click, fill, is visible, close)
6. **Cross-Feature Integration and Backward Compatibility** — Integration tests verifying the feature works with existing components, migration backward compatibility, schema serialization compatibility
7. **Security** — No logging of secrets/tokens/credentials, admin auth on protected endpoints, input sanitization, secure credential storage

## Design Document Must Include

Every design.md MUST include sections for:

1. **Structured Logging Events** — Complete table of log events per component with event name, level, and context fields following `{domain}.{component}.{action}_{state}` pattern
2. **data-testid Convention Map** — Table mapping every frontend element to its data-testid value
3. **agent-browser Validation Scripts** — Concrete bash scripts for each key user workflow
4. **Quality Gate Commands** — The exact bash commands to run for linting, type checking, and testing
5. **Test Fixtures** — Concrete fixture definitions for conftest.py (sample data, factories, mocks)
6. **Coverage Targets** — Table of coverage targets per layer (backend unit 90%+, frontend components 80%+, hooks 85%+, utils 90%+)
7. **Cross-Feature Integration Tests** — Table of integration test names and descriptions
8. **Security Considerations** — Credential handling, token storage, auth requirements, input sanitization

## Reference Steering Files

These project steering files define the standards that specs must incorporate:
- `code-standards.md` — Logging, testing tiers, type safety, quality commands
- `tech.md` — Stack, quality checks, testing tiers, performance targets
- `frontend-testing.md` — Vitest + RTL patterns, agent-browser scripts, coverage targets
- `frontend-patterns.md` — data-testid conventions, component patterns, TanStack Query
- `api-patterns.md` — Endpoint template with request_id correlation, DomainLogger usage
- `agent-browser.md` — Command reference for E2E validation
