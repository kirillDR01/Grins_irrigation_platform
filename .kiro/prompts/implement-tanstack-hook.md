# Implement TanStack Query Hook

Create TanStack Query hooks for data fetching and mutations.

## Query Key Factory Pattern

```typescript
// hooks/use{Feature}s.ts
export const {feature}Keys = {
  all: ['{feature}s'] as const,
  lists: () => [...{feature}Keys.all, 'list'] as const,
  list: (params: {Feature}ListParams) => [...{feature}Keys.lists(), params] as const,
  details: () => [...{feature}Keys.all, 'detail'] as const,
  detail: (id: string) => [...{feature}Keys.details(), id] as const,
};
```

## List Query Hook

```typescript
import { useQuery, UseQueryOptions } from '@tanstack/react-query';
import { {feature}Api } from '../api/{feature}Api';
import type { {Feature}, {Feature}ListParams } from '../types';
import type { PaginatedResponse } from '@/core/api/types';

export function use{Feature}s(
  params?: {Feature}ListParams,
  options?: Omit<UseQueryOptions<PaginatedResponse<{Feature}>>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: {feature}Keys.list(params ?? {}),
    queryFn: () => {feature}Api.list(params),
    ...options,
  });
}
```

## Single Item Query Hook

```typescript
export function use{Feature}(
  id: string | undefined,
  options?: Omit<UseQueryOptions<{Feature}>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: {feature}Keys.detail(id!),
    queryFn: () => {feature}Api.get(id!),
    enabled: !!id,
    ...options,
  });
}
```

## Create Mutation Hook

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { {feature}Api } from '../api/{feature}Api';
import type { {Feature}, {Feature}Create } from '../types';

export function useCreate{Feature}() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {Feature}Create) => {feature}Api.create(data),
    onSuccess: () => {
      // Invalidate list queries to refetch
      queryClient.invalidateQueries({ queryKey: {feature}Keys.lists() });
    },
  });
}
```

## Update Mutation Hook

```typescript
export function useUpdate{Feature}() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: {Feature}Update }) =>
      {feature}Api.update(id, data),
    onSuccess: (updated{Feature}) => {
      // Update the cache for this specific item
      queryClient.setQueryData(
        {feature}Keys.detail(updated{Feature}.id),
        updated{Feature}
      );
      // Invalidate list queries
      queryClient.invalidateQueries({ queryKey: {feature}Keys.lists() });
    },
  });
}
```

## Delete Mutation Hook

```typescript
export function useDelete{Feature}() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => {feature}Api.delete(id),
    onSuccess: (_, id) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: {feature}Keys.detail(id) });
      // Invalidate list queries
      queryClient.invalidateQueries({ queryKey: {feature}Keys.lists() });
    },
  });
}
```

## Usage in Components

```typescript
function {Feature}List() {
  const { data, isLoading, error } = use{Feature}s({ page: 1, page_size: 20 });
  const createMutation = useCreate{Feature}();

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <div>
      {data?.items.map(item => (
        <{Feature}Card key={item.id} {feature}={item} />
      ))}
    </div>
  );
}
```

## Checklist

- [ ] Query key factory with proper hierarchy
- [ ] List hook with pagination support
- [ ] Single item hook with enabled condition
- [ ] Create mutation with list invalidation
- [ ] Update mutation with cache update
- [ ] Delete mutation with cache removal
- [ ] Proper TypeScript types throughout
- [ ] Options parameter for customization
