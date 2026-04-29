/**
 * Tests for AIScheduleView composed page component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { ErrorBoundary } from '@/shared/components/ErrorBoundary';

// Mock heavy child components
vi.mock('./ScheduleOverviewEnhanced', () => ({
  ScheduleOverviewEnhanced: ({ weekTitle }: { weekTitle: string }) => (
    <div data-testid="schedule-overview-enhanced">{weekTitle}</div>
  ),
}));

vi.mock('@/features/scheduling-alerts', () => ({
  AlertsPanel: () => <div data-testid="alerts-panel" />,
  AlertCard: () => null,
  SuggestionCard: () => null,
  RouteSwapMap: () => null,
  ChangeRequestCard: () => null,
  useAlerts: () => ({ data: [], isLoading: false, error: null }),
  useResolveAlert: () => ({ mutate: vi.fn() }),
  useDismissAlert: () => ({ mutate: vi.fn() }),
  useChangeRequests: () => ({ data: [], isLoading: false }),
  useApproveChangeRequest: () => ({ mutate: vi.fn() }),
  useDenyChangeRequest: () => ({ mutate: vi.fn() }),
  alertKeys: { all: ['scheduling-alerts'] },
  alertsApi: {},
}));

vi.mock('@/features/ai', () => ({
  SchedulingChat: () => <div data-testid="scheduling-chat" />,
  ResourceMobileChat: () => <div data-testid="resource-mobile-chat" />,
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

import { AIScheduleView } from './AIScheduleView';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}

describe('AIScheduleView', () => {
  it('renders with data-testid="ai-schedule-page"', () => {
    render(<AIScheduleView />, { wrapper });
    expect(screen.getByTestId('ai-schedule-page')).toBeInTheDocument();
  });

  it('renders ScheduleOverviewEnhanced child', () => {
    render(<AIScheduleView />, { wrapper });
    expect(screen.getByTestId('schedule-overview-enhanced')).toBeInTheDocument();
  });

  it('renders AlertsPanel child', () => {
    render(<AIScheduleView />, { wrapper });
    expect(screen.getByTestId('alerts-panel')).toBeInTheDocument();
  });

  it('renders SchedulingChat child', () => {
    render(<AIScheduleView />, { wrapper });
    expect(screen.getByTestId('scheduling-chat')).toBeInTheDocument();
  });

  it('has <main> and <aside> semantic landmarks', () => {
    render(<AIScheduleView />, { wrapper });
    expect(document.querySelector('main')).toBeInTheDocument();
    expect(document.querySelector('aside')).toBeInTheDocument();
  });

  it('has visually hidden h1 heading', () => {
    render(<AIScheduleView />, { wrapper });
    const h1 = document.querySelector('h1');
    expect(h1).toBeInTheDocument();
    expect(h1?.className).toContain('sr-only');
  });

  it('error boundary catches chat crash and shows fallback', () => {
    const ThrowingChat = () => {
      throw new Error('chat error');
    };

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <BrowserRouter>
          <ErrorBoundary fallback={<div data-testid="chat-error-fallback">Chat unavailable</div>}>
            <ThrowingChat />
          </ErrorBoundary>
        </BrowserRouter>
      </QueryClientProvider>
    );
    expect(screen.getByTestId('chat-error-fallback')).toBeInTheDocument();
  });
});
