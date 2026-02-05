/**
 * Authentication types for the frontend.
 * Mirrors backend schemas from grins_platform/schemas/auth.py
 */

export type UserRole = 'admin' | 'manager' | 'tech';

export interface User {
  id: string;
  username: string;
  name: string;
  email: string | null;
  role: UserRole;
  is_active: boolean;
}

export interface LoginRequest {
  username: string;
  password: string;
  remember_me?: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
  csrf_token: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface AuthContextValue extends AuthState {
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  updateUser: (user: User) => void;
}
