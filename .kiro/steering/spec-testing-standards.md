---
inclusion: auto
---

# Spec Testing Standards

Every requirements.md created via the spec workflow MUST include dedicated testing and validation requirements. These are non-negotiable and must appear as explicit requirements (not just implied by code-standards.md).

## Required Testing Requirements in Every Spec

### 1. Backend Testing Requirement
Every spec with backend changes MUST include a requirement covering:
- Unit tests (`@pytest.mark.unit`) for all new services, repositories, and utilities with mocked dependencies
- Functional tests (`@pytest.mark.functional`) for user workflows with real DB
- Integration tests (`@pytest.mark.integration`) for cross-component flows
- Property-based tests (Hypothesis) for business logic with invariants (e.g., job generation counts, status transitions, financial calculations)

### 2. Frontend Testing Requirement
Every spec with frontend changes MUST include a requirement covering:
- Component tests (Vitest + React Testing Library) for all new components
- Hook tests for all custom hooks
- Form validation tests for all new forms
- Loading, error, and empty state coverage

### 3. Agent-Browser UI Validation Requirement
Every spec with frontend UI changes MUST include a requirement covering end-to-end UI validation using Vercel Agent Browser (`agent-browser`). The requirement should specify:
- Navigation validation: verify new tabs/pages are accessible and render correctly
- Interactive element validation: verify buttons, forms, filters, and modals function correctly
- Data display validation: verify tables, lists, charts, and KPI cards render with correct data
- Responsive state validation: verify loading states, empty states, and error states display properly
- Cross-component navigation: verify links between related views work (e.g., agreement detail → customer detail)

Example acceptance criteria pattern:
```
WHEN the Admin navigates to the [feature] page, agent-browser SHALL verify:
- The page loads without errors (snapshot confirms expected elements present)
- Interactive elements (buttons, filters, tabs) respond to clicks
- Data tables render with correct columns and data
- Form submissions produce expected success/error states
- Navigation between related views works correctly
```

### 4. Linting and Type Safety Requirement
Every spec MUST include a requirement that:
- All new backend code passes `ruff check`, `ruff format`, `mypy`, and `pyright` with zero errors
- All new frontend code passes ESLint and TypeScript strict mode with zero errors

### 5. Quality Gate Requirement
Every spec MUST include a final requirement that serves as a quality gate:
- All tests pass (unit, functional, integration, property-based, component)
- All linting and type checking passes with zero errors
- Agent-browser validation scripts pass for all new/modified UI
- Test coverage meets targets (services 90%+, components 80%+, hooks 85%+)
