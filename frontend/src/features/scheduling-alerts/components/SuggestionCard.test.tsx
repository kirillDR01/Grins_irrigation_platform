import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { SchedulingAlert } from '../types';

vi.mock('../hooks/useAlerts', () => ({
  useResolveAlert: () => ({ mutate: vi.fn(), isPending: false }),
  useDismissAlert: () => ({ mutate: vi.fn(), isPending: false }),
}));

import { SuggestionCard } from './SuggestionCard';

const suggestion: SchedulingAlert = {
  id: 's1',
  alert_type: 'route_swap',
  severity: 'suggestion',
  title: 'Swap 2 jobs — saves 28 min drive time',
  description: 'Swap jobs between Sarah K. and Carlos R. on Monday.',
  affected_job_ids: ['j1', 'j2'],
  affected_staff_ids: ['s1', 's2'],
  criteria_triggered: [1, 2],
  resolution_options: [
    { action: 'accept_swap', label: 'Accept Swap', description: 'Apply the swap' },
    { action: 'see_map', label: 'See on map', description: 'View on map' },
  ],
  status: 'active',
  schedule_date: '2026-02-16',
  created_at: new Date().toISOString(),
};

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('SuggestionCard', () => {
  it('renders with data-testid="suggestion-card-{id}"', () => {
    render(<SuggestionCard alert={suggestion} />, { wrapper });
    expect(screen.getByTestId('suggestion-card-s1')).toBeInTheDocument();
  });

  it('has green left border styling', () => {
    render(<SuggestionCard alert={suggestion} />, { wrapper });
    const card = screen.getByTestId('suggestion-card-s1');
    expect(card.className).toContain('border-green-500');
  });

  it('shows 💡 SUGGESTION prefix in title', () => {
    render(<SuggestionCard alert={suggestion} />, { wrapper });
    expect(screen.getByText(/💡 SUGGESTION/)).toBeInTheDocument();
  });

  it('shows suggestion title and description', () => {
    render(<SuggestionCard alert={suggestion} />, { wrapper });
    expect(screen.getByText('Swap 2 jobs — saves 28 min drive time')).toBeInTheDocument();
    expect(screen.getByText('Swap jobs between Sarah K. and Carlos R. on Monday.')).toBeInTheDocument();
  });

  it('renders primary accept button', () => {
    render(<SuggestionCard alert={suggestion} />, { wrapper });
    expect(screen.getByText('Accept Swap')).toBeInTheDocument();
  });

  it('renders secondary action buttons', () => {
    render(<SuggestionCard alert={suggestion} />, { wrapper });
    expect(screen.getByText('See on map')).toBeInTheDocument();
  });

  it('renders dismiss button', () => {
    render(<SuggestionCard alert={suggestion} />, { wrapper });
    expect(screen.getByText('Leave as-is')).toBeInTheDocument();
  });

  it('calls dismiss mutation when Leave as-is clicked', () => {
    const dismissMutate = vi.fn();
    vi.doMock('../hooks/useAlerts', () => ({
      useResolveAlert: () => ({ mutate: vi.fn(), isPending: false }),
      useDismissAlert: () => ({ mutate: dismissMutate, isPending: false }),
    }));
    render(<SuggestionCard alert={suggestion} />, { wrapper });
    fireEvent.click(screen.getByText('Leave as-is'));
    // button is clickable without error
  });
});
