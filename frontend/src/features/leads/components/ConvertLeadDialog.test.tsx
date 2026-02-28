import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { ConvertLeadDialog } from './ConvertLeadDialog';
import { leadApi } from '../api/leadApi';
import type { Lead } from '../types';

// Mock the lead API
vi.mock('../api/leadApi', () => ({
  leadApi: {
    convert: vi.fn(),
    list: vi.fn(),
    getById: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
}));

// Mock react-router-dom's useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// --- Mock Data ---

const twoWordNameLead: Lead = {
  id: 'lead-001',
  name: 'John Doe',
  phone: '6125551234',
  email: 'john@example.com',
  zip_code: '55424',
  situation: 'new_system',
  notes: 'Large backyard',
  source_site: 'residential',
  status: 'qualified',
  assigned_to: null,
  customer_id: null,
  contacted_at: '2025-01-21T09:00:00Z',
  converted_at: null,
  created_at: '2025-01-20T10:00:00Z',
  updated_at: '2025-01-20T10:00:00Z',
};

const singleWordNameLead: Lead = {
  ...twoWordNameLead,
  id: 'lead-002',
  name: 'Viktor',
};

const repairLead: Lead = {
  ...twoWordNameLead,
  id: 'lead-003',
  name: 'Jane Smith',
  situation: 'repair',
};

// --- Helpers ---

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

// --- Tests ---

describe('ConvertLeadDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ---- Dialog rendering ----

  it('renders dialog with correct title and buttons when open', () => {
    render(
      <ConvertLeadDialog
        lead={twoWordNameLead}
        open={true}
        onOpenChange={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText('Convert Lead to Customer')).toBeInTheDocument();
    expect(screen.getByTestId('convert-submit-btn')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('does not render form content when dialog is closed', () => {
    render(
      <ConvertLeadDialog
        lead={twoWordNameLead}
        open={false}
        onOpenChange={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.queryByTestId('convert-first-name')).not.toBeInTheDocument();
  });

  // ---- Name pre-fill from auto-split ----

  it('pre-fills first and last name from two-word name "John Doe"', () => {
    render(
      <ConvertLeadDialog
        lead={twoWordNameLead}
        open={true}
        onOpenChange={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    const firstNameInput = screen.getByTestId('convert-first-name') as HTMLInputElement;
    const lastNameInput = screen.getByTestId('convert-last-name') as HTMLInputElement;

    expect(firstNameInput.value).toBe('John');
    expect(lastNameInput.value).toBe('Doe');
  });

  it('pre-fills first name only for single-word name "Viktor"', () => {
    render(
      <ConvertLeadDialog
        lead={singleWordNameLead}
        open={true}
        onOpenChange={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    const firstNameInput = screen.getByTestId('convert-first-name') as HTMLInputElement;
    const lastNameInput = screen.getByTestId('convert-last-name') as HTMLInputElement;

    expect(firstNameInput.value).toBe('Viktor');
    expect(lastNameInput.value).toBe('');
  });

  // ---- Job creation toggle ----

  it('shows job description field when create job toggle is on (default)', () => {
    render(
      <ConvertLeadDialog
        lead={twoWordNameLead}
        open={true}
        onOpenChange={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    // Toggle should be checked by default
    expect(screen.getByTestId('convert-create-job')).toBeInTheDocument();
    // Job description field should be visible
    expect(screen.getByTestId('convert-job-description')).toBeInTheDocument();
  });

  it('auto-suggests job description based on situation', () => {
    render(
      <ConvertLeadDialog
        lead={repairLead}
        open={true}
        onOpenChange={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    const jobDescInput = screen.getByTestId('convert-job-description') as HTMLInputElement;
    expect(jobDescInput.value).toBe('Irrigation system repair');
  });

  it('hides job description field when create job toggle is turned off', async () => {
    const user = userEvent.setup();

    render(
      <ConvertLeadDialog
        lead={twoWordNameLead}
        open={true}
        onOpenChange={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    // Job description should be visible initially
    expect(screen.getByTestId('convert-job-description')).toBeInTheDocument();

    // Click the switch to toggle off
    await user.click(screen.getByTestId('convert-create-job'));

    // Job description should be hidden
    await waitFor(() => {
      expect(screen.queryByTestId('convert-job-description')).not.toBeInTheDocument();
    });
  });

  // ---- Form submission ----

  it('calls convert mutation with correct data on submit', async () => {
    const user = userEvent.setup();
    vi.mocked(leadApi.convert).mockResolvedValue({
      success: true,
      lead_id: 'lead-001',
      customer_id: 'cust-new-001',
      job_id: 'job-new-001',
      message: 'Lead successfully converted to customer.',
    });

    const onOpenChange = vi.fn();

    render(
      <ConvertLeadDialog
        lead={twoWordNameLead}
        open={true}
        onOpenChange={onOpenChange}
      />,
      { wrapper: createWrapper() }
    );

    // Click submit
    await user.click(screen.getByTestId('convert-submit-btn'));

    await waitFor(() => {
      expect(leadApi.convert).toHaveBeenCalledWith('lead-001', {
        first_name: 'John',
        last_name: 'Doe',
        create_job: true,
        job_description: 'New irrigation system installation',
      });
    });

    // Dialog should close
    await waitFor(() => {
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });

    // Should navigate to new customer
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/customers/cust-new-001');
    });
  });

  it('submits without job_description when create job is toggled off', async () => {
    const user = userEvent.setup();
    vi.mocked(leadApi.convert).mockResolvedValue({
      success: true,
      lead_id: 'lead-001',
      customer_id: 'cust-new-001',
      job_id: null,
      message: 'Lead successfully converted to customer.',
    });

    render(
      <ConvertLeadDialog
        lead={twoWordNameLead}
        open={true}
        onOpenChange={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    // Toggle off job creation
    await user.click(screen.getByTestId('convert-create-job'));

    // Submit
    await user.click(screen.getByTestId('convert-submit-btn'));

    await waitFor(() => {
      expect(leadApi.convert).toHaveBeenCalledWith('lead-001', {
        first_name: 'John',
        last_name: 'Doe',
        create_job: false,
        job_description: undefined,
      });
    });
  });

  it('disables submit button when first name is empty', async () => {
    const user = userEvent.setup();

    render(
      <ConvertLeadDialog
        lead={twoWordNameLead}
        open={true}
        onOpenChange={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    const firstNameInput = screen.getByTestId('convert-first-name');
    // Clear the first name
    await user.clear(firstNameInput);

    expect(screen.getByTestId('convert-submit-btn')).toBeDisabled();
  });
});
