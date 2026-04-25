/**
 * Tests for the WebAuthn / Passkey hooks.
 *
 * useLoginWithPasskey is exercised end-to-end against a mocked
 * webauthnApi + @simplewebauthn/browser. useRegisterPasskey and
 * useRevokePasskey wrap useMutation, so we verify they invalidate the
 * passkey list on success.
 */

import { renderHook, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import {
  QueryClient,
  QueryClientProvider,
  useQueryClient,
} from '@tanstack/react-query';
import type { ReactNode } from 'react';

import {
  useLoginWithPasskey,
  useRegisterPasskey,
  useRevokePasskey,
} from './usePasskeyAuth';
import { passkeyKeys } from '../api/keys';

// --- Mocks ----------------------------------------------------------------

vi.mock('../api/webauthn', () => ({
  webauthnApi: {
    authenticateBegin: vi.fn(),
    authenticateFinish: vi.fn(),
    registerBegin: vi.fn(),
    registerFinish: vi.fn(),
    revokePasskey: vi.fn(),
  },
}));

vi.mock('@simplewebauthn/browser', () => ({
  startAuthentication: vi.fn(),
  startRegistration: vi.fn(),
}));

const mockSetAuthState = vi.fn();
vi.mock('../components/AuthProvider', () => ({
  useAuth: () => ({
    setAuthState: mockSetAuthState,
    user: null,
    isAuthenticated: false,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
    updateUser: vi.fn(),
    loginWithPasskey: vi.fn(),
  }),
}));

import { webauthnApi } from '../api/webauthn';
import {
  startAuthentication,
  startRegistration,
} from '@simplewebauthn/browser';

const mockedAuthBegin = webauthnApi.authenticateBegin as unknown as Mock;
const mockedAuthFinish = webauthnApi.authenticateFinish as unknown as Mock;
const mockedRegisterBegin = webauthnApi.registerBegin as unknown as Mock;
const mockedRegisterFinish = webauthnApi.registerFinish as unknown as Mock;
const mockedRevokePasskey = webauthnApi.revokePasskey as unknown as Mock;
const mockedStartAuth = startAuthentication as unknown as Mock;
const mockedStartReg = startRegistration as unknown as Mock;

// --- Helpers --------------------------------------------------------------

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  function wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  }
  return { wrapper, qc };
}

// --- useLoginWithPasskey --------------------------------------------------

describe('useLoginWithPasskey', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('runs begin → startAuthentication → finish → setAuthState', async () => {
    mockedAuthBegin.mockResolvedValue({
      handle: 'h',
      options: { challenge: 'c' },
    });
    mockedStartAuth.mockResolvedValue({ id: 'asn-cred' });
    const loginResponse = {
      access_token: 'a',
      token_type: 'bearer',
      expires_in: 60,
      user: { id: 'u', username: 'kirill', name: 'K', email: null, role: 'admin', is_active: true },
      csrf_token: 'csrf',
    };
    mockedAuthFinish.mockResolvedValue(loginResponse);

    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useLoginWithPasskey(), { wrapper });

    await act(async () => {
      await result.current('kirill');
    });

    expect(mockedAuthBegin).toHaveBeenCalledWith({ username: 'kirill' });
    expect(mockedStartAuth).toHaveBeenCalledWith({
      optionsJSON: { challenge: 'c' },
    });
    expect(mockedAuthFinish).toHaveBeenCalledWith({
      handle: 'h',
      credential: { id: 'asn-cred' },
    });
    expect(mockSetAuthState).toHaveBeenCalledWith(loginResponse);
  });

  it('passes undefined username through unchanged (discoverable flow)', async () => {
    mockedAuthBegin.mockResolvedValue({
      handle: 'h',
      options: { challenge: 'c' },
    });
    mockedStartAuth.mockResolvedValue({ id: 'asn-cred' });
    mockedAuthFinish.mockResolvedValue({
      access_token: 'a',
      token_type: 'bearer',
      expires_in: 60,
      user: { id: 'u', username: 'kirill', name: 'K', email: null, role: 'admin', is_active: true },
      csrf_token: 'csrf',
    });

    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useLoginWithPasskey(), { wrapper });

    await act(async () => {
      await result.current(undefined);
    });

    expect(mockedAuthBegin).toHaveBeenCalledWith({ username: undefined });
  });
});

// --- useRegisterPasskey ---------------------------------------------------

describe('useRegisterPasskey', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('invalidates the passkey list on success', async () => {
    mockedRegisterBegin.mockResolvedValue({
      handle: 'h',
      options: { challenge: 'c' },
    });
    mockedStartReg.mockResolvedValue({ id: 'reg-cred' });
    mockedRegisterFinish.mockResolvedValue({
      id: 'cred-1',
      device_name: 'X',
      credential_device_type: 'multi_device',
      backup_eligible: true,
      created_at: '2026-04-25T00:00:00Z',
      last_used_at: null,
    });

    const { wrapper, qc } = makeWrapper();
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useRegisterPasskey(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync('My Mac');
    });

    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: passkeyKeys.lists(),
      });
    });
  });

  it('propagates NotAllowedError so the component can decide UI', async () => {
    mockedRegisterBegin.mockResolvedValue({
      handle: 'h',
      options: { challenge: 'c' },
    });
    const cancel = Object.assign(new Error('cancelled'), {
      name: 'NotAllowedError',
    });
    mockedStartReg.mockRejectedValue(cancel);

    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useRegisterPasskey(), { wrapper });

    await expect(result.current.mutateAsync('X')).rejects.toThrow(
      'cancelled'
    );
  });
});

// --- useRevokePasskey -----------------------------------------------------

describe('useRevokePasskey', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('invalidates the passkey list on success', async () => {
    mockedRevokePasskey.mockResolvedValue(undefined);

    const { wrapper, qc } = makeWrapper();
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useRevokePasskey(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync('cred-1');
    });

    expect(mockedRevokePasskey).toHaveBeenCalledWith('cred-1');
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: passkeyKeys.lists(),
      });
    });
  });
});

// Silence "unused import" warnings without changing behavior.
void useQueryClient;
