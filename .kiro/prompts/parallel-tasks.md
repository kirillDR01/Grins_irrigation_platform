# Identify Parallel Task Opportunities

Analyze tasks to find opportunities for parallel execution.

## Analysis Process

1. Read the tasks.md file
2. For each incomplete task, identify:
   - Input dependencies (what must exist first)
   - Output artifacts (what it creates)
   - Shared resources (files it modifies)

3. Group tasks that:
   - Have no dependencies on each other
   - Don't modify the same files
   - Can be validated independently

## Parallel Grouping Template

### Group A (Can run together)
- Task X.Y: {description} - Creates {artifact}
- Task X.Z: {description} - Creates {artifact}
- Reason: No shared dependencies

### Group B (Must be sequential)
- Task X.Y → Task X.Z
- Reason: X.Z depends on output of X.Y

## Current Customer Management Analysis

### Independent Tasks (Can Parallelize)
- Task 5.1 (CustomerService) and Task 5.5 (PropertyService)
- Task 6.1 (Exceptions) and Task 5.x (Services) - exceptions can be created first
- Task 7.x (Customer API) and Task 9.x (Property API) - after services done

### Sequential Dependencies
- Task 5.6 (Service Tests) depends on 5.1-5.5
- Task 7.x depends on Task 5.x and Task 6.x
- Task 10.x (Integration) depends on Task 7-9

## Subagent Strategy

For parallel execution, spawn subagents:
```
Main Agent: Coordinates and tracks progress
Subagent A: Implements CustomerService (5.1-5.4)
Subagent B: Implements PropertyService (5.5)
Main Agent: Waits for both, then runs tests (5.6)
```
