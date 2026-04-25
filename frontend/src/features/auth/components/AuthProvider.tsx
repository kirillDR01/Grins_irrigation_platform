/**
 * AuthProvider context for managing authentication state.
 *
 * Features:
 * - Manages user state
 * - Manages access token in memory (not localStorage for security)
 * - Manages CSRF token (read from cookie, send in headers)
 * - Implements login/logout functions
 * - Auto-refresh before token expiration
 *
 * Requirements: 16.8, 19.1-19.8, 20.5-20.6
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useRef,
  type ReactNode,
} from 'react';
import { apiClient } from '@/core/api/client';
import { authApi } from '../api';
import { webauthnApi } from '../api/webauthn';
import { startAuthentication } from '@simplewebauthn/browser';
import type {
  User,
  LoginRequest,
  LoginResponse,
  AuthContextValue,
} from '../types';

// Token expiration buffer (refresh 1 minute before expiry)
const TOKEN_REFRESH_BUFFER_MS = 60 * 1000;

// Default context value
const defaultContextValue: AuthContextValue = {
  user: null,
  isAuthenticated: false,
  isLoading: true,
  login: async () => {},
  logout: async () => {},
  refreshToken: async () => {},
  updateUser: () => {},
  setAuthState: () => {},
  loginWithPasskey: async () => {},
};

const AuthContext = createContext<AuthContextValue>(defaultContextValue);

/**
 * Get CSRF token from cookie.
 */
function getCsrfTokenFromCookie(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * Set up axios interceptor to add CSRF token to requests.
 */
function setupCsrfInterceptor(): number {
  return apiClient.interceptors.request.use((config) => {
    const csrfToken = getCsrfTokenFromCookie();
    if (csrfToken && config.headers) {
      config.headers['X-CSRF-Token'] = csrfToken;
    }
    return config;
  });
}

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const csrfInterceptorRef = useRef<number | null>(null);

  // Set up access token in axios headers
  useEffect(() => {
    if (accessToken) {
      apiClient.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
    } else {
      delete apiClient.defaults.headers.common['Authorization'];
    }
  }, [accessToken]);

  // Set up CSRF interceptor on mount
  useEffect(() => {
    csrfInterceptorRef.current = setupCsrfInterceptor();
    return () => {
      if (csrfInterceptorRef.current !== null) {
        apiClient.interceptors.request.eject(csrfInterceptorRef.current);
      }
    };
  }, []);

  // Schedule token refresh before expiration
  const scheduleTokenRefresh = useCallback((expiresIn: number) => {
    // Clear any existing timer
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }

    // Schedule refresh 1 minute before expiry
    const refreshTime = expiresIn * 1000 - TOKEN_REFRESH_BUFFER_MS;
    if (refreshTime > 0) {
      refreshTimerRef.current = setTimeout(async () => {
        try {
          const response = await authApi.refreshAccessToken();
          setAccessToken(response.access_token);
          scheduleTokenRefresh(response.expires_in);
        } catch {
          // Refresh failed, user needs to re-login
          setUser(null);
          setAccessToken(null);
        }
      }, refreshTime);
    }
  }, []);

  // Clean up timer on unmount
  useEffect(() => {
    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
    };
  }, []);

  // Listen for interceptor-driven token refreshes to sync state and reschedule timer
  useEffect(() => {
    const handleTokenRefreshed = (e: Event) => {
      const { access_token, expires_in } = (e as CustomEvent).detail;
      if (access_token) {
        setAccessToken(access_token);
        scheduleTokenRefresh(expires_in);
      }
    };
    window.addEventListener('token-refreshed', handleTokenRefreshed);
    return () => {
      window.removeEventListener('token-refreshed', handleTokenRefreshed);
    };
  }, [scheduleTokenRefresh]);

  // Try to restore session on mount
  useEffect(() => {
    const restoreSession = async () => {
      try {
        // Try to refresh token (will use HttpOnly cookie)
        const response = await authApi.refreshAccessToken();
        setAccessToken(response.access_token);
        scheduleTokenRefresh(response.expires_in);

        // Get user info
        const userInfo = await authApi.getCurrentUser();
        setUser(userInfo);
      } catch {
        // No valid session, user needs to login
        setUser(null);
        setAccessToken(null);
      } finally {
        setIsLoading(false);
      }
    };

    restoreSession();
  }, [scheduleTokenRefresh]);

  // Apply a LoginResponse — used by both password login and passkey login.
  const setAuthState = useCallback(
    (response: LoginResponse) => {
      setAccessToken(response.access_token);
      setUser(response.user);
      scheduleTokenRefresh(response.expires_in);
    },
    [scheduleTokenRefresh]
  );

  // Login function
  const login = useCallback(
    async (credentials: LoginRequest) => {
      const response = await authApi.login(credentials);
      setAuthState(response);
    },
    [setAuthState]
  );

  // Passkey login — runs the WebAuthn ceremony and applies the result.
  const loginWithPasskey = useCallback(
    async (username?: string) => {
      const begin = await webauthnApi.authenticateBegin({ username });
      const credential = await startAuthentication({ optionsJSON: begin.options });
      const response = await webauthnApi.authenticateFinish({
        handle: begin.handle,
        credential,
      });
      setAuthState(response);
    },
    [setAuthState]
  );

  // Logout function
  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      // Clear state regardless of API success
      setUser(null);
      setAccessToken(null);
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
        refreshTimerRef.current = null;
      }
    }
  }, []);

  // Manual token refresh
  const refreshToken = useCallback(async () => {
    const response = await authApi.refreshAccessToken();
    setAccessToken(response.access_token);
    scheduleTokenRefresh(response.expires_in);
  }, [scheduleTokenRefresh]);

  // Update user in context (after profile update)
  const updateUser = useCallback((updatedUser: User) => {
    setUser(updatedUser);
  }, []);

  const value: AuthContextValue = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    refreshToken,
    updateUser,
    setAuthState,
    loginWithPasskey,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Hook to access auth context.
 * Must be used within AuthProvider.
 */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === defaultContextValue) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
