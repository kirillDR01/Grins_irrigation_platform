# Frontend Testing

Stack: Vitest + React Testing Library + agent-browser (E2E)

## File Location
Co-located: `features/{feature}/components/CustomerList.test.tsx`

## Component Test
```tsx
import { render, screen } from '@testing-library/react';
import { QueryProvider } from '@/core/providers/QueryProvider';

const wrapper = ({ children }) => <QueryProvider>{children}</QueryProvider>;

describe('CustomerList', () => {
  it('renders loading state', () => {
    render(<CustomerList />, { wrapper });
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });
  it('renders table when loaded', async () => {
    render(<CustomerList />, { wrapper });
    expect(await screen.findByTestId('customer-table')).toBeInTheDocument();
  });
});
```

## Form Test
```tsx
it('shows validation errors', async () => {
  const user = userEvent.setup();
  render(<CustomerForm onSuccess={vi.fn()} />);
  await user.click(screen.getByTestId('submit-btn'));
  await waitFor(() => expect(screen.getByText('First name is required')).toBeInTheDocument());
});
```

## Hook Test
```tsx
const { result } = renderHook(() => useCustomers(), { wrapper: QueryProvider });
await waitFor(() => expect(result.current.isSuccess).toBe(true));
```

## agent-browser Validation Script
```bash
agent-browser open http://localhost:5173/{feature}s
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='{feature}-table']"
agent-browser click "[data-testid='add-{feature}-btn']"
agent-browser wait "[data-testid='{feature}-form']"
agent-browser fill "[name='fieldName']" "value"
agent-browser click "[data-testid='submit-btn']"
agent-browser wait --text "Success"
agent-browser close
```

## Coverage Targets
Components: 80%+ | Hooks: 85%+ | Utils: 90%+

## Commands
```bash
npm test                    # all tests
npm run test:coverage       # with coverage
npm test CustomerList       # specific file
```
