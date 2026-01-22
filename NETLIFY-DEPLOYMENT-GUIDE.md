# Netlify Deployment Guide

## Overview

This guide documents how to use the Netlify Power in Kiro for deploying the Grin's Irrigation Platform frontend. Netlify is ideal for deploying React, Next.js, Vue, and other modern web apps to a global CDN with automatic builds.

## Current Status

| Component | Status | Details |
|-----------|--------|---------|
| Netlify CLI | ✅ Installed | Available globally via `netlify` command |
| Authentication | ✅ Logged In | User: Kirill R (kirillrakitinsecond@gmail.com) |
| Team | ✅ Available | Grin_irrigation |
| Site Linked | ❌ Not Yet | No Netlify site created for this project |
| Frontend | ❌ Not Yet | Frontend directory will be created in Phase 3 |

## Prerequisites

### 1. Netlify CLI Installation

If not already installed:
```bash
npm install -g netlify-cli
```

### 2. Authentication

Check login status:
```bash
netlify status
```

If not logged in:
```bash
netlify login
```
This opens a browser for OAuth authentication.

### 3. Verify Installation

```bash
netlify --version
```

## Kiro Power Activation

The Netlify power is a CLI-based power (no MCP server required). To activate:

```
# In Kiro chat
Use kiroPowers tool with action="activate", powerName="netlify-deployment"
```

This provides deployment instructions and best practices.

## Project Setup

### Step 1: Create Frontend Directory

When Phase 3 begins, create the frontend structure:
```bash
mkdir -p frontend
cd frontend
npm create vite@latest . -- --template react-ts
npm install
```

### Step 2: Create netlify.toml

Create `frontend/netlify.toml`:
```toml
[build]
  command = "npm run build"
  publish = "dist"

# SPA redirect for client-side routing
[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

# Environment variables (non-sensitive)
[build.environment]
  NODE_VERSION = "18"

# Headers for security
[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-XSS-Protection = "1; mode=block"
    X-Content-Type-Options = "nosniff"
```

### Step 3: Link or Create Site

**Option A: Create New Site (Recommended for new projects)**
```bash
cd frontend
netlify init
```
Follow the interactive prompts to:
- Create a new site
- Connect to Git repository (optional)
- Configure build settings

**Option B: Link Existing Site**
```bash
netlify link --git-remote-url https://github.com/kirillDR01/Grins_irrigation_platform.git
```

## Deployment Commands

### Preview Deploy (Non-Production)

For testing changes before going live:
```bash
cd frontend
npm install          # Ensure dependencies installed
npm run build        # Build the project
netlify deploy       # Deploy to preview URL
```

This creates a unique preview URL for testing.

### Production Deploy

For deploying to the live site:
```bash
cd frontend
npm install
npm run build
netlify deploy --prod
```

### Deploy with Build

Let Netlify run the build:
```bash
netlify deploy --build --prod
```

## Environment Variables

### Setting Variables via CLI

```bash
# Set a variable
netlify env:set VITE_API_URL "https://api.grins-irrigation.com"

# List all variables
netlify env:list

# Get a specific variable
netlify env:get VITE_API_URL

# Delete a variable
netlify env:unset VITE_API_URL
```

### Required Variables for Grin's Platform

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `https://api.grins-irrigation.com` |
| `VITE_APP_NAME` | Application name | `Grin's Irrigation Admin` |

**Note:** Vite requires `VITE_` prefix for client-side environment variables.

## Useful Commands

### Site Management

```bash
# View site status
netlify status

# Open site in browser
netlify open

# Open admin dashboard
netlify open:admin

# View site details
netlify sites:list
```

### Build & Deploy

```bash
# Local development server with Netlify features
netlify dev

# Build locally (test build command)
netlify build

# Deploy with specific message
netlify deploy --prod --message "Phase 3: Initial frontend deployment"
```

### Logs & Debugging

```bash
# View deploy logs
netlify deploy:list

# View function logs (if using Netlify Functions)
netlify functions:list
```

## Continuous Deployment

### Git-Based Deployment

When linked to a Git repository, Netlify automatically:
1. Detects pushes to the main branch
2. Runs the build command
3. Deploys to production

Preview deploys are created for pull requests.

### Manual Trigger

```bash
# Trigger a new build
netlify build --context production
netlify deploy --prod
```

## Troubleshooting

### Common Issues

**1. Build Fails**
```bash
# Check build logs
netlify deploy --build 2>&1 | tee build.log

# Verify build command locally
npm run build
```

**2. Site Not Found**
```bash
# Re-link the site
netlify unlink
netlify link
```

**3. Environment Variables Not Working**
- Ensure variables have `VITE_` prefix for Vite projects
- Redeploy after setting new variables
- Check variable is set: `netlify env:list`

**4. 404 on Page Refresh (SPA)**
- Ensure `netlify.toml` has the SPA redirect rule
- Verify `publish` directory is correct

### Debug Mode

```bash
# Run with debug output
DEBUG=* netlify deploy
```

## Integration with Grin's Platform

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Netlify (Frontend)                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  React Admin Dashboard (Phase 3)                     │    │
│  │  - Customer Management                               │    │
│  │  - Job Management                                    │    │
│  │  - Schedule/Calendar                                 │    │
│  │  - Staff Management                                  │    │
│  │  - Dashboard Metrics                                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           │ HTTPS API Calls                  │
│                           ▼                                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 Railway (Backend API)                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  FastAPI Backend                                     │    │
│  │  - /api/v1/customers                                 │    │
│  │  - /api/v1/jobs                                      │    │
│  │  - /api/v1/staff                                     │    │
│  │  - /api/v1/services                                  │    │
│  │  - /api/v1/appointments (Phase 3)                    │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Deployment Workflow

1. **Backend (Railway)**: Deploy FastAPI backend first
2. **Frontend (Netlify)**: Deploy React frontend with `VITE_API_URL` pointing to Railway

### CORS Configuration

Ensure backend allows Netlify domain:
```python
# In FastAPI app
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://grins-irrigation.netlify.app",  # Production
        "https://*.netlify.app",                  # Preview deploys
        "http://localhost:5173",                  # Local dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Quick Reference

### Essential Commands

| Action | Command |
|--------|---------|
| Check status | `netlify status` |
| Preview deploy | `netlify deploy` |
| Production deploy | `netlify deploy --prod` |
| Set env var | `netlify env:set KEY "value"` |
| Local dev server | `netlify dev` |
| Open site | `netlify open` |
| View logs | `netlify deploy:list` |

### File Locations

| File | Purpose |
|------|---------|
| `frontend/netlify.toml` | Build and deploy configuration |
| `frontend/dist/` | Build output directory |
| `frontend/.netlify/` | Local Netlify state (gitignored) |

## Next Steps

1. **Phase 3 Start**: Create frontend directory with Vite + React + TypeScript
2. **Create Site**: Run `netlify init` in frontend directory
3. **Configure**: Set up `netlify.toml` with build settings
4. **Deploy**: Run `netlify deploy --prod` for initial deployment
5. **CI/CD**: Enable automatic deploys from Git

## Resources

- [Netlify CLI Documentation](https://docs.netlify.com/cli/get-started/)
- [Netlify Build Configuration](https://docs.netlify.com/configure-builds/file-based-configuration/)
- [Vite Deployment Guide](https://vitejs.dev/guide/static-deploy.html#netlify)
- Kiro Power: `kiroPowers` with `action="activate"`, `powerName="netlify-deployment"`
