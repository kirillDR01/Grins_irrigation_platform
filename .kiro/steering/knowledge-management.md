# Knowledge Management

Experimental feature: semantic search across codebase.

## Setup
```bash
kiro-cli settings chat.enableKnowledge true
/knowledge add --name "grins-src" --path ./src --index-type Best
/knowledge add --name "grins-tests" --path ./src/grins_platform/tests --index-type Fast
/knowledge add --name "grins-specs" --path ./.kiro/specs --index-type Best
```

## Usage
```bash
/knowledge search "LoggerMixin implementation"
/knowledge show
```

Use for: pattern discovery, test examples, spec reference, code reuse.
