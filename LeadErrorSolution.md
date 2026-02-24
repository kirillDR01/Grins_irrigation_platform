# Lead Form Submission Error — Solution

## Error

Submitting the "Get Your Free Design" form on `https://grins-irrigation.vercel.app` fails with:

```
Cross-Origin Request Blocked: The Same Origin Policy disallows reading the remote resource
at https://grins-platform-production.up.railway.app/api/v1/leads.
(Reason: CORS header 'Access-Control-Allow-Origin' missing). Status code: 404.
```

The browser's preflight `OPTIONS` request is rejected because the backend doesn't recognize the landing page as an allowed origin.

## Root Cause

The FastAPI backend reads allowed CORS origins from the `CORS_ORIGINS` environment variable on Railway. The landing page domain `https://grins-irrigation.vercel.app` is not included in that variable.

No code changes are needed — the CORS middleware in `src/grins_platform/app.py` already supports dynamic origins via environment configuration.

## Fix (Railway Environment Variable)

1. Open [Railway Dashboard](https://railway.app/dashboard) → your project → backend service → **Variables** tab
2. Add or update `CORS_ORIGINS`:

```
CORS_ORIGINS=https://grins-irrigation.vercel.app,https://grins-irrigation-platform.vercel.app
```

3. Railway auto-redeploys on variable change. If not, manually redeploy from the Deployments tab.

## Verification

Test the preflight request:

```bash
curl -I -X OPTIONS \
  -H "Origin: https://grins-irrigation.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  https://grins-platform-production.up.railway.app/api/v1/leads
```

Expected response headers:

```
Access-Control-Allow-Origin: https://grins-irrigation.vercel.app
Access-Control-Allow-Methods: *
Access-Control-Allow-Headers: *
```

Test the actual form POST:

```bash
curl -s -X POST https://grins-platform-production.up.railway.app/api/v1/leads \
  -H "Content-Type: application/json" \
  -H "Origin: https://grins-irrigation.vercel.app" \
  -d '{
    "name": "Test Lead",
    "phone": "(612) 555-0000",
    "zip_code": "55424",
    "situation": "new_system",
    "website": ""
  }'
```

Expected: HTTP 201 with `{"success": true, "message": "Thank you! We'll be in touch within 24 hours.", "lead_id": "..."}`.

## Important Rules for CORS_ORIGINS

- Include `https://` protocol prefix
- No trailing slash
- Comma-separate multiple origins
- Origins are case-sensitive

## Related Documentation

See [docs/lead-form-cors-fix.md](docs/lead-form-cors-fix.md) for the full detailed guide including troubleshooting steps.
