/**
 * Authentication API client.
 * Handles login, logout, token refresh, and user info.
 */

import { apiClient } from '@/core/api/client';
import type {
  LoginRequest,
  LoginResponse,
  TokenResponse,
  User,
  ChangePasswordRequest,
} from '../types';

const AUTH_BASE = '/auth';

/**
 * Login with username and password.
 * Sets refresh token as HttpOnly cookie (handled by backend).
 */
export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>(
    `${AUTH_BASE}/login`,
    credentials,
    { withCredentials: true }
  );
  return response.data;
}

/**
 * Logout and clear session.
 * Clears refresh token cookie (handled by backend).
 */
export async function logout(): Promise<void> {
  await apiClient.post(`${AUTH_BASE}/logout`, null, { withCredentials: true });
}

/**
 * Refresh access token using refresh token cookie.
 */
export async function refreshAccessToken(): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>(
    `${AUTH_BASE}/refresh`,
    null,
    { withCredentials: true }
  );
  return response.data;
}

/**
 * Get current user info.
 */
export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>(`${AUTH_BASE}/me`);
  return response.data;
}

/**
 * Change password.
 */
export async function changePassword(data: ChangePasswordRequest): Promise<void> {
  await apiClient.post(`${AUTH_BASE}/change-password`, data);
}

/**
 * Update user profile.
 */
export interface UpdateProfileRequest {
  name?: string;
  email?: string;
  phone?: string;
}

export async function updateProfile(data: UpdateProfileRequest): Promise<User> {
  const response = await apiClient.patch<User>(`${AUTH_BASE}/me`, data);
  return response.data;
}

export const authApi = {
  login,
  logout,
  refreshAccessToken,
  getCurrentUser,
  changePassword,
  updateProfile,
};
