/**
 * Tests for ResourceSuggestionsList component.
 * Validates: Requirements 30.6, 30.7, 30.8
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ResourceSuggestionsList } from './ResourceSuggestionsList';
import type { ResourceSuggestion } from '../types';

const mockSuggestions: ResourceSuggestion[] = [
  {
    id: 'rs1',
    suggestion_type: 'prejob_prep',
    title: 'Review customer history',
    description: 'Customer had 3 service calls last year. Check previous notes.',
    job_id: 'j30',
    action_label: 'View History',
    action_url: '/customers/c1/history',
    created_at: new Date().toISOString(),
    is_dismissed: false,
  },
  {
    id: 'rs2',
    suggestion_type: 'upsell_opportunity',
    title: 'Equipment upgrade available',
    description: 'Controller is 8 years old. Recommend smart controller upgrade.',
    job_id: 'j31',
    action_label: 'Create Quote',
    action_url: '/quotes/new?job=j31',
    created_at: new Date().toISOString(),
    is_dismissed: false,
  },
  {
    id: 'rs3',
    suggestion_type: 'parts_low',
    title: 'Parts running low',
    description: 'Only 2 PRV valves left. Nearest supply house: 10 min away.',
    job_id: null,
    action_label: 'Navigate to Supply',
    action_url: null,
    created_at: new Date().toISOString(),
    is_dismissed: false,
  },
];

const mockDismissMutate = vi.fn();

vi.mock('../hooks/useResourceSchedule', () => ({
  useResourceSuggestions: vi.fn(() => ({
    data: mockSuggestions,
    isLoading: false,
    error: null,
  })),
  useDismissResourceSuggestion: vi.fn(() => ({
    mutate: mockDismissMutate,
  })),
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  ClipboardList: () => <span>📋</span>,
  TrendingUp: () => <span>📈</span>,
  Clock: () => <span>🕐</span>,
  Package: () => <span>📦</span>,
  Hourglass: () => <span>⏳</span>,
  X: () => <span>✕</span>,
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('ResourceSuggestionsList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with data-testid', () => {
    render(<ResourceSuggestionsList />, { wrapper: createWrapper() });
    expect(screen.getByTestId('resource-suggestions-list')).toBeInTheDocument();
  });

  it('renders suggestion items with data-testid', () => {
    render(<ResourceSuggestionsList />, { wrapper: createWrapper() });
    expect(screen.getByTestId('resource-suggestion-rs1')).toBeInTheDocument();
    expect(screen.getByTestId('resource-suggestion-rs2')).toBeInTheDocument();
    expect(screen.getByTestId('resource-suggestion-rs3')).toBeInTheDocument();
  });

  it('displays suggestion titles', () => {
    render(<ResourceSuggestionsList />, { wrapper: createWrapper() });
    expect(screen.getByText('Review customer history')).toBeInTheDocument();
    expect(screen.getByText('Equipment upgrade available')).toBeInTheDocument();
    expect(screen.getByText('Parts running low')).toBeInTheDocument();
  });

  it('displays suggestion descriptions', () => {
    render(<ResourceSuggestionsList />, { wrapper: createWrapper() });
    expect(screen.getByText(/Customer had 3 service calls/)).toBeInTheDocument();
    expect(screen.getByText(/Controller is 8 years old/)).toBeInTheDocument();
  });

  it('displays suggestion count badge', () => {
    render(<ResourceSuggestionsList />, { wrapper: createWrapper() });
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('renders action buttons when action_label is present', () => {
    render(<ResourceSuggestionsList />, { wrapper: createWrapper() });
    expect(screen.getByText('View History')).toBeInTheDocument();
    expect(screen.getByText('Create Quote')).toBeInTheDocument();
    expect(screen.getByText('Navigate to Supply')).toBeInTheDocument();
  });

  it('renders dismiss buttons for each suggestion', () => {
    render(<ResourceSuggestionsList />, { wrapper: createWrapper() });
    const dismissButtons = screen.getAllByLabelText('Dismiss suggestion');
    expect(dismissButtons).toHaveLength(3);
  });

  it('calls dismiss mutation when dismiss is clicked', async () => {
    const user = userEvent.setup();
    render(<ResourceSuggestionsList />, { wrapper: createWrapper() });
    const dismissButtons = screen.getAllByLabelText('Dismiss suggestion');
    await user.click(dismissButtons[0]);
    expect(mockDismissMutate).toHaveBeenCalledWith('rs1');
  });

  it('filters out dismissed suggestions', async () => {
    const { useResourceSuggestions } = await import('../hooks/useResourceSchedule');
    (useResourceSuggestions as ReturnType<typeof vi.fn>).mockReturnValue({
      data: [
        { ...mockSuggestions[0], is_dismissed: true },
        mockSuggestions[1],
      ],
      isLoading: false,
      error: null,
    });
    render(<ResourceSuggestionsList />, { wrapper: createWrapper() });
    expect(screen.queryByTestId('resource-suggestion-rs1')).not.toBeInTheDocument();
    expect(screen.getByTestId('resource-suggestion-rs2')).toBeInTheDocument();
  });

  it('shows loading state', async () => {
    const { useResourceSuggestions } = await import('../hooks/useResourceSchedule');
    (useResourceSuggestions as ReturnType<typeof vi.fn>).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });
    render(<ResourceSuggestionsList />, { wrapper: createWrapper() });
    expect(screen.getByText('Loading suggestions…')).toBeInTheDocument();
  });

  it('shows empty state when no suggestions', async () => {
    const { useResourceSuggestions } = await import('../hooks/useResourceSchedule');
    (useResourceSuggestions as ReturnType<typeof vi.fn>).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });
    render(<ResourceSuggestionsList />, { wrapper: createWrapper() });
    expect(screen.getByText('No suggestions right now')).toBeInTheDocument();
  });
});
