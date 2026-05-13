import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { StaffWorkflowButtons } from './StaffWorkflowButtons';

// Mock the mutation hooks. Cluster D Item 5 routes the On-My-Way action
// through the job-side canonical hook; the other two stay on the
// appointment-side mutations.
const mockOnMyWayMutate = vi.fn();
const mockArrivedMutate = vi.fn();
const mockCompletedMutate = vi.fn();

vi.mock('../hooks/useAppointmentMutations', () => ({
  useMarkAppointmentArrived: () => ({
    mutateAsync: mockArrivedMutate,
    isPending: false,
  }),
  useMarkAppointmentCompleted: () => ({
    mutateAsync: mockCompletedMutate,
    isPending: false,
  }),
}));

vi.mock('@/features/jobs/hooks', () => ({
  useOnMyWay: () => ({
    mutateAsync: mockOnMyWayMutate,
    isPending: false,
  }),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('StaffWorkflowButtons', () => {
  it('shows "On My Way" button when status is confirmed', () => {
    render(
      <StaffWorkflowButtons appointmentId="apt-1" jobId="job-1" status="confirmed" />,
      { wrapper: createWrapper() }
    );
    expect(screen.getByTestId('on-my-way-btn')).toBeInTheDocument();
    expect(screen.getByText('On My Way')).toBeInTheDocument();
    expect(screen.queryByTestId('job-started-btn')).not.toBeInTheDocument();
    expect(screen.queryByTestId('job-complete-btn')).not.toBeInTheDocument();
  });

  it('shows "Job Started" button when status is en_route', () => {
    render(
      <StaffWorkflowButtons appointmentId="apt-1" jobId="job-1" status="en_route" />,
      { wrapper: createWrapper() }
    );
    expect(screen.getByTestId('job-started-btn')).toBeInTheDocument();
    expect(screen.getByText('Job Started')).toBeInTheDocument();
    expect(screen.queryByTestId('on-my-way-btn')).not.toBeInTheDocument();
  });

  it('shows "Job Complete" button when status is in_progress', () => {
    render(
      <StaffWorkflowButtons
        appointmentId="apt-1"
        jobId="job-1"
        status="in_progress"
        hasPaymentOrInvoice={true}
      />,
      { wrapper: createWrapper() }
    );
    expect(screen.getByTestId('job-complete-btn')).toBeInTheDocument();
    expect(screen.getByText('Job Complete')).toBeInTheDocument();
  });

  it('disables "Job Complete" when no payment or invoice (Req 36)', () => {
    render(
      <StaffWorkflowButtons
        appointmentId="apt-1"
        jobId="job-1"
        status="in_progress"
        hasPaymentOrInvoice={false}
      />,
      { wrapper: createWrapper() }
    );
    const btn = screen.getByTestId('job-complete-btn');
    expect(btn).toBeDisabled();
    expect(screen.getByTestId('complete-tooltip')).toBeInTheDocument();
    expect(
      screen.getByText('Please collect payment or send an invoice before completing this job')
    ).toBeInTheDocument();
  });

  it('enables "Job Complete" when payment or invoice exists', () => {
    render(
      <StaffWorkflowButtons
        appointmentId="apt-1"
        jobId="job-1"
        status="in_progress"
        hasPaymentOrInvoice={true}
      />,
      { wrapper: createWrapper() }
    );
    const btn = screen.getByTestId('job-complete-btn');
    expect(btn).not.toBeDisabled();
    expect(screen.queryByTestId('complete-tooltip')).not.toBeInTheDocument();
  });

  it('calls useOnMyWay mutation with jobId when "On My Way" is clicked', async () => {
    const user = userEvent.setup();
    mockOnMyWayMutate.mockResolvedValue({});
    render(
      <StaffWorkflowButtons appointmentId="apt-1" jobId="job-1" status="confirmed" />,
      { wrapper: createWrapper() }
    );
    await user.click(screen.getByTestId('on-my-way-btn'));
    expect(mockOnMyWayMutate).toHaveBeenCalledWith('job-1');
  });

  it('calls arrived mutation when "Job Started" is clicked', async () => {
    const user = userEvent.setup();
    mockArrivedMutate.mockResolvedValue({});
    render(
      <StaffWorkflowButtons appointmentId="apt-1" jobId="job-1" status="en_route" />,
      { wrapper: createWrapper() }
    );
    await user.click(screen.getByTestId('job-started-btn'));
    expect(mockArrivedMutate).toHaveBeenCalledWith('apt-1');
  });

  it('calls completed mutation when "Job Complete" is clicked', async () => {
    const user = userEvent.setup();
    mockCompletedMutate.mockResolvedValue({});
    render(
      <StaffWorkflowButtons
        appointmentId="apt-1"
        jobId="job-1"
        status="in_progress"
        hasPaymentOrInvoice={true}
      />,
      { wrapper: createWrapper() }
    );
    await user.click(screen.getByTestId('job-complete-btn'));
    expect(mockCompletedMutate).toHaveBeenCalledWith('apt-1');
  });

  it('shows nothing for terminal statuses', () => {
    const { container } = render(
      <StaffWorkflowButtons appointmentId="apt-1" jobId="job-1" status="completed" />,
      { wrapper: createWrapper() }
    );
    expect(screen.queryByTestId('on-my-way-btn')).not.toBeInTheDocument();
    expect(screen.queryByTestId('job-started-btn')).not.toBeInTheDocument();
    expect(screen.queryByTestId('job-complete-btn')).not.toBeInTheDocument();
    // Container should have the wrapper div but no buttons
    expect(container.querySelectorAll('button')).toHaveLength(0);
  });
});
