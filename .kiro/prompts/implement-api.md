# Implement API Endpoint

Implement a FastAPI endpoint following the Grins Platform patterns.

## Template Structure

```python
from fastapi import APIRouter, Depends, HTTPException, status
from grins_platform.schemas.{domain} import {RequestSchema}, {ResponseSchema}
from grins_platform.services.{domain}_service import {Domain}Service

router = APIRouter(prefix="/api/v1/{domain}s", tags=["{Domain}s"])

@router.post(
    "",
    response_model={ResponseSchema},
    status_code=status.HTTP_201_CREATED,
    summary="Create {domain}",
    description="Create a new {domain} with the provided data."
)
async def create_{domain}(
    data: {RequestSchema},
    service: {Domain}Service = Depends(get_{domain}_service)
) -> {ResponseSchema}:
    """Create a new {domain}."""
    try:
        return await service.create_{domain}(data)
    except DuplicateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{id}",
    response_model={ResponseSchema},
    summary="Get {domain}",
    description="Retrieve a {domain} by ID."
)
async def get_{domain}(
    id: int,
    service: {Domain}Service = Depends(get_{domain}_service)
) -> {ResponseSchema}:
    """Get {domain} by ID."""
    result = await service.get_{domain}(id)
    if not result:
        raise HTTPException(status_code=404, detail="{Domain} not found")
    return result
```

## HTTP Status Codes

| Operation | Success | Not Found | Validation Error | Duplicate |
|-----------|---------|-----------|------------------|-----------|
| POST      | 201     | -         | 400              | 400       |
| GET       | 200     | 404       | -                | -         |
| PUT       | 200     | 404       | 400              | -         |
| DELETE    | 204     | 404       | -                | -         |

## Checklist

- [ ] Router with prefix and tags
- [ ] Proper HTTP status codes
- [ ] Dependency injection for service
- [ ] Request/response schemas
- [ ] Exception handling with HTTPException
- [ ] Summary and description for OpenAPI
- [ ] Type hints on all parameters
