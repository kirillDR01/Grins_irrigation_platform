import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { JobForm } from './JobForm';
import { jobApi } from '../api/jobApi';
import type { Job } from '../types';

// Mock the API
vi.mock('../api/jobApi', () => ({
  jobApi: {
    create: vi.fn(),
    update: vi.fn(),
  },
}));

const mockJob: Job = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  customer_id: '123e4567-e89b-12d3-a456-426614174001',
  property_id: null,
  service_offering_id: null,
  job_type: 'spring_startup',
  category: 'ready_to_schedule',
  status: 'requested',
  description: 'Spring startup for irrigation system',
  estimated_duration_minutes: 60,
  priority_level: 0,
  weather_sensitive: false,
  staffing_required: 1,
  equipment_required: null,
  materials_required: null,
  quoted_amount: 150,
  final_amount: null,
  source: 'website',
  source_details: null,
  payment_collected_on_site: false,
  requested_at: '2025-01-20T10:00:00Z',
  approved_at: null,
  scheduled_at: null,
  started_at: null,
  completed_at: null,
  closed_at: null,
  created_at: '2025-01-20T10:00:00Z',
  updated_at: '2025-01-20T10:00:00Z',
};

// Helper to select value in Radix UI Select via hidden native select
function selectOption(container: HTMLElement, testId: string, value: string) {
  // Find the trigger button by testId
  const trigger = container.querySelector(`[data-testid="${testId}"]`);
  if (!trigger) throw new Error(`Select trigger not found: ${testId}`);

  // Find the hidden native select that Radix creates (sibling of the trigger)
  const hiddenSelect = trigger.parentElement?.querySelector(
    'select[aria-hidden="true"]'
  ) as HTMLSelectElement | null;

  if (hiddenSelect) {
    // Change the hidden select value
    fireEvent.change(hiddenSelect, { target: { value } });
  }
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>{children}</BrowserRouter>
      </QueryClientProvider>
    );
  };
}

describe('JobForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders form with empty fields for new job', () => {
    render(<JobForm customerId="123e4567-e89b-12d3-a456-426614174001" />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByTestId('job-form')).toBeInTheDocument();
    expect(screen.getByTestId('job-type-select')).toBeInTheDocument();
    expect(screen.getByTestId('description-input')).toBeInTheDocument();
    expect(screen.getByTestId('priority-select')).toBeInTheDocument();
    expect(screen.getByTestId('submit-btn')).toHaveTextContent('Create Job');
  });

  it('renders form with populated fields for editing', () => {
    render(<JobForm job={mockJob} />, { wrapper: createWrapper() });

    expect(screen.getByTestId('job-form')).toBeInTheDocument();
    expect(screen.getByTestId('description-input')).toHaveValue(
      'Spring startup for irrigation system'
    );
    expect(screen.getByTestId('submit-btn')).toHaveTextContent('Update Job');
  });

  it('shows validation error for missing job type', async () => {
    const user = userEvent.setup();
    render(<JobForm customerId="123e4567-e89b-12d3-a456-426614174001" />, {
      wrapper: createWrapper(),
    });

    // Submit without selecting job type
    await user.click(screen.getByTestId('submit-btn'));

    await waitFor(() => {
      expect(screen.getByText('Job type is required')).toBeInTheDocument();
    });
  });

  it('submits form with valid data for new job', async () => {
    const user = userEvent.setup();
    const onSuccess = vi.fn();
    vi.mocked(jobApi.create).mockResolvedValue(mockJob);

    const { container } = render(
      <JobForm
        customerId="123e4567-e89b-12d3-a456-426614174001"
        onSuccess={onSuccess}
      />,
      { wrapper: createWrapper() }
    );

    // Select job type using hidden native select
    selectOption(container, 'job-type-select', 'spring_startup');

    // Fill description
    await user.type(
      screen.getByTestId('description-input'),
      'Test job description'
    );

    // Submit form
    await user.click(screen.getByTestId('submit-btn'));

    await waitFor(() => {
      expect(jobApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          customer_id: '123e4567-e89b-12d3-a456-426614174001',
          job_type: 'spring_startup',
          description: 'Test job description',
        })
      );
    });

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it('submits form with valid data for editing', async () => {
    const user = userEvent.setup();
    const onSuccess = vi.fn();
    vi.mocked(jobApi.update).mockResolvedValue({
      ...mockJob,
      description: 'Updated description',
    });

    render(<JobForm job={mockJob} onSuccess={onSuccess} />, {
      wrapper: createWrapper(),
    });

    // Update description
    const descriptionInput = screen.getByTestId('description-input');
    await user.clear(descriptionInput);
    await user.type(descriptionInput, 'Updated description');

    // Submit form
    await user.click(screen.getByTestId('submit-btn'));

    await waitFor(() => {
      expect(jobApi.update).toHaveBeenCalledWith(
        mockJob.id,
        expect.objectContaining({
          description: 'Updated description',
        })
      );
    });

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it('calls onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();

    render(
      <JobForm
        customerId="123e4567-e89b-12d3-a456-426614174001"
        onCancel={onCancel}
      />,
      { wrapper: createWrapper() }
    );

    await user.click(screen.getByText('Cancel'));

    expect(onCancel).toHaveBeenCalled();
  });

  it('renders priority select dropdown', () => {
    render(<JobForm customerId="123e4567-e89b-12d3-a456-426614174001" />, {
      wrapper: createWrapper(),
    });

    // Verify priority select is present
    expect(screen.getByTestId('priority-select')).toBeInTheDocument();
    // Default value is 0 (Normal), so it shows "Normal" - use getAllByText since there are multiple
    expect(screen.getAllByText('Normal').length).toBeGreaterThan(0);
  });

  it('renders staffing input with default value', () => {
    render(<JobForm customerId="123e4567-e89b-12d3-a456-426614174001" />, {
      wrapper: createWrapper(),
    });

    // Verify staffing input is present with default value of 1
    const staffingInput = screen.getByTestId('staffing-input');
    expect(staffingInput).toBeInTheDocument();
    expect(staffingInput).toHaveValue(1);
  });

  it('allows setting duration and amount', async () => {
    const user = userEvent.setup();
    vi.mocked(jobApi.create).mockResolvedValue(mockJob);

    const { container } = render(
      <JobForm customerId="123e4567-e89b-12d3-a456-426614174001" />,
      { wrapper: createWrapper() }
    );

    // Select job type first
    selectOption(container, 'job-type-select', 'diagnostic');

    // Set duration
    await user.type(screen.getByTestId('duration-input'), '90');

    // Set amount
    await user.type(screen.getByTestId('amount-input'), '200');

    // Submit form
    await user.click(screen.getByTestId('submit-btn'));

    await waitFor(() => {
      expect(jobApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          estimated_duration_minutes: 90,
          quoted_amount: 200,
        })
      );
    });
  });

  it('allows toggling weather sensitive', async () => {
    const user = userEvent.setup();
    vi.mocked(jobApi.create).mockResolvedValue(mockJob);

    const { container } = render(
      <JobForm customerId="123e4567-e89b-12d3-a456-426614174001" />,
      { wrapper: createWrapper() }
    );

    // Select job type first
    selectOption(container, 'job-type-select', 'landscaping');

    // Toggle weather sensitive
    await user.click(screen.getByTestId('weather-checkbox'));

    // Submit form
    await user.click(screen.getByTestId('submit-btn'));

    await waitFor(() => {
      expect(jobApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          weather_sensitive: true,
        })
      );
    });
  });

  it('renders source select dropdown', () => {
    render(<JobForm customerId="123e4567-e89b-12d3-a456-426614174001" />, {
      wrapper: createWrapper(),
    });

    // Verify source select is present
    expect(screen.getByTestId('source-select')).toBeInTheDocument();
    expect(screen.getByText('Select source')).toBeInTheDocument();
  });
});
