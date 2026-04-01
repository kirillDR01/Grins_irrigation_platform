/**
 * Tests for AlertCard component.
 * Validates: Requirements 30.6, 30.7, 30.8
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AlertCard } from './AlertCard';
import type { SchedulingAlert } from '../types';

const mockMutate = vi.fn();

vi.mock('../hooks/useAlerts', () => ({
  useResolveAlert: vi.fn(() => ({
    mutate: mockMutate,
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

const sampleAlert: SchedulingAlert = {
  id: 'alert-1',
  alert_type: 'skill_mismatch',
  severity: 'critical',
  title: 'Backflow test assigned to uncertified tech',
  description: 'Carlos R. is not backflow-certified but assigned to backflow test on Tue.',
  affected_job_ids: ['j10'],
  affected_staff_ids: ['s5'],
  criteria_triggered: [6],
  resolution_options: [
    { action: 'reassign_mike', label: 'Reassign to Mike D.', description: 'Mike is certified', parameters: { staff_id: 's1' } },
    { action: 'see_alternatives', label: 'See alternatives', description: 'View other options', parameters: {} },
  ],
  status: 'active',
  resolved_by: null,
  resolved_action: null,
  resolved_at: null,
  schedule_date: '2025-03-04',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

describe('AlertCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with data-testid', () => {
    render(<AlertCard alert={sampleAlert} />, { wrapper: createWrapper() });
    expect(screen.getByTestId('alert-card-alert-1')).toBeInTheDocument();
  });

  it('renders red/critical styling', () => {
    render(<AlertCard alert={sampleAlert} />, { wrapper: createWrapper() });
    const card = screen.getByTestId('alert-card-alert-1');
    expect(card.className).toContain('bg-red');
    expect(card.className).toContain('border-red');
  });

  it('displays alert type label', () => {
    render(<AlertCard alert={sampleAlert} />, { wrapper: createWrapper() });
    expect(screen.getByText(/ALERT — Skill Mismatch/)).toBeInTheDocument();
  });

  it('displays alert title and description', () => {
    render(<AlertCard alert={sampleAlert} />, { wrapper: createWrapper() });
    expect(screen.getByText('Backflow test assigned to uncertified tech')).toBeInTheDocument();
    expect(screen.getByText(/Carlos R. is not backflow-certified/)).toBeInTheDocument();
  });

  it('renders resolution action buttons', () => {
    render(<AlertCard alert={sampleAlert} />, { wrapper: createWrapper() });
    expect(screen.getByText('Reassign to Mike D.')).toBeInTheDocument();
    expect(screen.getByText('See alternatives')).toBeInTheDocument();
  });

  it('calls resolve mutation when resolution button is clicked', async () => {
    const user = userEvent.setup();
    render(<AlertCard alert={sampleAlert} />, { wrapper: createWrapper() });
    await user.click(screen.getByText('Reassign to Mike D.'));
    expect(mockMutate).toHaveBeenCalledWith({
      id: 'alert-1',
      data: { action: 'reassign_mike', parameters: { staff_id: 's1' } },
    });
  });

  it('renders no buttons when resolution_options is empty', () => {
    const alertNoOptions = { ...sampleAlert, resolution_options: [] };
    render(<AlertCard alert={alertNoOptions} />, { wrapper: createWrapper() });
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
