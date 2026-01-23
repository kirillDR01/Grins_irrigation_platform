# Grin's Irrigation Platform - Admin Dashboard

A React + TypeScript admin dashboard for managing irrigation service operations, built with Vite and following Vertical Slice Architecture.

## Tech Stack

- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite
- **Styling:** Tailwind CSS v4 + shadcn/ui
- **State Management:** TanStack Query (React Query)
- **Forms:** React Hook Form + Zod validation
- **Tables:** TanStack Table
- **Calendar:** FullCalendar
- **Routing:** React Router v6
- **HTTP Client:** Axios
- **Testing:** Vitest + React Testing Library

## Getting Started

### Prerequisites

- Node.js 18+
- npm or pnpm
- Backend API running on `http://localhost:8000`

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:5173` (or next available port).

### Build

```bash
npm run build
```

### Testing

```bash
# Run tests
npm test

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch
```

### Linting & Type Checking

```bash
# Lint
npm run lint

# Type check
npm run typecheck
```

## Project Structure

```
frontend/src/
├── core/                   # Foundation (exists before features)
│   ├── api/
│   │   ├── client.ts       # Axios instance with interceptors
│   │   └── types.ts        # API response types
│   ├── config/
│   │   └── index.ts        # Environment configuration
│   ├── providers/
│   │   └── QueryProvider.tsx
│   └── router/
│       └── index.tsx       # Route definitions with code splitting
│
├── shared/                 # Cross-feature utilities
│   ├── components/
│   │   ├── ui/             # shadcn/ui components
│   │   ├── Layout.tsx      # Main layout with sidebar
│   │   ├── PageHeader.tsx  # Consistent page headers
│   │   ├── StatusBadge.tsx # Status indicators
│   │   ├── LoadingSpinner.tsx
│   │   └── ErrorBoundary.tsx
│   ├── hooks/
│   │   └── useDebounce.ts
│   └── utils/
│       └── cn.ts           # Class name utility
│
├── features/               # Feature slices (self-contained)
│   ├── customers/          # Customer management
│   │   ├── api/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── types/
│   │   └── index.ts
│   ├── jobs/               # Job management
│   │   └── ...
│   ├── schedule/           # Appointment scheduling
│   │   └── ...
│   ├── staff/              # Staff management
│   │   └── ...
│   └── dashboard/          # Dashboard metrics
│       └── ...
│
├── pages/                  # Page components (route targets)
│   ├── Dashboard.tsx
│   ├── Customers.tsx
│   ├── Jobs.tsx
│   ├── Schedule.tsx
│   ├── Staff.tsx
│   └── Settings.tsx
│
└── components/ui/          # shadcn/ui components
```

## Features

### Dashboard
- Overview metrics (customers, jobs, appointments)
- Jobs by status breakdown
- Today's schedule
- Quick action buttons

### Customer Management
- Customer list with search and pagination
- Customer detail view with properties and job history
- Create/edit customer forms with validation
- Customer flags (priority, red flag, slow payer)

### Job Management
- Job list with status filtering
- Job detail view with customer info
- Create/edit job forms
- Status workflow (requested → approved → scheduled → in_progress → completed)

### Schedule Management
- Calendar view (day/week/month) with FullCalendar
- List view with TanStack Table
- Appointment creation and editing
- Staff assignment

### Staff Management
- Staff list with role badges
- Staff detail view with availability
- Skills and certifications display

## API Integration

All API calls use TanStack Query for caching and state management.

### Query Key Factory Pattern

```typescript
export const customerKeys = {
  all: ['customers'] as const,
  lists: () => [...customerKeys.all, 'list'] as const,
  list: (params: CustomerListParams) => [...customerKeys.lists(), params] as const,
  details: () => [...customerKeys.all, 'detail'] as const,
  detail: (id: string) => [...customerKeys.details(), id] as const,
};
```

### Example Hook Usage

```typescript
// Query hook
const { data, isLoading, error } = useCustomers({ page: 1, page_size: 20 });

// Mutation hook
const createMutation = useCreateCustomer();
await createMutation.mutateAsync(customerData);
```

## Testing

Tests are co-located with components:

```
features/customers/components/
├── CustomerList.tsx
├── CustomerList.test.tsx
├── CustomerForm.tsx
└── CustomerForm.test.tsx
```

### Test Data IDs

All interactive elements have `data-testid` attributes for testing:

| Component | Test ID Pattern | Example |
|-----------|-----------------|---------|
| Pages | `{feature}-page` | `customers-page` |
| Tables | `{feature}-table` | `customer-table` |
| Forms | `{feature}-form` | `customer-form` |
| Buttons | `{action}-{feature}-btn` | `add-customer-btn` |

## Environment Variables

Create a `.env` file:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## Code Quality

- **ESLint:** TypeScript-aware linting
- **Prettier:** Code formatting
- **TypeScript:** Strict mode enabled
- **Vitest:** Unit and integration tests

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

Proprietary - Grin's Irrigation Platform
