/**
 * Tests for CreateJobModal (Cluster C — Task 10).
 *
 * Cluster C replaces the SignWell-gated convert flow with a plain
 * "Create Job" modal that fires `POST /api/v1/jobs` and flips the
 * sales entry to `closed_won`. These tests pin down the 10-field
 * layout, readonly + disabled-field behaviour, and the submit
 * payload shape.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import type { ReactNode } from 'react';
import { CreateJobModal } from './CreateJobModal';
import type { SalesEntry } from '@/features/sales/types/pipeline';

const mockCreateJobMutateAsync = vi.fn();
const mockUpdateJobMutateAsync = vi.fn();
const mockOverrideStatusMutateAsync = vi.fn();
const mockNavigate = vi.fn();

vi.mock('../hooks', () => ({
  useCreateJob: () => ({
    mutateAsync: mockCreateJobMutateAsync,
    isPending: false,
  }),
  useUpdateJob: () => ({
    mutateAsync: mockUpdateJobMutateAsync,
    isPending: false,
  }),
}));

vi.mock('@/features/sales/hooks/useSalesPipeline', () => ({
  useOverrideSalesStatus: () => ({
    mutateAsync: mockOverrideStatusMutateAsync,
    isPending: false,
  }),
  pipelineKeys: {
    all: ['sales-pipeline'] as const,
  },
}));

vi.mock('@/features/customers/hooks', () => ({
  useCustomer: () => ({
    data: {
      id: 'cust-001',
      first_name: 'Jane',
      last_name: 'Doe',
      phone: '+19527373312',
      email: 'kirillrakitinsecond@gmail.com',
      lead_source: 'referral',
      internal_notes: null,
      properties: [
        {
          id: 'prop-001',
          customer_id: 'cust-001',
          address: '123 Elm St',
          city: 'Minneapolis',
          state: 'MN',
          zip_code: '55401',
          is_primary: true,
        },
        {
          id: 'prop-002',
          customer_id: 'cust-001',
          address: '456 Oak Ave',
          city: 'Saint Paul',
          state: 'MN',
          zip_code: '55101',
          is_primary: false,
        },
      ],
    },
    isLoading: false,
    error: null,
  }),
}));

vi.mock('react-router-dom', async () => {
  const actual =
    await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function makeEntry(overrides: Partial<SalesEntry> = {}): SalesEntry {
  return {
    id: 'entry-001',
    customer_id: 'cust-001',
    property_id: 'prop-001',
    lead_id: 'lead-001',
    job_type: 'spring_startup',
    status: 'send_contract',
    last_contact_date: null,
    notes: 'Backyard sprinkler tune-up; gate code 1234.',
    override_flag: false,
    closed_reason: null,
    signwell_document_id: null,
    nudges_paused_until: null,
    dismissed_at: null,
    created_at: '2026-05-01T00:00:00Z',
    updated_at: '2026-05-01T00:00:00Z',
    customer_name: 'Jane Doe',
    customer_phone: '+19527373312',
    customer_email: 'kirillrakitinsecond@gmail.com',
    property_address: '123 Elm St',
    ...overrides,
  };
}

function wrap(node: ReactNode): ReactNode {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <MemoryRouter>
      <QueryClientProvider client={client}>{node}</QueryClientProvider>
    </MemoryRouter>
  );
}

describe('CreateJobModal', () => {
  beforeEach(() => {
    mockCreateJobMutateAsync.mockReset();
    mockUpdateJobMutateAsync.mockReset();
    mockOverrideStatusMutateAsync.mockReset();
    mockNavigate.mockReset();
    mockCreateJobMutateAsync.mockResolvedValue({ id: 'job-001' });
    mockOverrideStatusMutateAsync.mockResolvedValue({ id: 'entry-001' });
  });

  it('renders all 10 fields prefilled from the sales entry', async () => {
    render(
      wrap(
        <CreateJobModal
          open
          onOpenChange={() => undefined}
          salesEntry={makeEntry()}
        />,
      ),
    );

    await waitFor(() => {
      expect(screen.getByTestId('create-job-modal')).toBeInTheDocument();
    });

    // 1. Customer
    expect(screen.getByTestId('create-job-customer-input')).toHaveValue(
      'Jane Doe',
    );
    // 2. Property (combobox text trigger reflects selection)
    expect(screen.getByTestId('create-job-property-select')).toBeInTheDocument();
    // 3. Job type
    expect(screen.getByTestId('create-job-type-select')).toBeInTheDocument();
    // 4. Description prefilled from entry.notes
    expect(screen.getByTestId('create-job-description-input')).toHaveValue(
      'Backyard sprinkler tune-up; gate code 1234.',
    );
    // 5. Priority
    expect(screen.getByTestId('create-job-priority-select')).toBeInTheDocument();
    // 6. Estimated duration (nullable — empty by default)
    expect(screen.getByTestId('create-job-duration-input')).toHaveValue(null);
    // 7. Staffing required (default 1)
    expect(screen.getByTestId('create-job-staffing-input')).toHaveValue(1);
    // 8. Target start date (empty)
    expect(screen.getByTestId('create-job-start-date-input')).toHaveValue('');
    // 9. Lead source (readonly, from customer.lead_source)
    expect(screen.getByTestId('create-job-lead-source-input')).toHaveValue(
      'referral',
    );
    // 10. Tags (disabled)
    expect(screen.getByTestId('create-job-tags-input')).toBeDisabled();
  });

  it('customer and lead source are readonly; tags are disabled', () => {
    render(
      wrap(
        <CreateJobModal
          open
          onOpenChange={() => undefined}
          salesEntry={makeEntry()}
        />,
      ),
    );

    const customer = screen.getByTestId('create-job-customer-input');
    const leadSource = screen.getByTestId('create-job-lead-source-input');
    const tags = screen.getByTestId('create-job-tags-input');

    expect(customer).toHaveAttribute('readonly');
    expect(leadSource).toHaveAttribute('readonly');
    expect(tags).toBeDisabled();
    expect(
      screen.getByText(/Tags will be editable once Cluster A ships\./i),
    ).toBeInTheDocument();
  });

  it('submitting calls useCreateJob with the form values then advances to closed_won', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    const onCreated = vi.fn();

    render(
      wrap(
        <CreateJobModal
          open
          onOpenChange={onOpenChange}
          salesEntry={makeEntry()}
          onCreated={onCreated}
        />,
      ),
    );

    await waitFor(() => {
      expect(screen.getByTestId('create-job-submit-btn')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('create-job-submit-btn'));

    await waitFor(() => {
      expect(mockCreateJobMutateAsync).toHaveBeenCalledTimes(1);
    });

    expect(mockCreateJobMutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({
        customer_id: 'cust-001',
        property_id: 'prop-001',
        job_type: 'spring_startup',
        description: 'Backyard sprinkler tune-up; gate code 1234.',
        priority_level: 0,
        estimated_duration_minutes: null,
        staffing_required: 1,
      }),
    );

    await waitFor(() => {
      expect(mockOverrideStatusMutateAsync).toHaveBeenCalledWith({
        id: 'entry-001',
        body: { status: 'closed_won' },
      });
    });

    expect(onCreated).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'job-001' }),
    );
    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(mockNavigate).toHaveBeenCalledWith('/jobs/job-001');
  });
});
