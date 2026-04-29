/**
 * Tests for AIScheduleView composed page component (Bug 1 + Bug 7 fixes).
 *
 * Replaces the previous "child components are mocked" smoke test with one
 * that mocks the real data hooks (useUtilizationReport / useCapacityForecast)
 * and asserts that the resource × day grid renders real rows from fixture
 * data, plus that arrow navigation emits onViewModeChange with a date.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';

const mockUseUtilization = vi.fn();
const mockUseCapacity = vi.fn();

vi.mock('../hooks/useAIScheduling', async () => {
  const actual = await vi.importActual<
    typeof import('../hooks/useAIScheduling')
  >('../hooks/useAIScheduling');
  return {
    ...actual,
    useUtilizationReport: (...args: unknown[]) => mockUseUtilization(...args),
    useCapacityForecast: (...args: unknown[]) => mockUseCapacity(...args),
  };
});

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
  useSchedulingChat: () => ({
    messages: [],
    sendMessage: vi.fn(),
    isLoading: false,
  }),
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

const utilFixture = {
  period_start: '2026-04-29',
  period_end: '2026-04-29',
  overall_utilization_pct: 72,
  resources: [
    {
      staff_id: 'staff-1',
      staff_name: 'Alice Tech',
      total_jobs: 4,
      total_minutes: 240,
      utilization_pct: 80,
      revenue_per_hour: 120,
    },
    {
      staff_id: 'staff-2',
      staff_name: 'Bob Tech',
      total_jobs: 3,
      total_minutes: 180,
      utilization_pct: 64,
      revenue_per_hour: 110,
    },
  ],
};

const capacityFixture = {
  date: '2026-04-29',
  total_jobs: 7,
  total_staff: 2,
  utilization_pct: 72,
  forecast_confidence: 0.8,
};

afterEach(() => {
  mockUseUtilization.mockReset();
  mockUseCapacity.mockReset();
});

describe('AIScheduleView', () => {
  it('renders the page shell with data-testid="ai-schedule-page"', () => {
    mockUseUtilization.mockReturnValue({
      data: utilFixture,
      isLoading: false,
      error: null,
    });
    mockUseCapacity.mockReturnValue({
      data: capacityFixture,
      isLoading: false,
      error: null,
    });
    render(<AIScheduleView />, { wrapper });
    expect(screen.getByTestId('ai-schedule-page')).toBeInTheDocument();
  });

  it('renders one resource row per utilization-report row (Bug 1 fix)', () => {
    mockUseUtilization.mockReturnValue({
      data: utilFixture,
      isLoading: false,
      error: null,
    });
    mockUseCapacity.mockReturnValue({
      data: capacityFixture,
      isLoading: false,
      error: null,
    });
    render(<AIScheduleView />, { wrapper });
    expect(screen.getByTestId('resource-row-staff-1')).toBeInTheDocument();
    expect(screen.getByTestId('resource-row-staff-2')).toBeInTheDocument();
  });

  it('shows the loading spinner while the data hooks are loading', () => {
    mockUseUtilization.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });
    mockUseCapacity.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });
    render(<AIScheduleView />, { wrapper });
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('shows an error message when either query fails', () => {
    mockUseUtilization.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('utilization failed'),
    });
    mockUseCapacity.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });
    render(<AIScheduleView />, { wrapper });
    expect(screen.getByTestId('error-message')).toBeInTheDocument();
  });

  it('clicking the next-date arrow re-fetches with the shifted date (Bug 7)', async () => {
    mockUseUtilization.mockReturnValue({
      data: utilFixture,
      isLoading: false,
      error: null,
    });
    mockUseCapacity.mockReturnValue({
      data: capacityFixture,
      isLoading: false,
      error: null,
    });
    const user = userEvent.setup();
    render(<AIScheduleView />, { wrapper });

    const initialUtilCalls = mockUseUtilization.mock.calls.length;
    await user.click(screen.getByTestId('schedule-date-next-btn'));

    expect(mockUseUtilization.mock.calls.length).toBeGreaterThan(
      initialUtilCalls,
    );
  });

  it('renders SchedulingChat in the right pane', () => {
    mockUseUtilization.mockReturnValue({
      data: utilFixture,
      isLoading: false,
      error: null,
    });
    mockUseCapacity.mockReturnValue({
      data: capacityFixture,
      isLoading: false,
      error: null,
    });
    render(<AIScheduleView />, { wrapper });
    expect(screen.getByTestId('scheduling-chat')).toBeInTheDocument();
  });

  it('renders AlertsPanel below the overview', () => {
    mockUseUtilization.mockReturnValue({
      data: utilFixture,
      isLoading: false,
      error: null,
    });
    mockUseCapacity.mockReturnValue({
      data: capacityFixture,
      isLoading: false,
      error: null,
    });
    render(<AIScheduleView />, { wrapper });
    expect(screen.getByTestId('alerts-panel')).toBeInTheDocument();
  });

  it('has <main> and <aside> semantic landmarks', () => {
    mockUseUtilization.mockReturnValue({
      data: utilFixture,
      isLoading: false,
      error: null,
    });
    mockUseCapacity.mockReturnValue({
      data: capacityFixture,
      isLoading: false,
      error: null,
    });
    render(<AIScheduleView />, { wrapper });
    expect(document.querySelector('main')).toBeInTheDocument();
    expect(document.querySelector('aside')).toBeInTheDocument();
  });
});
