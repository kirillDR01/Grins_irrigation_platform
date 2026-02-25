# agent-browser Reference

Full docs: `docs/agent-browser.md`

## Install
```bash
npm install -g agent-browser
agent-browser install
```

## Core Workflow (AI-optimal)
1. `agent-browser open <url>`
2. `agent-browser snapshot -i` → get interactive elements with refs (@e1, @e2...)
3. `agent-browser click @e1` / `agent-browser fill @e2 "text"` → interact via refs
4. Re-snapshot after page changes

## Key Commands
```
open <url>              navigate (aliases: goto, navigate)
click <sel>             click element
fill <sel> <text>       clear and fill input
type <sel> <text>       type into element (no clear)
press <key>             keyboard key (Enter, Tab, Control+a)
select <sel> <val>      dropdown select
check/uncheck <sel>     checkbox
scroll <dir> [px]       up/down/left/right
screenshot [path]       capture (--full for full page)
snapshot                accessibility tree with refs (use -i for interactive only, -c compact, -d N depth)
eval <js>               run JavaScript
close                   close browser
```

## Get Info
```
get text/html/value/attr/title/url/count/box <sel>
is visible/enabled/checked <sel>
```

## Selectors (priority order)
1. **Refs** `@e1` — from snapshot, deterministic, preferred
2. **CSS** `"#id"`, `".class"`, `"div > button"`
3. **Semantic** `find role button click --name "Submit"` / `find label "Email" fill "text"`
4. **Text/XPath** `"text=Submit"` / `"xpath=//button"`

## Wait
```
wait <selector>              wait for element visible
wait <ms>                    wait ms
wait --text "Welcome"        wait for text
wait --url "**/dash"         wait for URL pattern
wait --load networkidle      wait for load state
```

## Sessions
```bash
agent-browser --session name open url    # isolated session
agent-browser session list               # list sessions
```

## Options
`--json` machine output | `--headed` visible browser | `--full` full-page screenshot | `-i` interactive snapshot | `-c` compact snapshot

## Navigation
`back` | `forward` | `reload`

## Tabs
`tab` list | `tab new [url]` | `tab <n>` switch | `tab close [n]`

## Auth
```bash
agent-browser open api.example.com --headers '{"Authorization": "Bearer <token>"}'
```
Headers scoped to origin only.

## Debug
`trace start/stop [path]` | `console` | `errors` | `highlight <sel>` | `state save/load <path>`

## Architecture
Rust CLI → Node.js daemon (Playwright/Chromium). Daemon auto-starts and persists between commands.
