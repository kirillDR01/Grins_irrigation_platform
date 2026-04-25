/**
 * WebAuthn / Passkey API client.
 */

import { apiClient } from '@/core/api/client';
import type { LoginResponse } from '../types';
import type {
  AuthenticationBeginRequest,
  AuthenticationBeginResponse,
  AuthenticationFinishRequest,
  Passkey,
  PasskeyListResponse,
  RegistrationBeginResponse,
  RegistrationFinishRequest,
} from '../types/webauthn';

const BASE = '/auth/webauthn';

async function registerBegin(): Promise<RegistrationBeginResponse> {
  const response = await apiClient.post<RegistrationBeginResponse>(
    `${BASE}/register/begin`,
    null,
    { withCredentials: true }
  );
  return response.data;
}

async function registerFinish(
  req: RegistrationFinishRequest
): Promise<Passkey> {
  const response = await apiClient.post<Passkey>(
    `${BASE}/register/finish`,
    req,
    { withCredentials: true }
  );
  return response.data;
}

async function authenticateBegin(
  req: AuthenticationBeginRequest
): Promise<AuthenticationBeginResponse> {
  const response = await apiClient.post<AuthenticationBeginResponse>(
    `${BASE}/authenticate/begin`,
    req,
    { withCredentials: true }
  );
  return response.data;
}

async function authenticateFinish(
  req: AuthenticationFinishRequest
): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>(
    `${BASE}/authenticate/finish`,
    req,
    { withCredentials: true }
  );
  return response.data;
}

async function listPasskeys(): Promise<PasskeyListResponse> {
  const response = await apiClient.get<PasskeyListResponse>(
    `${BASE}/credentials`,
    { withCredentials: true }
  );
  return response.data;
}

async function revokePasskey(id: string): Promise<void> {
  await apiClient.delete(`${BASE}/credentials/${id}`, {
    withCredentials: true,
  });
}

export const webauthnApi = {
  registerBegin,
  registerFinish,
  authenticateBegin,
  authenticateFinish,
  listPasskeys,
  revokePasskey,
};
