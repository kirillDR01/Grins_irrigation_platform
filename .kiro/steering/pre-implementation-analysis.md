# Pre-Implementation Analysis

Before executing spec tasks or "run all tasks", complete this analysis.

## Checklist
1. **MCP Servers**: List installed (`kiroPowers` action="list"). Need external docs, DB, or testing servers?
2. **Powers**: List installed powers. Any keyword matches for planned work?
3. **Parallel Execution**: Read tasks.md. Identify independent tasks → parallelize. Common: models in parallel after migrations, independent API endpoints, independent services.
4. **Subagents**: `spec-task-execution` (spec tasks), `context-gatherer` (understand code), `general-task-execution` (arbitrary tasks). Plan delegation.
5. **Custom Prompts**: Check `.kiro/prompts/`. Key: `@implement-migration`, `@next-task`, `@checkpoint`, `@feature-complete-check`
6. **Custom Agents**: Check `.kiro/agents/`. Available: api-layer, service-layer, repository-layer, test-specialist, quality-checker.

## Output
Summarize: which MCP servers, powers, parallel groups, subagent assignments, prompts, agents to use. Present to user before starting.
