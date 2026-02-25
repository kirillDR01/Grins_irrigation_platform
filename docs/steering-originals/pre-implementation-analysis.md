# Pre-Implementation Tooling Analysis

## Purpose

Before executing any spec tasks or running "run all tasks", the agent MUST complete a tooling analysis to identify opportunities for efficiency gains through Kiro's advanced features.

## When This Applies

This analysis is REQUIRED before:
- Starting task execution on any spec
- Running "run all tasks" command
- Beginning a new implementation phase
- Starting work on a new feature

## Mandatory Analysis Checklist

### 1. MCP Servers Assessment

**Check for useful MCP servers:**
- [ ] List currently installed MCP servers using `kiroPowers` tool with action="list"
- [ ] Identify if any external documentation servers would help (AWS docs, library docs, etc.)
- [ ] Determine if database or API testing MCP servers would be beneficial
- [ ] Check if any code generation or analysis MCP servers are available

**Questions to answer:**
- Are there MCP servers that could provide documentation for libraries we're using?
- Are there MCP servers that could help with database operations?
- Are there MCP servers that could assist with testing or validation?

**Action:** Document which MCP servers to activate and why, or confirm none are needed.

### 2. Powers Assessment

**Check for useful Powers:**
- [ ] List installed Kiro Powers using `kiroPowers` tool
- [ ] Review power keywords against the planned work
- [ ] Identify if any powers match the implementation domain

**Questions to answer:**
- Do any installed powers have keywords matching our work (e.g., "database", "api", "testing")?
- Should any new powers be installed for this phase?
- Which powers should be activated before starting?

**Action:** Activate relevant powers or confirm none are applicable.

### 3. Parallel Execution Opportunities

**Analyze task dependencies:**
- [ ] Read the tasks.md file for the spec
- [ ] Identify tasks that have NO dependencies on each other
- [ ] Create a dependency graph showing parallelization opportunities
- [ ] Estimate time savings from parallel execution

**Common parallel patterns:**
- Database migrations can run sequentially, but models can be created in parallel after
- Service layer components with no shared dependencies can be parallel
- API endpoints for different resources can be parallel
- Tests can often run in parallel

**Action:** Document which tasks can be parallelized and the expected time savings.

### 4. Subagent Strategy

**Identify specialized subagents:**
- [ ] Review available subagents: `spec-task-execution`, `context-gatherer`, `general-task-execution`
- [ ] Determine which tasks benefit from subagent delegation
- [ ] Define clear boundaries for each subagent's responsibilities
- [ ] Plan handoff points between subagents

**Subagent selection criteria:**
- `spec-task-execution`: For executing individual spec tasks with PBT support
- `context-gatherer`: For understanding unfamiliar code before making changes
- `general-task-execution`: For arbitrary tasks not tied to specs

**Action:** Document subagent invocation strategy.

### 5. Custom Prompts Assessment

**Check for applicable prompts:**
- [ ] Review `.kiro/prompts/` for relevant prompts
- [ ] Identify prompts that match the planned work
- [ ] Consider if new prompts should be created

**Key prompts for implementation:**
- `@implement-migration` - For database migrations
- `@next-task` - For task-by-task execution
- `@checkpoint` - For saving progress
- `@feature-complete-check` - For verification

**Action:** List prompts to use during implementation.

### 6. Custom Agents Assessment

**Check for applicable agents:**
- [ ] Review `.kiro/agents/` for specialized agents
- [ ] Identify agents that match the planned work
- [ ] Consider if new agents should be created

**Available agents:**
- `api-layer-agent` - For API endpoint implementation
- `service-layer-agent` - For service layer implementation
- `repository-layer-agent` - For repository implementation
- `test-specialist-agent` - For test creation
- `quality-checker-agent` - For quality validation

**Action:** Document which agents to use for which tasks.

## Output Format

After completing the analysis, produce a summary:

```markdown
## Pre-Implementation Analysis Summary

### MCP Servers
- **Status:** {None needed / Activating X servers}
- **Servers:** {List if any}
- **Rationale:** {Why these servers help}

### Powers
- **Status:** {None needed / Activating X powers}
- **Powers:** {List if any}
- **Rationale:** {Why these powers help}

### Parallel Execution
- **Parallelizable Tasks:** {List task groups}
- **Estimated Time Savings:** {X%}
- **Dependency Graph:** {Brief description}

### Subagent Strategy
- **Primary Subagent:** {spec-task-execution / other}
- **Delegation Plan:** {Which tasks to delegate}

### Custom Prompts
- **Prompts to Use:** {List}

### Custom Agents
- **Agents to Use:** {List with task assignments}

### Recommendation
{Summary of the optimal execution strategy}
```

## Integration with Task Execution

When the user requests "run all tasks" or starts task execution:

1. **FIRST**: Complete this pre-implementation analysis
2. **THEN**: Present the analysis summary to the user
3. **THEN**: Ask if the user wants to proceed with the recommended strategy
4. **FINALLY**: Begin task execution using the identified tools and strategies

## Example Analysis for Field Operations

```markdown
## Pre-Implementation Analysis: Field Operations

### MCP Servers
- **Status:** None needed
- **Rationale:** All work is internal Python/FastAPI development

### Powers
- **Status:** None needed
- **Rationale:** Standard development patterns sufficient

### Parallel Execution
- **Parallelizable Tasks:**
  - Service Catalog (Tasks 1.1, 2.2, 3.1, 4.1, 6.x, 11.x)
  - Staff Management (Tasks 1.4, 2.5, 3.3, 4.4, 8.x, 13.x)
  - These have NO dependencies on each other
- **Estimated Time Savings:** 30-40%

### Subagent Strategy
- **Primary Subagent:** spec-task-execution
- **Delegation Plan:** 
  - Subagent A: Service Catalog tasks
  - Subagent B: Staff Management tasks
  - Main agent: Job Management (depends on Service Catalog)

### Custom Prompts
- `@implement-migration` for Tasks 1.1-1.4
- `@checkpoint` after each major milestone
- `@feature-complete-check` at end

### Custom Agents
- `service-layer-agent` for Tasks 6.x, 7.x, 8.x
- `api-layer-agent` for Tasks 11.x, 12.x, 13.x
- `test-specialist-agent` for Tasks 15.x, 16.x

### Recommendation
Execute Service Catalog and Staff Management in parallel using subagents,
then execute Job Management sequentially (depends on Service Catalog).
Use specialized agents for each layer. Estimated 35% time savings.
```

## Enforcement

This steering document ensures that:
1. Agents don't miss efficiency opportunities
2. Kiro's advanced features are utilized
3. Parallel execution is considered
4. The hackathon showcases Kiro's capabilities
