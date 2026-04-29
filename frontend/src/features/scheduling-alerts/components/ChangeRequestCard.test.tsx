import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ChangeRequest } from '../types';

vi.mock('../hooks/useAlerts', () => ({
  useApproveChangeRequest: () => ({ mutate: vi.fn(), isPending: false }),
  useDenyChangeRequest: () => ({ mutate: vi.fn(), isPending: false }),
}));

import { ChangeRequestCard } from './ChangeRequestCard';

const pendingRequest: ChangeRequest = {
  id: 'cr1',
  resource_id: 'r1',
  resource_name: 'Carlos R.',
  request_type: 'delay_report',
  details: 'Running 30 minutes late on current job due to extra zones.',
  affected_job_id: 'j1',
  recommended_action: 'Notify next customer and adjust ETA.',
  status: 'pending',
  admin_notes: null,
  created_at: new Date().toISOString(),
};

const approvedRequest: ChangeRequest = {
  ...pendingRequest,
  id: 'cr2',
  status: 'approved',
};

const deniedRequest: ChangeRequest = {
  ...pendingRequest,
  id: 'cr3',
  status: 'denied',
};

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('ChangeRequestCard', () => {
  it('renders with data-testid="change-request-card-{id}"', () => {
    render(<ChangeRequestCard request={pendingRequest} />, { wrapper });
    expect(screen.getByTestId('change-request-card-cr1')).toBeInTheDocument();
  });

  it('shows resource name and request type', () => {
    render(<ChangeRequestCard request={pendingRequest} />, { wrapper });
    expect(screen.getByText(/Carlos R\./)).toBeInTheDocument();
    expect(screen.getByText(/delay report/i)).toBeInTheDocument();
  });

  it('shows field notes (details)', () => {
    render(<ChangeRequestCard request={pendingRequest} />, { wrapper });
    expect(screen.getByText('Running 30 minutes late on current job due to extra zones.')).toBeInTheDocument();
  });

  it('shows AI recommendation', () => {
    render(<ChangeRequestCard request={pendingRequest} />, { wrapper });
    expect(screen.getByText(/Notify next customer and adjust ETA\./)).toBeInTheDocument();
  });

  it('shows Approve and Deny buttons for pending requests', () => {
    render(<ChangeRequestCard request={pendingRequest} />, { wrapper });
    expect(screen.getByText('Approve')).toBeInTheDocument();
    expect(screen.getByText('Deny')).toBeInTheDocument();
  });

  it('shows deny reason input after clicking Deny', () => {
    render(<ChangeRequestCard request={pendingRequest} />, { wrapper });
    fireEvent.click(screen.getByText('Deny'));
    expect(screen.getByPlaceholderText('Reason for denial...')).toBeInTheDocument();
    expect(screen.getByText('Confirm Deny')).toBeInTheDocument();
  });

  it('shows approved status badge for approved requests', () => {
    render(<ChangeRequestCard request={approvedRequest} />, { wrapper });
    expect(screen.getByText('approved')).toBeInTheDocument();
    expect(screen.queryByText('Approve')).toBeNull();
  });

  it('shows denied status badge for denied requests', () => {
    render(<ChangeRequestCard request={deniedRequest} />, { wrapper });
    expect(screen.getByText('denied')).toBeInTheDocument();
  });
});
