# Implement Feature Slice

Create a complete feature slice following Vertical Slice Architecture for the Admin Dashboard.

## Feature Slice Structure

```
frontend/src/features/{feature}/
├── components/
│   ├── {Feature}List.tsx       # List view with TanStack Table
│   ├── {Feature}Detail.tsx     # Detail view
│   ├── {Feature}Form.tsx       # Create/Edit form
│   └── {Feature}Search.tsx     # Search component (if needed)
├── hooks/
│   ├── use{Feature}s.ts        # List query hook
│   ├── use{Feature}.ts         # Single item query hook
│   ├── useCreate{Feature}.ts   # Create mutation hook
│   └── useUpdate{Feature}.ts   # Update mutation hook
├── api/
│   └── {feature}Api.ts         # API client functions
├── types/
│   └── index.ts                # TypeScript types
└── index.ts                    # Public exports
```

## Implementation Order

1. **Types** - Define TypeScript interfaces first
2. **API Client** - Create API functions with Axios
3. **Query Hooks** - Create TanStack Query hooks
4. **Mutation Hooks** - Create mutation hooks with cache invalidation
5. **Components** - Build UI components using hooks

## Type Definition Template

```typescript
// types/index.ts
export interface {Feature} {
  id: string;
  // ... fields from API response
  created_at: string;
  updated_at: string;
}

export interface {Feature}Create {
  // ... fields for creation (no id, timestamps)
}

export interface {Feature}Update {
  // ... optional fields for update
}

export interface {Feature}ListParams {
  page?: number;
  page_size?: number;
  // ... filter fields
}
```

## API Client Template

```typescript
// api/{feature}Api.ts
import { apiClient } from '@/core/api/client';
import type { {Feature}, {Feature}Create, {Feature}Update } from '../types';

export const {feature}Api = {
  list: (params?: {Feature}ListParams) =>
    apiClient.get<PaginatedResponse<{Feature}>>('/{feature}s', { params }),
  
  get: (id: string) =>
    apiClient.get<{Feature}>(`/{feature}s/${id}`),
  
  create: (data: {Feature}Create) =>
    apiClient.post<{Feature}>('/{feature}s', data),
  
  update: (id: string, data: {Feature}Update) =>
    apiClient.put<{Feature}>(`/{feature}s/${id}`, data),
  
  delete: (id: string) =>
    apiClient.delete(`/{feature}s/${id}`),
};
```

## Query Hook Template

```typescript
// hooks/use{Feature}s.ts
import { useQuery } from '@tanstack/react-query';
import { {feature}Api } from '../api/{feature}Api';

export const {feature}Keys = {
  all: ['{feature}s'] as const,
  lists: () => [...{feature}Keys.all, 'list'] as const,
  list: (params: {Feature}ListParams) => [...{feature}Keys.lists(), params] as const,
  details: () => [...{feature}Keys.all, 'detail'] as const,
  detail: (id: string) => [...{feature}Keys.details(), id] as const,
};

export function use{Feature}s(params?: {Feature}ListParams) {
  return useQuery({
    queryKey: {feature}Keys.list(params ?? {}),
    queryFn: () => {feature}Api.list(params).then(res => res.data),
  });
}
```

## Checklist

- [ ] Types defined with proper TypeScript interfaces
- [ ] API client with all CRUD operations
- [ ] Query hooks with queryKey factory
- [ ] Mutation hooks with cache invalidation
- [ ] List component with TanStack Table
- [ ] Detail component with data display
- [ ] Form component with React Hook Form + Zod
- [ ] All components have data-testid attributes
- [ ] Public exports in index.ts
