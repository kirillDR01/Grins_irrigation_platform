# Parallel Execution Strategy

## Dependency Pattern (Customer Management example)
```
Phase 1 (sequential): DB Setup → Models → Schemas → Repositories
Phase 2 (parallel):   CustomerService | PropertyService | Exceptions
Phase 3 (sequential): Service Tests (needs all services)
Phase 4 (parallel):   Customer CRUD API | Customer Ops API | Property API
Phase 5 (sequential): Integration Tests → PBT Tests → Documentation
```

## Rules
- Sequential phases complete before next starts
- Within a phase, independent tasks run as parallel subagents
- After parallel phase, run tests sequentially

## Subagent Pattern
```
Main Agent:
1. Queue independent tasks to separate subagents
2. Wait for all to complete
3. Run tests (test-specialist-agent)
4. Run quality checks (quality-checker-agent)
```

Estimated savings: 40-55% vs fully sequential.
