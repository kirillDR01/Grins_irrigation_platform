import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { SchedulingAlert } from '../types';

const mockMutate = vi.fn();

vi.mock('../hooks/useAlerts', () => ({
  useResolveAlert: () => ({ mutate: mockMutate, isPending: false }),
}));

import { AlertCard } from './AlertCard';

const alert: SchedulingAlert = {
  id: 'a1',
  alert_type: 'skill_mismatch',
  severity: 'critical',
  title: 'Backflow test assigned to uncertified tech',
  description: 'Carlos R. is not backflow-certified.',
  affected_job_ids: ['j1'],
  affected_staff_ids: ['s1'],
  criteria_triggered: [6],
  resolution_options: [
    { action: 'reassign', label: 'Reassign to Mike D.', description: 'Reassign' },
    { action: 'see_alternatives', label: 'See alternatives', description: 'View options' },
  ],
  status: 'active',
  schedule_date: '2026-02-16',
  created_at: new Date().toISOString(),
};

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('AlertCard', () => {
  it('renders with data-testid="alert-card-{id}"', () => {
    render(<AlertCard alert={alert} />, { wrapper });
    expect(screen.getByTestId('alert-card-a1')).toBeInTheDocument();
  });

  it('has red left border styling', () => {
    render(<AlertCard alert={alert} />, { wrapper });
    const card = screen.getByTestId('alert-card-a1');
    expect(card.className).toContain('border-red-500');
  });

  it('shows ⚠ ALERT prefix in title', () => {
    render(<AlertCard alert={alert} />, { wrapper });
    expect(screen.getByText(/⚠ ALERT/)).toBeInTheDocument();
  });

  it('shows alert title and description', () => {
    render(<AlertCard alert={alert} />, { wrapper });
    expect(screen.getByText('Backflow test assigned to uncertified tech')).toBeInTheDocument();
    expect(screen.getByText('Carlos R. is not backflow-certified.')).toBeInTheDocument();
  });

  it('renders resolution action buttons', () => {
    render(<AlertCard alert={alert} />, { wrapper });
    expect(screen.getByText('Reassign to Mike D.')).toBeInTheDocument();
    expect(screen.getByText('See alternatives')).toBeInTheDocument();
  });

  it('calls resolve mutation when action button clicked', () => {
    render(<AlertCard alert={alert} />, { wrapper });
    fireEvent.click(screen.getByText('Reassign to Mike D.'));
    expect(mockMutate).toHaveBeenCalledWith({
      id: 'a1',
      action: 'reassign',
      parameters: undefined,
    });
  });

  it('renders no action buttons when resolution_options is empty', () => {
    const noOptions = { ...alert, resolution_options: [] };
    render(<AlertCard alert={noOptions} />, { wrapper });
    expect(screen.queryByRole('button')).toBeNull();
  });
});
