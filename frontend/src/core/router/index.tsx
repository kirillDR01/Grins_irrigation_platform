import { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom';
import { Layout } from '@/shared/components/Layout';
import { LoadingPage } from '@/shared/components/LoadingSpinner';

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
const StaffPage = lazy(() =>
  import('@/pages/Staff').then((m) => ({ default: m.StaffPage }))
);
const SettingsPage = lazy(() =>
  import('@/pages/Settings').then((m) => ({ default: m.SettingsPage }))
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

export const router = createBrowserRouter([
  {
    path: '/',
    element: <LayoutWrapper />,
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
        path: 'staff',
        element: <StaffPage />,
      },
      {
        path: 'staff/:id',
        element: <StaffPage />,
      },
      {
        path: 'settings',
        element: <SettingsPage />,
      },
    ],
  },
]);
