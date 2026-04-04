/**
 * Integration tests for AIScheduleView page routing.
 * Verifies the page renders correctly when navigated to via the router.
 *
 * Validates: Requirements 2.1, 2.3, 2.4, 2.5
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// ── Mock auth (ProtectedRoute just renders children) ───────────────────

vi.mock('@/features/auth', () => ({
  ProtectedRoute: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  LoginPage: () => <div data-testid="login-page" />,
  useAuth: () => ({
    user: { id: '1', name: 'Admin', role: 'admin', email: 'admin@test.com' },
    isAuthenticated: true,
    isLoading: false,
  }),
}));

// ── Mock Layout (just renders children) ────────────────────────────────

vi.mock('@/shared/components/Layout', () => ({
  Layout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="layout">{children}</div>
  ),
}));

// ── Mock LoadingSpinner ────────────────────────────────────────────────

vi.mock('@/shared/components/LoadingSpinner', () => ({
  LoadingPage: () => <div data-testid="loading-page" />,
  LoadingSpinner: () => <div data-testid="loading-spinner" />,
}));

// ── Mock child components of AIScheduleView ────────────────────────────

vi.mock('./ScheduleOverviewEnhanced', () => ({
  ScheduleOverviewEnhanced: () => <div data-testid="schedule-overview-enhanced" />,
}));

vi.mock('@/features/scheduling-alerts', () => ({
  AlertsPanel: () => <div data-testid="alerts-panel" />,
  alertKeys: { all: ['alerts'] },
}));

vi.mock('@/features/ai/components/SchedulingChat', () => ({
  SchedulingChat: () => <div data-testid="scheduling-chat" />,
}));

// ── Mock hooks used by AIScheduleView ──────────────────────────────────

vi.mock('../hooks', () => ({
  useWeeklySchedule: vi.fn(() => ({
    data: { days: [] },
    isLoading: false,
    error: null,
  })),
}));

vi.mock('../hooks/useScheduleGeneration', () => ({
  useScheduleCapacity: vi.fn(() => ({
    data: null,
    isLoading: false,
    error: null,
  })),
  scheduleGenerationKeys: { all: ['schedule-generation'] },
}));

// ── Import after mocks ─────────────────────────────────────────────────

import { AIScheduleView } from './AIScheduleView';
import { ProtectedRoute } from '@/features/auth';
import { Layout } from '@/shared/components/Layout';

// ── Test-specific router config (mirrors real router, no lazy loading) ─

function ProtectedLayoutWrapper() {
  return (
    <ProtectedRoute>
      <Layout>
        <AIScheduleView />
      </Layout>
    </ProtectedRoute>
  );
}

function createTestRouter(initialEntries: string[]) {
  return createMemoryRouter(
    [
      {
        path: '/schedule/generate',
        element: <ProtectedLayoutWrapper />,
      },
    ],
    { initialEntries }
  );
}

function renderWithRouter(initialEntries: string[] = ['/schedule/generate']) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const router = createTestRouter(initialEntries);
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}

// ── Tests ──────────────────────────────────────────────────────────────

describe('AIScheduleView Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders AIScheduleView at /schedule/generate', () => {
    renderWithRouter();
    expect(screen.getByTestId('ai-schedule-page')).toBeInTheDocument();
  });

  it('renders within the layout wrapper', () => {
    renderWithRouter();
    const layout = screen.getByTestId('layout');
    expect(layout).toBeInTheDocument();
    expect(layout).toContainElement(screen.getByTestId('ai-schedule-page'));
  });

  it('renders all three child components within the page', () => {
    renderWithRouter();
    expect(screen.getByTestId('schedule-overview-enhanced')).toBeInTheDocument();
    expect(screen.getByTestId('alerts-panel')).toBeInTheDocument();
    expect(screen.getByTestId('scheduling-chat')).toBeInTheDocument();
  });

  it('renders within ProtectedRoute (authenticated user sees content, not login)', () => {
    renderWithRouter();
    // Should NOT see login page since user is authenticated
    expect(screen.queryByTestId('login-page')).not.toBeInTheDocument();
    // Should see the actual page content
    expect(screen.getByTestId('ai-schedule-page')).toBeInTheDocument();
  });
});
