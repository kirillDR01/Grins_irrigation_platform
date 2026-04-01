/**
 * Tests for SuggestionCard component.
 * Validates: Requirements 30.6, 30.7, 30.8
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SuggestionCard } from './SuggestionCard';
import type { SchedulingAlert } from '../types';

const mockResolveMutate = vi.fn();
const mockDismissMutate = vi.fn();

vi.mock('../hooks/useAlerts', () => ({
  useResolveAlert: vi.fn(() => ({
    mutate: mockResolveMutate,
    isPending: false,
  })),
  useDismissAlert: vi.fn(() => ({
    mutate: mockDismissMutate,
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

const sampleSuggestion: SchedulingAlert = {
  id: 'sug-1',
  alert_type: 'route_swap',
  severity: 'suggestion',
  title: 'Swap 2 jobs to save 28 min',
  description: 'Swap jobs between Sarah K. and Carlos R. on Monday — saves 28 min drive time.',
  affected_job_ids: ['j3', 'j4'],
  affected_staff_ids: ['s2', 's3'],
  criteria_triggered: [1, 2],
  resolution_options: [
    { action: 'accept_swap', label: 'Accept', description: 'Apply the swap', parameters: {} },
    { action: 'see_map', label: 'See on map', description: 'View routes', parameters: {} },
  ],
  status: 'active',
  resolved_by: null,
  resolved_action: null,
  resolved_at: null,
  schedule_date: '2025-03-04',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

describe('SuggestionCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with data-testid', () => {
    render(<SuggestionCard suggestion={sampleSuggestion} />, { wrapper: createWrapper() });
    expect(screen.getByTestId('suggestion-card-sug-1')).toBeInTheDocument();
  });

  it('renders green styling', () => {
    render(<SuggestionCard suggestion={sampleSuggestion} />, { wrapper: createWrapper() });
    const card = screen.getByTestId('suggestion-card-sug-1');
    expect(card.className).toContain('bg-green');
    expect(card.className).toContain('border-green');
  });

  it('displays suggestion type label', () => {
    render(<SuggestionCard suggestion={sampleSuggestion} />, { wrapper: createWrapper() });
    expect(screen.getByText(/SUGGESTION — Route Swap/)).toBeInTheDocument();
  });

  it('displays title and description', () => {
    render(<SuggestionCard suggestion={sampleSuggestion} />, { wrapper: createWrapper() });
    expect(screen.getByText('Swap 2 jobs to save 28 min')).toBeInTheDocument();
    expect(screen.getByText(/saves 28 min drive time/)).toBeInTheDocument();
  });

  it('renders accept action buttons', () => {
    render(<SuggestionCard suggestion={sampleSuggestion} />, { wrapper: createWrapper() });
    expect(screen.getByText('Accept')).toBeInTheDocument();
    expect(screen.getByText('See on map')).toBeInTheDocument();
  });

  it('renders dismiss button', () => {
    render(<SuggestionCard suggestion={sampleSuggestion} />, { wrapper: createWrapper() });
    expect(screen.getByText('Leave as-is')).toBeInTheDocument();
  });

  it('calls resolve mutation when accept is clicked', async () => {
    const user = userEvent.setup();
    render(<SuggestionCard suggestion={sampleSuggestion} />, { wrapper: createWrapper() });
    await user.click(screen.getByText('Accept'));
    expect(mockResolveMutate).toHaveBeenCalledWith({
      id: 'sug-1',
      data: { action: 'accept_swap', parameters: {} },
    });
  });

  it('calls dismiss mutation when Leave as-is is clicked', async () => {
    const user = userEvent.setup();
    render(<SuggestionCard suggestion={sampleSuggestion} />, { wrapper: createWrapper() });
    await user.click(screen.getByText('Leave as-is'));
    expect(mockDismissMutate).toHaveBeenCalledWith({ id: 'sug-1' });
  });
});
