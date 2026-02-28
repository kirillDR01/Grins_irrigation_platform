# Kiro CLI Reference

## Quick Start
```bash
curl -fsSL https://cli.kiro.dev/install | bash  # install
kiro-cli login                                    # auth (opens browser)
kiro-cli                                          # start chat
```

## Models
Auto (recommended, cheapest) | Haiku 4.5 (fastest) | Sonnet 4.0/4.5 (coding) | Opus 4.5 (complex)
Switch: `/model` | Set default: `/model set-current-as-default`

## Steering (project knowledge)
Markdown files providing persistent context.
- Global: `~/.kiro/steering/` | Project: `.kiro/steering/`
- Key files: product.md, tech.md, structure.md

## Prompts
Local: `.kiro/prompts/` | Global: `~/.kiro/prompts/` | Use: `@prompt-name`
Local/global prompts don't support native args — prompt must ask user if args missing.

## MCP Servers
Config: `.kiro/settings/mcp.json`
```json
{ "mcpServers": { "name": { "command": "cmd", "args": [], "env": {} } } }
```
Commands: `kiro-cli mcp add`, `/mcp` (list/status)

## Custom Agents
Location: `.kiro/agents/` (project) or `~/.kiro/agents/` (global)
```json
{ "name": "my-agent", "prompt": "...", "tools": ["read","write","shell"], "allowedTools": ["read"], "resources": ["file://README.md"], "model": "claude-sonnet-4" }
```
Commands: `/agent generate` | `/agent list` | `/agent swap name`

## Context
| Type | Persistence | Impact | Use For |
|------|------------|--------|---------|
| Agent Resources | Persistent | Always active | Essential files |
| Session Context | Current session | Always active | Temp files |
| Knowledge Bases | Persistent | Searched on demand | Large codebases |

`/context show` | `/context add file` | `/context clear`

## Hooks
```json
{ "hooks": { "preToolUse": [{"matcher":"shell","command":"echo check"}], "postToolUse": [{"matcher":"write","command":"cargo fmt"}] } }
```
Types: agentSpawn, userPromptSubmit, preToolUse (can block), postToolUse, stop

## Key Slash Commands
`/help` `/quit` `/clear` `/context show|add|remove` `/model` `/agent list|swap` `/chat resume` `/tools` `/prompts list` `/knowledge search`

## Config Hierarchy
Agent Config > Project `.kiro/` > Global `~/.kiro/`
