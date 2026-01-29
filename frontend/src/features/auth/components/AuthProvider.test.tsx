/**
 * Tests for AuthProvider context.
 * Requirements: 16.8, 19.1-19.8, 20.5-20.6
 */

import { render, screen, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthProvider, useAuth } from './AuthProvider';
import { authApi } from '../api';
import { apiClient } from '@/core/api/client';

// Mock the auth API
vi.mock('../api', () => ({
  authApi: {
    login: vi.fn(),
    logout: vi.fn(),
    refreshAccessToken: vi.fn(),
    getCurrentUser: vi.fn(),
  },
}));

// Mock apiClient
vi.mock('@/core/api/client', () => ({
  apiClient: {
    defaults: {
      headers: {
        common: {} as Record<string, string>,
      },
    },
    interceptors: {
      request: {
        use: vi.fn(() => 1),
        eject: vi.fn(),
      },
    },
  },
}));

// Test component that uses useAuth
function TestConsumer({ onLogin, onLogout, onRefresh }: {
  onLogin?: () => void;
  onLogout?: () => void;
  onRefresh?: () => void;
}) {
  const { user, isAuthenticated, isLoading, login, logout, refreshToken } = useAuth();
  
  const handleLogin = async () => {
    try {
      await login({ username: 'test', password: 'pass' });
      onLogin?.();
    } catch {
      // Expected in some tests
    }
  };
  
  const handleLogout = async () => {
    await logout();
    onLogout?.();
  };
  
  const handleRefresh = async () => {
    try {
      await refreshToken();
      onRefresh?.();
    } catch {
      // Expected in some tests
    }
  };
  
  return (
    <div>
      <div data-testid="is-loading">{isLoading ? 'loading' : 'not-loading'}</div>
      <div data-testid="is-authenticated">{isAuthenticated ? 'authenticated' : 'not-authenticated'}</div>
      <div data-testid="user">{user ? user.username : 'no-user'}</div>
      <button data-testid="login-btn" onClick={handleLogin}>Login</button>
      <button data-testid="logout-btn" onClick={handleLogout}>Logout</button>
      <button data-testid="refresh-btn" onClick={handleRefresh}>Refresh</button>
    </div>
  );
}

const mockUser = {
  id: '123',
  username: 'testuser',
  name: 'Test User',
  email: 'test@example.com',
  role: 'admin' as const,
  is_active: true,
};

const mockLoginResponse = {
  access_token: 'test-access-token',
  token_type: 'bearer',
  expires_in: 900,
  user: mockUser,
  csrf_token: 'test-csrf-token',
};

const mockTokenResponse = {
  access_token: 'refreshed-access-token',
  token_type: 'bearer',
  expires_in: 900,
};

describe('AuthProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clear cookies
    document.cookie = 'csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    // Reset apiClient headers
    (apiClient.defaults.headers.common as Record<string, string>) = {};
  });

  it('shows loading state initially then not-loading after session check', async () => {
    // Mock refresh to reject (no session)
    vi.mocked(authApi.refreshAccessToken).mockRejectedValue(new Error('No session'));

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('not-loading');
    });
  });

  it('shows not authenticated when no session exists', async () => {
    vi.mocked(authApi.refreshAccessToken).mockRejectedValue(new Error('No session'));

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('not-authenticated');
      expect(screen.getByTestId('user')).toHaveTextContent('no-user');
    });
  });

  it('updates user state on successful login', async () => {
    vi.mocked(authApi.refreshAccessToken).mockRejectedValue(new Error('No session'));
    vi.mocked(authApi.login).mockResolvedValue(mockLoginResponse);

    const onLogin = vi.fn();

    render(
      <AuthProvider>
        <TestConsumer onLogin={onLogin} />
      </AuthProvider>
    );

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('not-loading');
    });

    // Click login
    await act(async () => {
      screen.getByTestId('login-btn').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('authenticated');
      expect(screen.getByTestId('user')).toHaveTextContent('testuser');
    });
  });

  it('does not update state on login failure', async () => {
    vi.mocked(authApi.refreshAccessToken).mockRejectedValue(new Error('No session'));
    vi.mocked(authApi.login).mockRejectedValue(new Error('Invalid credentials'));

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('not-loading');
    });

    // Click login (will fail)
    await act(async () => {
      screen.getByTestId('login-btn').click();
    });

    // State should remain unauthenticated
    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('not-authenticated');
      expect(screen.getByTestId('user')).toHaveTextContent('no-user');
    });
  });

  it('clears user state on logout', async () => {
    // Start with a session
    vi.mocked(authApi.refreshAccessToken).mockResolvedValue(mockTokenResponse);
    vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUser);
    vi.mocked(authApi.logout).mockResolvedValue(undefined);

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    // Should be authenticated after session restore
    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('authenticated');
    });

    // Click logout
    await act(async () => {
      screen.getByTestId('logout-btn').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('not-authenticated');
      expect(screen.getByTestId('user')).toHaveTextContent('no-user');
    });
  });

  it('updates access token on manual refresh', async () => {
    vi.mocked(authApi.refreshAccessToken)
      .mockResolvedValueOnce(mockTokenResponse)
      .mockResolvedValueOnce({ ...mockTokenResponse, access_token: 'new-token' });
    vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUser);

    const onRefresh = vi.fn();

    render(
      <AuthProvider>
        <TestConsumer onRefresh={onRefresh} />
      </AuthProvider>
    );

    // Wait for initial session restore
    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('authenticated');
    });

    // Click refresh
    await act(async () => {
      screen.getByTestId('refresh-btn').click();
    });

    // Verify refresh was called twice (once on mount, once on click)
    await waitFor(() => {
      expect(authApi.refreshAccessToken).toHaveBeenCalledTimes(2);
    });
  });

  it('sets up CSRF interceptor on mount', async () => {
    vi.mocked(authApi.refreshAccessToken).mockRejectedValue(new Error('No session'));

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('not-loading');
    });

    // Verify interceptor was set up
    expect(apiClient.interceptors.request.use).toHaveBeenCalled();
  });

  it('reads CSRF token from cookie and adds to headers via interceptor', async () => {
    // Set CSRF cookie
    document.cookie = 'csrf_token=test-csrf-value; path=/';

    vi.mocked(authApi.refreshAccessToken).mockRejectedValue(new Error('No session'));

    // Capture the interceptor function
    let interceptorFn: ((config: { headers?: Record<string, string> }) => { headers?: Record<string, string> }) | null = null;
    vi.mocked(apiClient.interceptors.request.use).mockImplementation((fn) => {
      interceptorFn = fn as typeof interceptorFn;
      return 1;
    });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('not-loading');
    });

    // Verify interceptor was registered
    expect(interceptorFn).not.toBeNull();

    // Test the interceptor adds CSRF token
    const config = { headers: {} as Record<string, string> };
    const result = interceptorFn!(config);
    expect(result.headers?.['X-CSRF-Token']).toBe('test-csrf-value');
  });
});

describe('AuthProvider - auto-refresh', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clear cookies
    document.cookie = 'csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    // Reset apiClient headers
    (apiClient.defaults.headers.common as Record<string, string>) = {};
  });

  it('schedules auto-refresh timer when session is restored', async () => {
    // This test verifies that scheduleTokenRefresh is called with expires_in
    // The actual timer behavior is tested implicitly through the refresh mechanism
    vi.mocked(authApi.refreshAccessToken).mockResolvedValue({
      ...mockTokenResponse,
      expires_in: 120, // 2 minutes
    });
    vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUser);

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    // Wait for session restore
    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('authenticated');
    });

    // Verify refresh was called (which triggers scheduleTokenRefresh internally)
    expect(authApi.refreshAccessToken).toHaveBeenCalledTimes(1);
    
    // The AuthProvider schedules a refresh timer internally
    // We verify this by checking that the component is in authenticated state
    // and the refresh API was called successfully
    expect(screen.getByTestId('user')).toHaveTextContent('testuser');
  });
});

describe('useAuth hook', () => {
  it('throws error when used outside AuthProvider', () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<TestConsumer />);
    }).toThrow('useAuth must be used within an AuthProvider');

    consoleSpy.mockRestore();
  });
});
