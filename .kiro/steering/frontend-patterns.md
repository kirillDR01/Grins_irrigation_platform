# Frontend Patterns

## Architecture: VSA (Vertical Slice)
```
frontend/src/
├── core/          # api/client.ts, config, providers (QueryProvider), router
├── shared/        # ui/ components, hooks (useDebounce), utils (formatters)
└── features/{f}/  # components/, hooks/, api/, types/, index.ts
```
Features import from core/ and shared/, never from each other.

## Component Patterns

### List
```tsx
export function CustomerList() {
  const [params, setParams] = useState<Params>({ page: 1, page_size: 20 });
  const { data, isLoading, error } = useCustomers(params);
  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  return (
    <div data-testid="customer-list">
      <PageHeader title="Customers" action={<AddButton />} />
      <DataTable data={data?.items ?? []} columns={columns}
        pagination={{ page: params.page, total: data?.total ?? 0, onPageChange: p => setParams(s => ({...s, page: p})) }} />
    </div>
  );
}
```

### Form (React Hook Form + Zod)
```tsx
const schema = z.object({
  firstName: z.string().min(1, 'Required'),
  lastName: z.string().min(1, 'Required'),
  phone: z.string().regex(/^\d{10}$/, '10 digits'),
  email: z.string().email().optional().or(z.literal('')),  // optional field pattern
});
type FormData = z.infer<typeof schema>;

export function CustomerForm({ customer, onSuccess }: Props) {
  const create = useCreateCustomer();
  const update = useUpdateCustomer();
  const form = useForm<FormData>({ resolver: zodResolver(schema), defaultValues: customer ?? { firstName: '', lastName: '', phone: '', email: '' } });
  const onSubmit = async (data: FormData) => {
    try {
      customer ? await update.mutateAsync({ id: customer.id, data }) : await create.mutateAsync(data);
      toast({ title: 'Success', description: 'Customer saved' });
      onSuccess?.();
    } catch (error) {
      toast({ title: 'Error', description: error.message, variant: 'destructive' });
    }
  };
  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} data-testid="customer-form">
        <FormField control={form.control} name="firstName" render={({ field }) => (
          <FormItem>
            <FormLabel>First Name</FormLabel>
            <FormControl><Input {...field} /></FormControl>
            <FormMessage />
          </FormItem>
        )} />
        {/* Repeat FormField pattern for each field */}
        <Button type="submit" data-testid="submit-btn">{customer ? 'Update' : 'Create'}</Button>
      </form>
    </Form>
  );
}
```

## TanStack Query

### Key Factory
```ts
export const customerKeys = {
  all: ['customers'] as const,
  lists: () => [...customerKeys.all, 'list'] as const,
  list: (params: Params) => [...customerKeys.lists(), params] as const,
  detail: (id: string) => [...customerKeys.all, 'detail', id] as const,
};
```

### Hooks
```ts
export function useCustomers(params?) { return useQuery({ queryKey: customerKeys.list(params ?? {}), queryFn: () => api.list(params) }); }
export function useCreateCustomer() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.create, onSuccess: () => qc.invalidateQueries({ queryKey: customerKeys.lists() }) });
}
```

## Styling
`cn()` for conditional classes: `cn('base', isActive && 'active-class')`
Status colors: Record<Status, string> mapping to Tailwind bg/text classes.

## data-testid Convention
Pages: `{feature}-page` | Tables: `{feature}-table` | Rows: `{feature}-row` | Forms: `{feature}-form` | Buttons: `{action}-{feature}-btn` | Nav: `nav-{feature}` | Status: `status-{value}`

## Import Conventions
```ts
import { apiClient } from '@/core/api/client';         // core
import { Button, Card } from '@/shared/components/ui';  // shared ui
import { Layout } from '@/shared/components/Layout';     // shared layout
import { useDebounce } from '@/shared/hooks/useDebounce'; // shared hooks
import { CustomerList, useCustomers } from '@/features/customers'; // feature public API via index.ts
```
`@/` = `frontend/src/`. Features export public API through `index.ts`.

## Error Handling
Queries: check `error` → show `<Alert variant="destructive">`.
Mutations: try/catch with `toast({ title, description, variant: 'destructive' })` (shown in Form pattern above).
