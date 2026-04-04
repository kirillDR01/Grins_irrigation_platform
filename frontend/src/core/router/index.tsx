import { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom';
import { Layout } from '@/shared/components/Layout';
import { LoadingPage } from '@/shared/components/LoadingSpinner';
import { ProtectedRoute, LoginPage } from '@/features/auth';

// Lazy load pages for code splitting
const DashboardPage = lazy(() =>
  import('@/pages/Dashboard').then((m) => ({ default: m.DashboardPage }))
);
const CustomersPage = lazy(() =>
  import('@/pages/Customers').then((m) => ({ default: m.CustomersPage }))
);
const JobsPage = lazy(() =>
  import('@/pages/Jobs').then((m) => ({ default: m.JobsPage }))
);
const SchedulePage = lazy(() =>
  import('@/pages/Schedule').then((m) => ({ default: m.SchedulePage }))
);
const ScheduleGeneratePage = lazy(() =>
  import('@/pages/ScheduleGenerate').then((m) => ({
    default: m.ScheduleGeneratePage,
  }))
);
const ScheduleMobilePage = lazy(() =>
  import('@/pages/ScheduleMobile').then((m) => ({
    default: m.ScheduleMobilePage,
  }))
);
const StaffPage = lazy(() =>
  import('@/pages/Staff').then((m) => ({ default: m.StaffPage }))
);
const SettingsPage = lazy(() =>
  import('@/pages/Settings').then((m) => ({ default: m.SettingsPage }))
);
const InvoicesPage = lazy(() =>
  import('@/pages/Invoices').then((m) => ({ default: m.InvoicesPage }))
);
const LeadsPage = lazy(() =>
  import('@/pages/Leads').then((m) => ({ default: m.LeadsPage }))
);
const WorkRequestsRedirect = lazy(() =>
  import('@/pages/WorkRequestsRedirect').then((m) => ({
    default: m.WorkRequestsRedirect,
  }))
);
const AgreementsPage = lazy(() =>
  import('@/pages/Agreements').then((m) => ({
    default: m.AgreementsPage,
  }))
);
const SalesPage = lazy(() =>
  import('@/pages/Sales').then((m) => ({ default: m.SalesPage }))
);
const AccountingPage = lazy(() =>
  import('@/pages/Accounting').then((m) => ({ default: m.AccountingPage }))
);
const MarketingPage = lazy(() =>
  import('@/pages/Marketing').then((m) => ({ default: m.MarketingPage }))
);
const CommunicationsPage = lazy(() =>
  import('@/pages/Communications').then((m) => ({
    default: m.CommunicationsPage,
  }))
);
const EstimateDetailPage = lazy(() =>
  import('@/pages/EstimateDetail').then((m) => ({
    default: m.EstimateDetailPage,
  }))
);

// Portal pages (public, no auth, no layout)
const EstimateReviewPage = lazy(() =>
  import('@/pages/portal/EstimateReview').then((m) => ({
    default: m.EstimateReviewPage,
  }))
);
const ContractSigningPage = lazy(() =>
  import('@/pages/portal/ContractSigning').then((m) => ({
    default: m.ContractSigningPage,
  }))
);
const InvoicePortalPage = lazy(() =>
  import('@/pages/portal/InvoicePortal').then((m) => ({
    default: m.InvoicePortalPage,
  }))
);

// Layout wrapper component with Suspense for lazy loaded pages
function LayoutWrapper() {
  return (
    <Layout>
      <Suspense fallback={<LoadingPage message="Loading..." />}>
        <Outlet />
      </Suspense>
    </Layout>
  );
}

// Protected layout wrapper - wraps all authenticated routes
function ProtectedLayoutWrapper() {
  return (
    <ProtectedRoute>
      <LayoutWrapper />
    </ProtectedRoute>
  );
}

// Public portal wrapper - Suspense only, no auth, no layout
function PortalWrapper() {
  return (
    <Suspense fallback={<LoadingPage message="Loading..." />}>
      <Outlet />
    </Suspense>
  );
}

export const router = createBrowserRouter([
  // Public route: Login
  {
    path: '/login',
    element: <LoginPage />,
  },
  // Public portal routes (no auth, no layout)
  {
    path: '/portal',
    element: <PortalWrapper />,
    children: [
      {
        path: 'estimates/:token',
        element: <EstimateReviewPage />,
      },
      {
        path: 'contracts/:token',
        element: <ContractSigningPage />,
      },
      {
        path: 'invoices/:token',
        element: <InvoicePortalPage />,
      },
    ],
  },
  // Protected routes
  {
    path: '/',
    element: <ProtectedLayoutWrapper />,
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: 'dashboard',
        element: <DashboardPage />,
      },
      {
        path: 'customers',
        element: <CustomersPage />,
      },
      {
        path: 'customers/:id',
        element: <CustomersPage />,
      },
      {
        path: 'leads',
        element: <LeadsPage />,
      },
      {
        path: 'leads/:id',
        element: <LeadsPage />,
      },
      {
        path: 'work-requests',
        element: <WorkRequestsRedirect />,
      },
      {
        path: 'work-requests/:id',
        element: <WorkRequestsRedirect />,
      },
      {
        path: 'jobs',
        element: <JobsPage />,
      },
      {
        path: 'jobs/:id',
        element: <JobsPage />,
      },
      {
        path: 'schedule',
        element: <SchedulePage />,
      },
      {
        path: 'schedule/generate',
        element: <ScheduleGeneratePage />,
      },
      {
        path: 'schedule/mobile',
        element: <ScheduleMobilePage />,
      },
      {
        path: 'staff',
        element: <StaffPage />,
      },
      {
        path: 'staff/:id',
        element: <StaffPage />,
      },
      {
        path: 'invoices',
        element: <InvoicesPage />,
      },
      {
        path: 'invoices/:id',
        element: <InvoicesPage />,
      },
      {
        path: 'agreements',
        element: <AgreementsPage />,
      },
      {
        path: 'agreements/:id',
        element: <AgreementsPage />,
      },
      {
        path: 'sales',
        element: <SalesPage />,
      },
      {
        path: 'accounting',
        element: <AccountingPage />,
      },
      {
        path: 'marketing',
        element: <MarketingPage />,
      },
      {
        path: 'communications',
        element: <CommunicationsPage />,
      },
      {
        path: 'estimates/:id',
        element: <EstimateDetailPage />,
      },
      {
        path: 'settings',
        element: <SettingsPage />,
      },
    ],
  },
]);
