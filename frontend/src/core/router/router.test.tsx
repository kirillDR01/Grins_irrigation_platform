/**
 * Router route verification tests.
 * Validates: Requirements 2.1, 4.1
 */

import { describe, it, expect, vi } from 'vitest';

// ── Mock all lazy-loaded page components to avoid importing real modules ──

vi.mock('@/pages/Dashboard', () => ({ DashboardPage: () => null }));
vi.mock('@/pages/Customers', () => ({ CustomersPage: () => null }));
vi.mock('@/pages/Jobs', () => ({ JobsPage: () => null }));
vi.mock('@/pages/Schedule', () => ({ SchedulePage: () => null }));
vi.mock('@/pages/ScheduleGenerate', () => ({ ScheduleGeneratePage: () => null }));
vi.mock('@/pages/ScheduleMobile', () => ({ ScheduleMobilePage: () => null }));
vi.mock('@/pages/Staff', () => ({ StaffPage: () => null }));
vi.mock('@/pages/Settings', () => ({ SettingsPage: () => null }));
vi.mock('@/pages/Invoices', () => ({ InvoicesPage: () => null }));
vi.mock('@/pages/Leads', () => ({ LeadsPage: () => null }));
vi.mock('@/pages/WorkRequestsRedirect', () => ({ WorkRequestsRedirect: () => null }));
vi.mock('@/pages/Agreements', () => ({ AgreementsPage: () => null }));
vi.mock('@/pages/Sales', () => ({ SalesPage: () => null }));
vi.mock('@/pages/Accounting', () => ({ AccountingPage: () => null }));
vi.mock('@/pages/Marketing', () => ({ MarketingPage: () => null }));
vi.mock('@/pages/Communications', () => ({ CommunicationsPage: () => null }));
vi.mock('@/pages/EstimateDetail', () => ({ EstimateDetailPage: () => null }));
vi.mock('@/pages/portal/EstimateReview', () => ({ EstimateReviewPage: () => null }));
vi.mock('@/pages/portal/ContractSigning', () => ({ ContractSigningPage: () => null }));
vi.mock('@/pages/portal/InvoicePortal', () => ({ InvoicePortalPage: () => null }));
vi.mock('@/shared/components/Layout', () => ({ Layout: ({ children }: { children: React.ReactNode }) => children }));
vi.mock('@/shared/components/LoadingSpinner', () => ({ LoadingPage: () => null }));
vi.mock('@/features/auth', () => ({
  ProtectedRoute: ({ children }: { children: React.ReactNode }) => children,
  LoginPage: () => null,
}));

import { router } from './index';

/**
 * Recursively collect all route paths from the router config.
 */
function collectPaths(routes: { path?: string; children?: { path?: string; children?: unknown[] }[] }[]): string[] {
  const paths: string[] = [];
  for (const route of routes) {
    if (route.path) paths.push(route.path);
    if (route.children) {
      paths.push(...collectPaths(route.children));
    }
  }
  return paths;
}

describe('Router configuration', () => {
  it('contains schedule/generate route', () => {
    const paths = collectPaths(router.routes);
    expect(paths).toContain('schedule/generate');
  });

  it('contains schedule/mobile route', () => {
    const paths = collectPaths(router.routes);
    expect(paths).toContain('schedule/mobile');
  });
});
