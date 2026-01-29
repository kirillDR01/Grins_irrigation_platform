/**
 * Tests for ProtectedRoute component.
 * Requirements: 20.1-20.4
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from './ProtectedRoute';
import * as AuthProviderModule from './AuthProvider';

// Mock useAuth hook
const mockUseAuth = vi.spyOn(AuthProviderModule, 'useAuth');

function renderWithRouter(
  ui: React.ReactElement,
  { initialEntries = ['/protected'] } = {}
) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/login" element={<div data-testid="login-page">Login</div>} />
        <Route path="/protected" element={ui} />
      </Routes>
    </MemoryRouter>
  );
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state while checking auth', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: true,
      login: vi.fn(),
      logout: vi.fn(),
      refreshToken: vi.fn(),
    });

    renderWithRouter(
      <ProtectedRoute>
        <div data-testid="protected-content">Protected Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText(/checking authentication/i)).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  it('redirects to login when not authenticated', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshToken: vi.fn(),
    });

    renderWithRouter(
      <ProtectedRoute>
        <div data-testid="protected-content">Protected Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByTestId('login-page')).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: '1',
        username: 'testuser',
        name: 'Test User',
        email: 'test@example.com',
        role: 'admin',
        is_active: true,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshToken: vi.fn(),
    });

    renderWithRouter(
      <ProtectedRoute>
        <div data-testid="protected-content">Protected Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  it('shows access denied for unauthorized role', () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: '1',
        username: 'techuser',
        name: 'Tech User',
        email: 'tech@example.com',
        role: 'tech',
        is_active: true,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshToken: vi.fn(),
    });

    renderWithRouter(
      <ProtectedRoute allowedRoles={['admin', 'manager']}>
        <div data-testid="protected-content">Admin Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByTestId('access-denied')).toBeInTheDocument();
    expect(screen.getByText('Access Denied')).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  it('allows access when user has required role', () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: '1',
        username: 'manager',
        name: 'Manager User',
        email: 'manager@example.com',
        role: 'manager',
        is_active: true,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshToken: vi.fn(),
    });

    renderWithRouter(
      <ProtectedRoute allowedRoles={['admin', 'manager']}>
        <div data-testid="protected-content">Manager Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
    expect(screen.queryByTestId('access-denied')).not.toBeInTheDocument();
  });

  it('allows any authenticated user when no roles specified', () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: '1',
        username: 'techuser',
        name: 'Tech User',
        email: 'tech@example.com',
        role: 'tech',
        is_active: true,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshToken: vi.fn(),
    });

    renderWithRouter(
      <ProtectedRoute>
        <div data-testid="protected-content">Any User Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });
});
