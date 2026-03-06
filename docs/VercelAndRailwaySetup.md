# Vercel & Railway CLI Setup

> Setup documentation for the Grins Irrigation Platform deployment CLIs.
> Date: 2026-03-03

---

## Prerequisites

- **Node.js**: v20.20.0+
- **npm**: v10.8.2+
- **Homebrew** (macOS): installed at `/opt/homebrew/bin/brew`

---

## 1. Railway CLI

### Installation

Railway CLI was installed via Homebrew:

```bash
brew install railway
```

**Installed version**: `4.30.5` (upgraded from `4.27.5` during setup)

**Binary location**: `/opt/homebrew/bin/railway`

### Update

```bash
brew upgrade railway
```

### Authentication

Railway CLI requires **browser-based login** for interactive authentication:

```bash
railway login
```

This opens a browser window for OAuth. After authenticating, a session token is stored in `~/.railway/config.json`.

> **Note**: Railway API Tokens (created via Account Settings > Tokens) work with the Railway GraphQL API but are **not supported by the CLI** for interactive commands like `whoami`. The CLI expects a browser session. API tokens are intended for CI/CD pipelines using the `RAILWAY_TOKEN` environment variable.

For CI/CD environments only:

```bash
export RAILWAY_TOKEN="<your-api-token>"
railway up  # deploy in CI
```

### Project Linking

The project is already linked in `~/.railway/config.json`:

| Setting         | Value                                    |
|-----------------|------------------------------------------|
| Project Name    | `zealous-heart`                          |
| Project ID      | `13317c6b-ca1f-48dd-b00b-91bfda8a7e5a`  |
| Environment     | `production`                             |
| Environment ID  | `df2bddee-c7be-412c-881a-63d7c70e25e1`  |
| Service         | `Grins_irrigation_platform`              |
| Service ID      | `e3f7489a-9c9c-4fe0-a26c-b075153d9d18`  |

Additional service in the project:

| Service   | Service ID                                 |
|-----------|--------------------------------------------|
| Postgres  | `b4be7465-049b-4dc8-b392-7a393556c16b`    |

To re-link (if needed):

```bash
railway link
```

### Common Commands

```bash
railway whoami          # Check logged-in user
railway status          # Show linked project/environment/service
railway up              # Deploy current directory
railway logs            # View service logs
railway run <cmd>       # Run command with Railway env vars injected
railway variables       # List environment variables
railway project list    # List all projects
railway domain          # Manage custom domains
```

### Current Auth Status

The previous browser session has **expired**. To re-authenticate:

```bash
railway login
```

Railway account email: `kirillrakitinsecond@gmail.com`

---

## 2. Vercel CLI

### Installation

Vercel CLI was installed globally via npm:

```bash
npm install -g vercel
```

**Installed version**: `50.26.0`

**Binary location**: installed via npm global

### Update

```bash
npm update -g vercel
```

### Authentication

Vercel supports both browser login and token-based auth:

```bash
# Browser login (interactive)
vercel login

# Token-based (non-interactive / CI)
vercel --token "<your-token>" <command>
```

**Authenticated user**: `kirilldr01`

**Team/Scope**: `kirilldr01s-projects`

### Project Linking

The Vercel project has been linked to this directory. Config stored in `.vercel/project.json`:

| Setting       | Value                                      |
|---------------|--------------------------------------------|
| Project Name  | `grins-irrigation-platform`                |
| Project ID    | `prj_SZexdljNexKryhM7PAJn3DQkDbSK`        |
| Org/Team ID   | `team_FANuLIVR0JFqdlXMuNgcJKvi`           |
| Production URL| https://grins-irrigation-platform.vercel.app |
| Node Version  | 24.x                                       |

To re-link (if needed):

```bash
vercel link --project grins-irrigation-platform --scope kirilldr01s-projects
```

### Environment Variables

| Variable                   | Environments                        |
|----------------------------|-------------------------------------|
| `VITE_API_URL`             | Development, Preview, Production    |
| `VITE_GOOGLE_MAPS_API_KEY` | Development, Preview, Production    |
| `VITE_API_BASE_URL`        | Production, Preview, Development    |

Manage env vars:

```bash
vercel env ls                          # List all env vars
vercel env add <NAME>                  # Add a new env var
vercel env rm <NAME>                   # Remove an env var
vercel env pull .env.local             # Pull env vars to local file
```

### Other Vercel Projects in Account

| Project              | Production URL                                                  |
|----------------------|-----------------------------------------------------------------|
| grins-irrigation     | https://grins-irrigation-kirilldr01s-projects.vercel.app        |

### Common Commands

```bash
vercel whoami                          # Check logged-in user
vercel ls                              # List recent deployments
vercel deploy                          # Create a preview deployment
vercel deploy --prod                   # Deploy to production
vercel logs <deployment-url>           # View deployment logs
vercel inspect <deployment-url>        # Inspect a deployment
vercel domains ls                      # List domains
vercel project ls                      # List all projects
```

---

## 3. Architecture Overview

```
Grins Irrigation Platform
├── Backend (Railway)
│   ├── Service: Grins_irrigation_platform (FastAPI)
│   ├── Service: Postgres (Database)
│   └── Environment: production
│
└── Frontend (Vercel)
    ├── Project: grins-irrigation-platform (Vite/React)
    ├── Node: 24.x
    └── Env vars: VITE_API_URL, VITE_API_BASE_URL, VITE_GOOGLE_MAPS_API_KEY
```

---

## 4. Deployment Workflow

### Deploy Backend (Railway)

```bash
# Authenticate first
railway login

# Check status
railway status

# Deploy
railway up

# View logs
railway logs
```

### Deploy Frontend (Vercel)

```bash
# Preview deployment
vercel deploy

# Production deployment
vercel deploy --prod

# Or with token (CI/CD)
vercel deploy --prod --token "<token>" --scope kirilldr01s-projects
```

### Verify Deployments

```bash
# Check Railway service status
railway status

# Check recent Vercel deployments
vercel ls
```

---

## 5. Troubleshooting

### Railway: "Unauthorized" Error

```bash
# Session expired — re-login via browser
railway login

# If using API token in CI, verify it's set
echo $RAILWAY_TOKEN
```

### Railway: "Cannot login in non-interactive mode"

The CLI requires a TTY for browser login. Run `railway login` from a regular terminal (not from an IDE terminal or script).

### Vercel: "No existing credentials found"

```bash
# Login via browser
vercel login

# Or use a token
vercel --token "<token>" whoami
```

### Vercel: "missing_scope" Error

Add `--scope kirilldr01s-projects` to your command:

```bash
vercel ls --scope kirilldr01s-projects
```

---

## 6. Setup Steps Performed (2026-03-03)

1. **Railway CLI** was already installed (`v4.27.5` via Homebrew)
2. **Upgraded Railway CLI** to `v4.30.5` via `brew upgrade railway`
3. **Installed Vercel CLI** `v50.26.0` via `npm install -g vercel`
4. **Verified Railway project** is linked in `~/.railway/config.json` (project: `zealous-heart`)
5. **Confirmed Railway services**: `Grins_irrigation_platform` + `Postgres`
6. **Authenticated Vercel CLI** with API token (user: `kirilldr01`)
7. **Linked Vercel project** `grins-irrigation-platform` to this directory (created `.vercel/project.json`)
8. **Verified Vercel environment variables**: 3 vars configured across all environments
9. **Railway browser re-login needed**: previous session expired, run `railway login` from a terminal
