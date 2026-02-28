# Frontend Patterns

## Architecture: Vertical Slice Architecture (VSA)

The frontend follows Vertical Slice Architecture where each feature is self-contained with its own components, hooks, API client, and types.

## Directory Structure

```
frontend/src/
├── core/                   # Foundation (exists before features)
│   ├── api/
│   │   ├── client.ts       # Axios instance
│   │   └── types.ts        # API response types
│   ├── config/
│   │   └── index.ts        # Environment config
│   ├── providers/
│   │   └── QueryProvider.tsx
│   └── router/
│       └── index.tsx
│
├── shared/                 # Cross-feature utilities (3+ features)
│   ├── components/
│   │   ├── ui/             # shadcn/ui components
│   │   ├── Layout.tsx
│   │   ├── PageHeader.tsx
│   │   └── StatusBadge.tsx
│   ├── hooks/
│   │   └── useDebounce.ts
│   └── utils/
│       └── formatters.ts
│
└── features/               # Feature slices
    └── {feature}/
        ├── components/
        ├── hooks/
        ├── api/
        ├── types/
        └── index.ts
```

## Component Patterns

### List Component Pattern

```typescript
export function CustomerList() {
  const [params, setParams] = useState<CustomerListParams>({
    page: 1,
    page_size: 20,
  });
  const { data, isLoading, error } = useCustomers(params);

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <div data-testid="customer-list">
      <PageHeader title="Customers" action={<AddButton />} />
      <DataTable
        data={data?.items ?? []}
        columns={columns}
        pagination={{
          page: params.page,
          pageSize: params.page_size,
          total: data?.total ?? 0,
          onPageChange: (page) => setParams(p => ({ ...p, page })),
        }}
      />
    </div>
  );
}
```

### Form Component Pattern

```typescript
const schema = z.object({
  firstName: z.string().min(1, 'First name is required'),
  lastName: z.string().min(1, 'Last name is required'),
  phone: z.string().regex(/^\d{10}$/, 'Phone must be 10 digits'),
  email: z.string().email().optional().or(z.literal('')),
});

type FormData = z.infer<typeof schema>;

export function CustomerForm({ customer, onSuccess }: CustomerFormProps) {
  const createMutation = useCreateCustomer();
  const updateMutation = useUpdateCustomer();
  
  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: customer ?? {
      firstName: '',
      lastName: '',
      phone: '',
      email: '',
    },
  });

  const onSubmit = async (data: FormData) => {
    if (customer) {
      await updateMutation.mutateAsync({ id: customer.id, data });
    } else {
      await createMutation.mutateAsync(data);
    }
    onSuccess?.();
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} data-testid="customer-form">
        <FormField
          control={form.control}
          name="firstName"
          render={({ field }) => (
            <FormItem>
              <FormLabel>First Name</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {/* ... more fields */}
        <Button type="submit" data-testid="submit-btn">
          {customer ? 'Update' : 'Create'}
        </Button>
      </form>
    </Form>
  );
}
```

## TanStack Query Patterns

### Query Key Factory

```typescript
export const customerKeys = {
  all: ['customers'] as const,
  lists: () => [...customerKeys.all, 'list'] as const,
  list: (params: CustomerListParams) => [...customerKeys.lists(), params] as const,
  details: () => [...customerKeys.all, 'detail'] as const,
  detail: (id: string) => [...customerKeys.details(), id] as const,
};
```

### Query Hook

```typescript
export function useCustomers(params?: CustomerListParams) {
  return useQuery({
    queryKey: customerKeys.list(params ?? {}),
    queryFn: () => customerApi.list(params),
  });
}
```

### Mutation Hook with Cache Invalidation

```typescript
export function useCreateCustomer() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: customerApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() });
    },
  });
}
```

## Styling Patterns

### Using cn() for Conditional Classes

```typescript
import { cn } from '@/shared/utils/cn';

<div className={cn(
  'base-class',
  isActive && 'active-class',
  variant === 'primary' && 'primary-class'
)} />
```

### Status Badge Colors

```typescript
const statusColors: Record<JobStatus, string> = {
  requested: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-blue-100 text-blue-800',
  scheduled: 'bg-purple-100 text-purple-800',
  in_progress: 'bg-orange-100 text-orange-800',
  completed: 'bg-green-100 text-green-800',
  closed: 'bg-gray-100 text-gray-800',
  cancelled: 'bg-red-100 text-red-800',
};
```

## Testing Attributes

Always add `data-testid` attributes for agent-browser testing:

```typescript
// Pages
<div data-testid="customers-page">

// Tables
<table data-testid="customer-table">

// Rows
<tr data-testid="customer-row">

// Forms
<form data-testid="customer-form">

// Buttons
<button data-testid="add-customer-btn">
<button data-testid="submit-btn">

// Navigation
<a data-testid="nav-customers">

// Status badges
<span data-testid="status-approved">
```

## Import Conventions

```typescript
// Core imports
import { apiClient } from '@/core/api/client';
import { QueryProvider } from '@/core/providers/QueryProvider';

// Shared imports
import { Button, Card } from '@/shared/components/ui';
import { Layout } from '@/shared/components/Layout';
import { useDebounce } from '@/shared/hooks/useDebounce';

// Feature imports (from public index.ts)
import { CustomerList, useCustomers } from '@/features/customers';
```

## Error Handling

```typescript
// In components
const { data, error, isLoading } = useCustomers();

if (error) {
  return (
    <Alert variant="destructive">
      <AlertTitle>Error</AlertTitle>
      <AlertDescription>{error.message}</AlertDescription>
    </Alert>
  );
}

// In mutations
const mutation = useCreateCustomer();

const handleSubmit = async (data: FormData) => {
  try {
    await mutation.mutateAsync(data);
    toast({ title: 'Success', description: 'Customer created' });
  } catch (error) {
    toast({ 
      title: 'Error', 
      description: error.message,
      variant: 'destructive' 
    });
  }
};
```
