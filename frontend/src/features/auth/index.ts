/**
 * Auth feature public exports.
 */

// Components
export { AuthProvider, useAuth } from './components/AuthProvider';
export { LoginPage } from './components/LoginPage';
export { ProtectedRoute } from './components/ProtectedRoute';
export { UserMenu } from './components/UserMenu';
export { PasskeyManager } from './components/PasskeyManager';

// API
export { authApi } from './api';
export { webauthnApi } from './api/webauthn';
export { passkeyKeys } from './api/keys';

// Hooks
export {
  useLoginWithPasskey,
  useRegisterPasskey,
  useRevokePasskey,
} from './hooks/usePasskeyAuth';

// Types
export type {
  User,
  UserRole,
  LoginRequest,
  LoginResponse,
  TokenResponse,
  ChangePasswordRequest,
  AuthState,
  AuthContextValue,
} from './types';
export type { Passkey, PasskeyListResponse } from './types/webauthn';
