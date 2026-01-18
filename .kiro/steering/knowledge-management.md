# Knowledge Management Guide

## Enabling Knowledge Management

Knowledge management is an experimental feature that provides semantic search across your codebase.

### Setup (CLI)

```bash
# Enable the feature
kiro-cli settings chat.enableKnowledge true

# Add your codebase
/knowledge add --name "grins-src" --path ./src --index-type Best
/knowledge add --name "grins-tests" --path ./src/grins_platform/tests --index-type Fast
/knowledge add --name "grins-specs" --path ./.kiro/specs --index-type Best
```

### Usage

```bash
# Search for patterns
/knowledge search "LoggerMixin implementation"
/knowledge search "property-based test example"
/knowledge search "customer repository methods"

# View indexed content
/knowledge show
```

## Benefits for Grins Platform

1. **Pattern Discovery**: Find existing implementations to follow
2. **Test Examples**: Search for similar test patterns
3. **Spec Reference**: Quick access to requirements and design
4. **Code Reuse**: Find existing utilities and helpers

## Recommended Indexes

| Name | Path | Index Type | Purpose |
|------|------|------------|---------|
| grins-src | ./src | Best | Main source code |
| grins-tests | ./src/grins_platform/tests | Fast | Test patterns |
| grins-specs | ./.kiro/specs | Best | Requirements and design |
| grins-steering | ./.kiro/steering | Fast | Standards and patterns |
