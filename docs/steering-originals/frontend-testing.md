# Frontend Testing Guide

## Testing Stack

- **Vitest**: Test runner (fast, Vite-native)
- **React Testing Library**: Component testing
- **MSW (Mock Service Worker)**: API mocking (optional)
- **agent-browser**: E2E/UI validation

## Test File Organization

```
frontend/src/features/{feature}/
├── components/
│   ├── CustomerList.tsx
│   └── CustomerList.test.tsx    # Co-located test
├── hooks/
│   ├── useCustomers.ts
│   └── useCustomers.test.ts     # Co-located test
```

## Component Testing Patterns

### Basic Component Test

```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CustomerList } from './CustomerList';
import { QueryProvider } from '@/core/providers/QueryProvider';

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryProvider>{children}</QueryProvider>
);

describe('CustomerList', () => {
  it('renders loading state initially', () => {
    render(<CustomerList />, { wrapper });
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('renders customer table when data loads', async () => {
    render(<CustomerList />, { wrapper });
    expect(await screen.findByTestId('customer-table')).toBeInTheDocument();
  });
});
```

### Form Validation Test

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CustomerForm } from './CustomerForm';

describe('CustomerForm', () => {
  it('shows validation errors for empty required fields', async () => {
    const user = userEvent.setup();
    render(<CustomerForm onSuccess={vi.fn()} />);
    
    await user.click(screen.getByTestId('submit-btn'));
    
    await waitFor(() => {
      expect(screen.getByText('First name is required')).toBeInTheDocument();
    });
  });

  it('submits form with valid data', async () => {
    const user = userEvent.setup();
    const onSuccess = vi.fn();
    render(<CustomerForm onSuccess={onSuccess} />);
    
    await user.type(screen.getByLabelText('First Name'), 'John');
    await user.type(screen.getByLabelText('Last Name'), 'Doe');
    await user.type(screen.getByLabelText('Phone'), '6125551234');
    await user.click(screen.getByTestId('submit-btn'));
    
    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });
});
```

### Hook Testing

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { useCustomers } from './useCustomers';
import { QueryProvider } from '@/core/providers/QueryProvider';

describe('useCustomers', () => {
  it('fetches customers successfully', async () => {
    const { result } = renderHook(() => useCustomers(), {
      wrapper: QueryProvider,
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.items).toBeDefined();
  });
});
```

## Agent-Browser UI Validation

### Test Data IDs Convention

| Component | Test ID Pattern | Example |
|-----------|-----------------|---------|
| Page containers | `{feature}-page` | `customers-page` |
| Tables | `{feature}-table` | `customer-table` |
| Table rows | `{feature}-row` | `customer-row` |
| Forms | `{feature}-form` | `customer-form` |
| Buttons | `{action}-{feature}-btn` | `add-customer-btn` |
| Inputs | Form field `name` attribute | `name="firstName"` |
| Status badges | `status-{status}` | `status-scheduled` |
| Navigation | `nav-{feature}` | `nav-customers` |

### Validation Script Pattern

```bash
#!/bin/bash
# scripts/validate-{feature}.sh

echo "🧪 {Feature} User Journey Test"
echo "Scenario: Viktor {does something}"

agent-browser open http://localhost:5173/{feature}s
agent-browser wait --load networkidle

# Step 1: Verify page loads
echo "Step 1: Page loads correctly"
agent-browser is visible "[data-testid='{feature}-table']" && echo "  ✓ Table visible"

# Step 2: Test interaction
echo "Step 2: Test {action}"
agent-browser click "[data-testid='add-{feature}-btn']"
agent-browser wait "[data-testid='{feature}-form']"
echo "  ✓ Form opened"

# Step 3: Fill form
echo "Step 3: Fill form"
agent-browser fill "[name='fieldName']" "value"
agent-browser click "[data-testid='submit-btn']"
agent-browser wait --text "Success"
echo "  ✓ Form submitted"

agent-browser close
echo "✅ {Feature} Validation PASSED!"
```

### Running Validations

```bash
# Ensure frontend is running
cd frontend && npm run dev

# In another terminal, run validations
bash scripts/validate-layout.sh
bash scripts/validate-customers.sh
bash scripts/validate-jobs.sh
bash scripts/validate-schedule.sh

# Or run all
bash scripts/validate-all.sh
```

## Coverage Requirements

| Component Type | Target Coverage |
|----------------|-----------------|
| Components | 80%+ |
| Hooks | 85%+ |
| Utils | 90%+ |

## Running Tests

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run specific file
npm test CustomerList

# Watch mode
npm run test:watch
```

## Vitest Configuration

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['node_modules/', 'src/test/'],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

## Test Setup File

```typescript
// src/test/setup.ts
import '@testing-library/jest-dom';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// Cleanup after each test
afterEach(() => {
  cleanup();
});
```
