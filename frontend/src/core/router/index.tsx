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
const StaffPage = lazy(() =>
  import('@/pages/Staff').then((m) => ({ default: m.StaffPage }))
);
const SettingsPage = lazy(() =>
  import('@/pages/Settings').then((m) => ({ default: m.SettingsPage }))
);
const InvoicesPage = lazy(() =>
  import('@/pages/Invoices').then((m) => ({ default: m.InvoicesPage }))
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

export const router = createBrowserRouter([
  // Public route: Login
  {
    path: '/login',
    element: <LoginPage />,
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
        path: 'settings',
        element: <SettingsPage />,
      },
    ],
  },
]);
