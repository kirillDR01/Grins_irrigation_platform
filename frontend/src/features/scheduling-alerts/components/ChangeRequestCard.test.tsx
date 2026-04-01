/**
 * Tests for ChangeRequestCard component.
 * Validates: Requirements 30.6, 30.7, 30.8
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ChangeRequestCard } from './ChangeRequestCard';
import type { ChangeRequest } from '../types';

const mockApproveMutate = vi.fn();
const mockDenyMutate = vi.fn();

vi.mock('../hooks/useAlerts', () => ({
  useApproveChangeRequest: vi.fn(() => ({
    mutate: mockApproveMutate,
    isPending: false,
  })),
  useDenyChangeRequest: vi.fn(() => ({
    mutate: mockDenyMutate,
    isPending: false,
  })),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

const sampleRequest: ChangeRequest = {
  id: 'cr-1',
  resource_id: 's5',
  resource_name: 'Carlos R.',
  request_type: 'followup_job',
  details: { notes: 'Needs follow-up for valve replacement', parts_needed: 'PRV valve' },
  affected_job_id: 'j10',
  recommended_action: 'Schedule follow-up within 3 days',
  status: 'pending',
  admin_id: null,
  admin_notes: null,
  resolved_at: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

describe('ChangeRequestCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with data-testid', () => {
    render(<ChangeRequestCard request={sampleRequest} />, { wrapper: createWrapper() });
    expect(screen.getByTestId('change-request-card-cr-1')).toBeInTheDocument();
  });

  it('displays request type label', () => {
    render(<ChangeRequestCard request={sampleRequest} />, { wrapper: createWrapper() });
    expect(screen.getByText(/CHANGE REQUEST — Follow-Up Job Request/)).toBeInTheDocument();
  });

  it('displays resource name', () => {
    render(<ChangeRequestCard request={sampleRequest} />, { wrapper: createWrapper() });
    expect(screen.getByText('Carlos R.')).toBeInTheDocument();
  });

  it('displays AI recommended action', () => {
    render(<ChangeRequestCard request={sampleRequest} />, { wrapper: createWrapper() });
    expect(screen.getByText(/Schedule follow-up within 3 days/)).toBeInTheDocument();
  });

  it('displays field notes from details', () => {
    render(<ChangeRequestCard request={sampleRequest} />, { wrapper: createWrapper() });
    expect(screen.getByText(/Needs follow-up for valve replacement/)).toBeInTheDocument();
  });

  it('renders approve button for pending requests', () => {
    render(<ChangeRequestCard request={sampleRequest} />, { wrapper: createWrapper() });
    expect(screen.getByText('Approve')).toBeInTheDocument();
  });

  it('renders deny button for pending requests', () => {
    render(<ChangeRequestCard request={sampleRequest} />, { wrapper: createWrapper() });
    expect(screen.getByText('Deny')).toBeInTheDocument();
  });

  it('calls approve mutation when approve is clicked', async () => {
    const user = userEvent.setup();
    render(<ChangeRequestCard request={sampleRequest} />, { wrapper: createWrapper() });
    await user.click(screen.getByText('Approve'));
    expect(mockApproveMutate).toHaveBeenCalledWith({ id: 'cr-1' });
  });

  it('shows deny reason input on first deny click, then confirms', async () => {
    const user = userEvent.setup();
    render(<ChangeRequestCard request={sampleRequest} />, { wrapper: createWrapper() });

    // First click shows input
    await user.click(screen.getByText('Deny'));
    expect(screen.getByPlaceholderText('Reason for denial...')).toBeInTheDocument();
    expect(screen.getByText('Confirm Deny')).toBeInTheDocument();

    // Type reason and confirm
    await user.type(screen.getByPlaceholderText('Reason for denial...'), 'Not needed');
    await user.click(screen.getByText('Confirm Deny'));
    expect(mockDenyMutate).toHaveBeenCalledWith({
      id: 'cr-1',
      data: { reason: 'Not needed' },
    });
  });

  it('hides approve/deny buttons for non-pending requests', () => {
    const approvedRequest = { ...sampleRequest, status: 'approved' as const };
    render(<ChangeRequestCard request={approvedRequest} />, { wrapper: createWrapper() });
    expect(screen.queryByText('Approve')).not.toBeInTheDocument();
    expect(screen.queryByText('Deny')).not.toBeInTheDocument();
  });

  it('displays status badge', () => {
    render(<ChangeRequestCard request={sampleRequest} />, { wrapper: createWrapper() });
    expect(screen.getByText('pending')).toBeInTheDocument();
  });
});
