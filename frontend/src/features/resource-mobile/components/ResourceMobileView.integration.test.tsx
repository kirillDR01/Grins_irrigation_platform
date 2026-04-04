/**
 * Integration tests for ResourceMobileView page routing.
 * Verifies the page renders correctly when navigated to via the router.
 *
 * Validates: Requirements 4.1, 4.3, 4.4
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
    user: { id: '2', name: 'Tech', role: 'resource', email: 'tech@test.com' },
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

// ── Mock child components of ResourceMobileView ────────────────────────

vi.mock('./ResourceScheduleView', () => ({
  ResourceScheduleView: () => <div data-testid="resource-schedule-view" />,
}));

vi.mock('@/features/ai/components/ResourceMobileChat', () => ({
  ResourceMobileChat: () => <div data-testid="resource-mobile-chat" />,
}));

// ── Import after mocks ─────────────────────────────────────────────────

import { ResourceMobileView } from './ResourceMobileView';
import { ProtectedRoute } from '@/features/auth';
import { Layout } from '@/shared/components/Layout';

// ── Test-specific router config (mirrors real router, no lazy loading) ─

function ProtectedLayoutWrapper() {
  return (
    <ProtectedRoute>
      <Layout>
        <ResourceMobileView />
      </Layout>
    </ProtectedRoute>
  );
}

function createTestRouter(initialEntries: string[]) {
  return createMemoryRouter(
    [
      {
        path: '/schedule/mobile',
        element: <ProtectedLayoutWrapper />,
      },
    ],
    { initialEntries }
  );
}

function renderWithRouter(initialEntries: string[] = ['/schedule/mobile']) {
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

describe('ResourceMobileView Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders ResourceMobileView at /schedule/mobile', () => {
    renderWithRouter();
    expect(screen.getByTestId('resource-mobile-page')).toBeInTheDocument();
  });

  it('renders within the layout wrapper', () => {
    renderWithRouter();
    const layout = screen.getByTestId('layout');
    expect(layout).toBeInTheDocument();
    expect(layout).toContainElement(screen.getByTestId('resource-mobile-page'));
  });

  it('renders both child components within the page', () => {
    renderWithRouter();
    expect(screen.getByTestId('resource-schedule-view')).toBeInTheDocument();
    expect(screen.getByTestId('resource-mobile-chat')).toBeInTheDocument();
  });

  it('renders within ProtectedRoute (authenticated user sees content, not login)', () => {
    renderWithRouter();
    // Should NOT see login page since user is authenticated
    expect(screen.queryByTestId('login-page')).not.toBeInTheDocument();
    // Should see the actual page content
    expect(screen.getByTestId('resource-mobile-page')).toBeInTheDocument();
  });
});
