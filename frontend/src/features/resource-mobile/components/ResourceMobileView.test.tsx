/**
 * Tests for ResourceMobileView composed page component (Bug 2 fix).
 *
 * Verifies the page wires useResourceSchedule and renders loading,
 * error, and data states correctly.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { ResourceSchedule } from '../types';

vi.mock('@/features/auth', () => ({
  useAuth: () => ({
    user: { id: 'staff-1', name: 'Test Staff', role: 'tech' },
    isAuthenticated: true,
    isLoading: false,
  }),
}));

const mockUseResourceSchedule = vi.fn();
vi.mock('../hooks/useResourceSchedule', () => ({
  useResourceSchedule: (...args: unknown[]) => mockUseResourceSchedule(...args),
}));

vi.mock('@/features/ai', () => ({
  ResourceMobileChat: () => <div data-testid="resource-mobile-chat" />,
  SchedulingChat: () => null,
  PreJobChecklist: () => null,
  AILoadingState: () => null,
  AIErrorState: () => null,
  AIStreamingText: () => null,
  AIQueryChat: () => null,
  AIScheduleGenerator: () => null,
  AICategorization: () => null,
  AICommunicationDrafts: () => null,
  AIEstimateGenerator: () => null,
  MorningBriefing: () => null,
  CommunicationsQueue: () => null,
  useSchedulingChat: () => ({ messages: [], sendMessage: vi.fn(), isLoading: false }),
  schedulingChatKeys: { all: ['scheduling-chat'] },
}));

import { ResourceMobileView } from './ResourceMobileView';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}

const fixtureSchedule: ResourceSchedule = {
  date: '2026-05-01',
  staff_id: 'staff-1',
  staff_name: 'Test Staff',
  total_drive_minutes: 42,
  jobs: [
    {
      id: 'job-1',
      job_type: 'Service Call',
      address: '123 Main St',
      customer_name: 'Acme Co',
      estimated_duration_minutes: 60,
      eta: '09:00',
      status: 'scheduled',
      notes: null,
      gate_code: null,
      requires_special_prep: false,
      route_order: 1,
    },
  ],
};

afterEach(() => {
  mockUseResourceSchedule.mockReset();
});

describe('ResourceMobileView', () => {
  it('renders the page shell with data-testid="resource-mobile-page"', () => {
    mockUseResourceSchedule.mockReturnValue({
      data: fixtureSchedule,
      isLoading: false,
      error: null,
    });
    render(<ResourceMobileView />, { wrapper });
    expect(screen.getByTestId('resource-mobile-page')).toBeInTheDocument();
  });

  it('shows the loading spinner while the query is loading', () => {
    mockUseResourceSchedule.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });
    render(<ResourceMobileView />, { wrapper });
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('shows the error message on query failure', () => {
    mockUseResourceSchedule.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Schedule fetch failed'),
    });
    render(<ResourceMobileView />, { wrapper });
    expect(screen.getByTestId('error-message')).toBeInTheDocument();
    expect(screen.getByText(/Schedule fetch failed/)).toBeInTheDocument();
  });

  it('renders route cards for each job once data is loaded', () => {
    mockUseResourceSchedule.mockReturnValue({
      data: fixtureSchedule,
      isLoading: false,
      error: null,
    });
    render(<ResourceMobileView />, { wrapper });
    expect(screen.getByTestId('route-card-1')).toBeInTheDocument();
  });

  it('renders ResourceMobileChat below the schedule pane', () => {
    mockUseResourceSchedule.mockReturnValue({
      data: fixtureSchedule,
      isLoading: false,
      error: null,
    });
    render(<ResourceMobileView />, { wrapper });
    expect(screen.getByTestId('resource-mobile-chat')).toBeInTheDocument();
  });
});
