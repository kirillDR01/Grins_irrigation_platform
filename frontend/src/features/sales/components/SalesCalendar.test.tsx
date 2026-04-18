/**
 * Tests for SalesCalendar InternalNotesCard integration.
 *
 * Validates: internal-notes-simplification Requirement 4, 9
 * - Card renders with customer internal_notes in the edit dialog
 * - Placeholder renders when no customer is selected
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { SalesCalendar } from './SalesCalendar';

// Mock FullCalendar to avoid complex calendar rendering
vi.mock('@fullcalendar/react', () => ({
  default: ({ dateClick }: { dateClick?: (arg: { dateStr: string }) => void }) => (
    <div data-testid="fullcalendar">
      <button
        data-testid="mock-date-click"
        onClick={() => dateClick?.({ dateStr: '2026-04-20' })}
      >
        Click Date
      </button>
    </div>
  ),
}));
vi.mock('@fullcalendar/daygrid', () => ({ default: {} }));
vi.mock('@fullcalendar/timegrid', () => ({ default: {} }));
vi.mock('@fullcalendar/interaction', () => ({ default: {} }));

const mockPipelineItems = [
  {
    id: 'entry-001',
    customer_id: 'cust-001',
    customer_name: 'Jane Doe',
    customer_phone: '+19527373312',
    job_type: 'install',
    status: 'send_estimate',
    property_address: '123 Elm St',
  },
  {
    id: 'entry-002',
    customer_id: null,
    customer_name: 'No Customer Yet',
    customer_phone: null,
    job_type: 'repair',
    status: 'new_lead',
    property_address: null,
  },
];

vi.mock('../hooks/useSalesPipeline', () => ({
  useSalesCalendarEvents: () => ({
    data: [],
    isLoading: false,
  }),
  useCreateCalendarEvent: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateCalendarEvent: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteCalendarEvent: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useSalesPipeline: () => ({
    data: { items: mockPipelineItems },
    isLoading: false,
  }),
}));

const mockUpdateCustomerMutateAsync = vi.fn().mockResolvedValue(undefined);
vi.mock('@/features/customers/hooks', () => ({
  useUpdateCustomer: () => ({
    mutateAsync: mockUpdateCustomerMutateAsync,
    isPending: false,
  }),
  customerKeys: {
    all: ['customers'],
    lists: () => ['customers', 'list'],
    detail: (id: string) => ['customers', 'detail', id],
  },
}));

vi.mock('@/features/customers/api/customerApi', () => ({
  customerApi: {
    get: vi.fn().mockResolvedValue({
      id: 'cust-001',
      first_name: 'Jane',
      last_name: 'Doe',
      phone: '+19527373312',
      internal_notes: 'Estimate appointment notes',
      is_priority: false,
      is_red_flag: false,
      is_slow_payer: false,
      properties: [],
    }),
  },
}));

vi.mock('@/shared/utils/invalidationHelpers', () => ({
  invalidateAfterCustomerInternalNotesSave: vi.fn(),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

describe('SalesCalendar InternalNotesCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows placeholder when no customer is selected in the create dialog', async () => {
    const user = userEvent.setup();

    render(<SalesCalendar />, { wrapper: createWrapper() });

    // Open the create dialog by clicking a date
    await user.click(screen.getByTestId('mock-date-click'));

    await waitFor(() => {
      expect(screen.getByTestId('calendar-event-form')).toBeInTheDocument();
    });

    // No customer selected yet — should show placeholder
    expect(screen.getByText('Notes will appear here once the customer is created')).toBeInTheDocument();
  });

  it('renders InternalNotesCard when a sales entry with customer is selected', async () => {
    const user = userEvent.setup();

    render(<SalesCalendar />, { wrapper: createWrapper() });

    // Open the create dialog
    await user.click(screen.getByTestId('mock-date-click'));

    await waitFor(() => {
      expect(screen.getByTestId('calendar-event-form')).toBeInTheDocument();
    });

    // Select a sales entry that has a customer
    const select = screen.getByRole('combobox') as HTMLSelectElement;
    await user.selectOptions(select, 'entry-001');

    // Wait for customer data to load and InternalNotesCard to render
    await waitFor(() => {
      expect(screen.getByTestId('sales-calendar-notes-editor')).toBeInTheDocument();
    });

    expect(screen.getByText('Estimate appointment notes')).toBeInTheDocument();
  });
});
