# Postman Power Integration Guide

This document provides comprehensive documentation for the Postman Power integration with Kiro IDE for the Grin's Irrigation Platform project.

## Overview

The Postman Power enables automated API testing directly from Kiro IDE. It connects to Postman's cloud services via MCP (Model Context Protocol) to create workspaces, collections, environments, and run automated tests.

## Setup Requirements

### 1. Postman API Key

1. Go to [postman.com](https://postman.com) and sign in
2. Click your avatar → **Settings** → **API Keys**
3. Click **Generate API Key**
4. Name it (e.g., "Kiro MCP Integration")
5. Copy the key (starts with `PMAK-`)

### 2. Environment Variable Configuration

The Postman Power uses environment variable interpolation for security. Set the API key:

```bash
# Add to your shell profile (~/.zshrc or ~/.bashrc)
export POSTMAN_API_KEY="PMAK-your-actual-key-here"

# Reload your shell
source ~/.zshrc
```

### 3. MCP Configuration

The Power is configured at the user level in `~/.kiro/settings/mcp.json`:

```json
{
  "powers": {
    "mcpServers": {
      "power-postman-postman": {
        "url": "https://mcp.postman.com/minimal",
        "headers": {
          "Authorization": "Bearer ${POSTMAN_API_KEY}"
        }
      }
    }
  }
}
```

### 4. Restart Kiro IDE

After setting the environment variable, restart Kiro IDE to pick up the changes.

---

## Project Resources Created

### Workspace

| Property | Value |
|----------|-------|
| **Name** | Grins Irrigation Platform |
| **ID** | `1b9f7a2b-5e92-42e0-abee-0be520dce654` |
| **Type** | Personal |
| **Description** | API testing workspace for Grin's Irrigation Platform - Field Service Automation System |

### Collection

| Property | Value |
|----------|-------|
| **Name** | Grins Irrigation API |
| **ID** | `8365c246-9686-4b49-9411-a7ea4e7383a4` |
| **UID** | `51717366-8365c246-9686-4b49-9411-a7ea4e7383a4` |

### Environment

| Property | Value |
|----------|-------|
| **Name** | Local Development |
| **ID** | `3515efac-a8af-4dd9-bbfc-d15b63d78777` |
| **UID** | `51717366-3515efac-a8af-4dd9-bbfc-d15b63d78777` |
| **Variables** | `base_url` = `http://localhost:8000` |

### Requests in Collection

| Request Name | Method | Endpoint | Request ID |
|--------------|--------|----------|------------|
| Health Check | GET | `{{base_url}}/health` | (root) |
| List Customers | GET | `{{base_url}}/api/v1/customers` | `7b23c668-47be-e50c-601c-118784e0cd16` |
| Create Customer | POST | `{{base_url}}/api/v1/customers` | `5dc14ba4-3139-89f8-2902-d9c51fc50bac` |
| List Jobs | GET | `{{base_url}}/api/v1/jobs` | `03fa1105-2fca-9d57-264b-c29bb612ec29` |
| List Staff | GET | `{{base_url}}/api/v1/staff` | `2ce71865-aa3b-c48b-7dd4-8704e1bab715` |
| List Service Offerings | GET | `{{base_url}}/api/v1/services` | `851c793c-0d8c-1b3b-977a-aa8ae11b8f6b` |

---

## Local Configuration Files

### `.postman.json`

This file stores Postman resource IDs for automated testing:

```json
{
  "workspace": {
    "id": "1b9f7a2b-5e92-42e0-abee-0be520dce654",
    "name": "Grins Irrigation Platform"
  },
  "collection": {
    "id": "8365c246-9686-4b49-9411-a7ea4e7383a4",
    "uid": "51717366-8365c246-9686-4b49-9411-a7ea4e7383a4",
    "name": "Grins Irrigation API"
  },
  "environment": {
    "id": "3515efac-a8af-4dd9-bbfc-d15b63d78777",
    "uid": "51717366-3515efac-a8af-4dd9-bbfc-d15b63d78777",
    "name": "Local Development"
  }
}
```

### `.kiro/hooks/postman-api-testing.kiro.hook`

This hook automatically triggers API testing when source code changes:

```json
{
  "enabled": true,
  "name": "API Postman Testing",
  "description": "Monitors API source code changes and automatically runs Postman collection tests",
  "version": "1",
  "when": {
    "type": "fileEdited",
    "patterns": [
      "src/grins_platform/api/**/*.py",
      "src/grins_platform/services/**/*.py",
      "src/grins_platform/schemas/**/*.py",
      "src/grins_platform/repositories/**/*.py"
    ]
  },
  "then": {
    "type": "askAgent",
    "prompt": "API source code has been modified. Please retrieve the contents of the .postman.json file. If the file exists, get the collection ID and run the collection using the Postman Power, showing me the results and propose fixes for any errors found."
  }
}
```

---

## Using the Postman Power

### Verify Connection

Ask Kiro to verify the Postman connection:

```
Verify that the Postman Power is connected and working.
```

Kiro will call `getAuthenticatedUser` to confirm authentication.

### Run API Tests

**Prerequisites:** Start the API server first:

```bash
# Option 1: Docker
docker-compose up -d

# Option 2: Direct
uv run uvicorn grins_platform.main:app --reload
```

**Run tests via Kiro:**

```
Run the Postman collection for the Grins Irrigation API and show me the results.
```

Or be more specific:

```
Use the Postman Power to run collection ID 51717366-8365c246-9686-4b49-9411-a7ea4e7383a4 
with environment ID 51717366-3515efac-a8af-4dd9-bbfc-d15b63d78777
```

### Add New Requests

Ask Kiro to add new API requests to the collection:

```
Add a new request to the Postman collection for GET /api/v1/properties endpoint.
```

### Create New Environment

For staging or production testing:

```
Create a new Postman environment called "Staging" with base_url set to https://api.staging.grins.com
```

---

## Available Postman Power Tools

The Postman Power (Minimal mode) provides 40 tools:

### Workspace Management
- `createWorkspace` - Create a new workspace
- `getWorkspace` - Get workspace details
- `getWorkspaces` - List all accessible workspaces
- `updateWorkspace` - Update workspace properties

### Collection Management
- `createCollection` - Create a new API collection
- `getCollection` - Get detailed collection information
- `getCollections` - List all collections in a workspace
- `putCollection` - Replace/update entire collection
- `duplicateCollection` - Create a copy of a collection
- `createCollectionRequest` - Add a request to a collection
- `createCollectionResponse` - Add a response example to a request

### Environment Management
- `createEnvironment` - Create a new environment
- `getEnvironment` - Get environment details
- `getEnvironments` - List all environments
- `putEnvironment` - Replace/update entire environment

### Testing & Execution
- `runCollection` - Execute a collection with automated tests

### User & Metadata
- `getAuthenticatedUser` - Get current user information

---

## Example Kiro Commands

### Basic Operations

```
# Check connection
Verify the Postman Power is working

# List workspaces
Show me all my Postman workspaces

# Get collection details
Get the details of the Grins Irrigation API collection

# Run tests
Run the Postman collection and show results
```

### Advanced Operations

```
# Add request with test script
Add a POST request to create a new job at /api/v1/jobs with a test 
that verifies the response status is 201 and the response contains an id field

# Create staging environment
Create a Postman environment for staging with:
- base_url: https://api.staging.grins.com
- api_key: {{STAGING_API_KEY}}

# Duplicate collection for a new version
Duplicate the Grins Irrigation API collection with suffix "v2"
```

---

## Troubleshooting

### "401 Unauthorized" Error

**Cause:** API key not set or invalid

**Solution:**
1. Verify `POSTMAN_API_KEY` environment variable is set: `echo $POSTMAN_API_KEY`
2. Regenerate API key at postman.com if needed
3. Restart Kiro IDE after setting the variable

### "Collection not found" Error

**Cause:** Using wrong collection ID format

**Solution:** Use the full UID format: `{owner_id}-{collection_id}`
- ✅ Correct: `51717366-8365c246-9686-4b49-9411-a7ea4e7383a4`
- ❌ Wrong: `8365c246-9686-4b49-9411-a7ea4e7383a4`

### All Requests Fail When Running Collection

**Cause:** API server not running

**Solution:**
1. Start the server: `docker-compose up -d` or `uv run uvicorn grins_platform.main:app`
2. Verify server is running: `curl http://localhost:8000/health`
3. Re-run the collection

### Environment Variables Not Substituted

**Cause:** Environment not selected or variable not defined

**Solution:**
1. Ensure environment ID is passed to `runCollection`
2. Verify variable exists in environment: use `getEnvironment` to check

---

## Integration with CI/CD

For automated testing in CI/CD pipelines, you can:

1. **Use Postman CLI (Newman):**
   ```bash
   npm install -g newman
   newman run https://api.postman.com/collections/51717366-8365c246-9686-4b49-9411-a7ea4e7383a4 \
     --environment https://api.postman.com/environments/51717366-3515efac-a8af-4dd9-bbfc-d15b63d78777 \
     --api-key $POSTMAN_API_KEY
   ```

2. **Use Kiro Power in GitHub Actions:**
   The Postman Power can be invoked programmatically for automated testing.

---

## Best Practices

1. **Store IDs in `.postman.json`** - Keep resource IDs in version control for team consistency
2. **Use environment variables** - Never hardcode URLs or API keys in requests
3. **Add test scripts** - Include assertions in each request to validate responses
4. **Organize with folders** - Group related requests (Customers, Jobs, Staff, etc.)
5. **Run before deployment** - Execute collection tests as part of your deployment process
6. **Keep collection in sync** - Update Postman collection when API changes

---

## Quick Reference

| Action | Command/Tool |
|--------|--------------|
| Verify connection | `getAuthenticatedUser` |
| List workspaces | `getWorkspaces` |
| Get collection | `getCollection` with UID |
| Run tests | `runCollection` with collection UID and environment UID |
| Add request | `createCollectionRequest` |
| Create environment | `createEnvironment` |

---

## Links

- **Postman Workspace:** [Open in Postman](https://go.postman.co/workspace/1b9f7a2b-5e92-42e0-abee-0be520dce654)
- **Postman API Documentation:** https://www.postman.com/postman/workspace/postman-public-workspace/documentation/12959542-c8142d51-e97c-46b6-bd77-52bb66712c9a
- **Kiro Powers Documentation:** See Kiro IDE documentation
