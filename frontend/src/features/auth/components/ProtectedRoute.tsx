/**
 * ProtectedRoute component for authentication and authorization.
 *
 * Features:
 * - Check authentication state
 * - Redirect to login if not authenticated
 * - Check role permissions
 * - Display AccessDenied for unauthorized roles
 *
 * Requirements: 20.1-20.4
 */

import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthProvider';
import type { UserRole } from '../types';
import { LoadingPage } from '@/shared/components/LoadingSpinner';
import { AlertTriangle } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactNode;
  /** Required roles to access this route. If empty, any authenticated user can access. */
  allowedRoles?: UserRole[];
}

/**
 * AccessDenied component displayed when user lacks required role.
 */
function AccessDenied() {
  return (
    <div
      className="flex min-h-[400px] flex-col items-center justify-center"
      data-testid="access-denied"
    >
      <AlertTriangle className="h-16 w-16 text-yellow-500 mb-4" />
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h1>
      <p className="text-gray-600 text-center max-w-md">
        You don't have permission to access this page. Please contact your
        administrator if you believe this is an error.
      </p>
    </div>
  );
}

/**
 * ProtectedRoute wrapper component.
 *
 * Wraps routes that require authentication and optionally specific roles.
 *
 * @example
 * // Any authenticated user
 * <ProtectedRoute>
 *   <DashboardPage />
 * </ProtectedRoute>
 *
 * @example
 * // Only admin and manager roles
 * <ProtectedRoute allowedRoles={['admin', 'manager']}>
 *   <AdminPage />
 * </ProtectedRoute>
 */
export function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  // Show loading while checking auth state
  if (isLoading) {
    return <LoadingPage message="Checking authentication..." />;
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated || !user) {
    // Save the attempted URL for redirecting after login
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role permissions if allowedRoles is specified
  if (allowedRoles && allowedRoles.length > 0) {
    if (!allowedRoles.includes(user.role)) {
      return <AccessDenied />;
    }
  }

  // User is authenticated and authorized
  return <>{children}</>;
}
