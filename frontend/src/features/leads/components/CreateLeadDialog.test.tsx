import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { CreateLeadDialog } from './CreateLeadDialog';
import { leadApi } from '../api/leadApi';

// Mock the API
vi.mock('../api/leadApi', () => ({
  leadApi: {
    createManual: vi.fn(),
    list: vi.fn(),
    followUpQueue: vi.fn(),
  },
}));

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
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

describe('CreateLeadDialog', () => {
  const mockOnOpenChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the dialog when open', () => {
    render(
      <CreateLeadDialog open={true} onOpenChange={mockOnOpenChange} />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByTestId('create-lead-dialog')).toBeInTheDocument();
    expect(screen.getByText('Add New Lead')).toBeInTheDocument();
  });

  it('does not render form content when closed', () => {
    render(
      <CreateLeadDialog open={false} onOpenChange={mockOnOpenChange} />,
      { wrapper: createWrapper() }
    );

    expect(screen.queryByTestId('create-lead-form')).not.toBeInTheDocument();
  });

  it('shows all form fields', () => {
    render(
      <CreateLeadDialog open={true} onOpenChange={mockOnOpenChange} />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByTestId('create-lead-name')).toBeInTheDocument();
    expect(screen.getByTestId('create-lead-phone')).toBeInTheDocument();
    expect(screen.getByTestId('create-lead-email')).toBeInTheDocument();
    expect(screen.getByTestId('create-lead-address')).toBeInTheDocument();
    expect(screen.getByTestId('create-lead-city')).toBeInTheDocument();
    expect(screen.getByTestId('create-lead-state')).toBeInTheDocument();
    expect(screen.getByTestId('create-lead-zip')).toBeInTheDocument();
    expect(screen.getByTestId('create-lead-situation')).toBeInTheDocument();
    expect(screen.getByTestId('create-lead-notes')).toBeInTheDocument();
  });

  it('shows validation errors when submitting empty required fields', async () => {
    const user = userEvent.setup();
    render(
      <CreateLeadDialog open={true} onOpenChange={mockOnOpenChange} />,
      { wrapper: createWrapper() }
    );

    await user.click(screen.getByTestId('create-lead-submit'));

    await waitFor(() => {
      expect(screen.getByText('Name is required')).toBeInTheDocument();
    });

    // API should not be called
    expect(leadApi.createManual).not.toHaveBeenCalled();
  });

  it('submits form with valid data', async () => {
    const user = userEvent.setup();
    vi.mocked(leadApi.createManual).mockResolvedValue({
      id: 'new-lead-id',
      name: 'John Doe',
      phone: '6125550123',
      email: null,
      address: null,
      city: null,
      state: null,
      zip_code: null,
      situation: 'exploring',
      notes: null,
      source_site: 'admin',
      status: 'new',
      assigned_to: null,
      customer_id: null,
      contacted_at: null,
      converted_at: null,
      lead_source: 'other',
      source_detail: 'Manual CRM entry',
      intake_tag: null,
      action_tags: ['NEEDS_CONTACT'],
      sms_consent: false,
      terms_accepted: false,
      email_marketing_consent: false,
      created_at: '2025-01-20T10:00:00Z',
      updated_at: '2025-01-20T10:00:00Z',
    });

    render(
      <CreateLeadDialog open={true} onOpenChange={mockOnOpenChange} />,
      { wrapper: createWrapper() }
    );

    await user.type(screen.getByTestId('create-lead-name'), 'John Doe');
    await user.type(screen.getByTestId('create-lead-phone'), '6125550123');
    await user.click(screen.getByTestId('create-lead-submit'));

    await waitFor(() => {
      expect(leadApi.createManual).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'John Doe',
          phone: '6125550123',
        })
      );
    });
  });

  it('preserves form data on API failure', async () => {
    const user = userEvent.setup();
    vi.mocked(leadApi.createManual).mockRejectedValue(new Error('Server error'));

    render(
      <CreateLeadDialog open={true} onOpenChange={mockOnOpenChange} />,
      { wrapper: createWrapper() }
    );

    await user.type(screen.getByTestId('create-lead-name'), 'John Doe');
    await user.type(screen.getByTestId('create-lead-phone'), '6125550123');
    await user.click(screen.getByTestId('create-lead-submit'));

    await waitFor(() => {
      // Form data should still be present
      expect(screen.getByTestId('create-lead-name')).toHaveValue('John Doe');
      expect(screen.getByTestId('create-lead-phone')).toHaveValue('6125550123');
    });

    // Dialog should remain open
    expect(mockOnOpenChange).not.toHaveBeenCalledWith(false);
  });

  it('closes dialog on cancel', async () => {
    const user = userEvent.setup();
    render(
      <CreateLeadDialog open={true} onOpenChange={mockOnOpenChange} />,
      { wrapper: createWrapper() }
    );

    await user.click(screen.getByText('Cancel'));
    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });
});
