/**
 * Hooks for the WebAuthn / Passkey ceremonies.
 *
 * - useLoginWithPasskey: end-to-end sign-in with biometric prompt.
 * - useRegisterPasskey: enroll a new passkey for the logged-in user.
 * - useRevokePasskey: revoke an owned passkey.
 */

import { useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  startAuthentication,
  startRegistration,
} from '@simplewebauthn/browser';

import { webauthnApi } from '../api/webauthn';
import { passkeyKeys } from '../api/keys';
import { useAuth } from '../components/AuthProvider';

export function useLoginWithPasskey() {
  const { setAuthState } = useAuth();

  return useCallback(
    async (username?: string) => {
      const begin = await webauthnApi.authenticateBegin({ username });
      const credential = await startAuthentication({ optionsJSON: begin.options });
      const loginResponse = await webauthnApi.authenticateFinish({
        handle: begin.handle,
        credential,
      });
      setAuthState(loginResponse);
    },
    [setAuthState]
  );
}

export function useRegisterPasskey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (deviceName: string) => {
      const begin = await webauthnApi.registerBegin();
      const credential = await startRegistration({ optionsJSON: begin.options });
      return webauthnApi.registerFinish({
        handle: begin.handle,
        device_name: deviceName,
        credential,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: passkeyKeys.lists() });
    },
  });
}

export function useRevokePasskey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => webauthnApi.revokePasskey(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: passkeyKeys.lists() });
    },
  });
}
