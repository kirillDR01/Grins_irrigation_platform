/**
 * WebAuthn / Passkey types — mirror backend `schemas/webauthn.py`.
 */

import type {
  PublicKeyCredentialCreationOptionsJSON,
  PublicKeyCredentialRequestOptionsJSON,
  RegistrationResponseJSON,
  AuthenticationResponseJSON,
} from '@simplewebauthn/browser';

export interface RegistrationBeginResponse {
  handle: string;
  options: PublicKeyCredentialCreationOptionsJSON;
}

export interface RegistrationFinishRequest {
  handle: string;
  device_name: string;
  credential: RegistrationResponseJSON;
}

export interface AuthenticationBeginRequest {
  username?: string;
}

export interface AuthenticationBeginResponse {
  handle: string;
  options: PublicKeyCredentialRequestOptionsJSON;
}

export interface AuthenticationFinishRequest {
  handle: string;
  credential: AuthenticationResponseJSON;
}

export type CredentialDeviceType = 'single_device' | 'multi_device';

export interface Passkey {
  id: string;
  device_name: string;
  credential_device_type: CredentialDeviceType;
  backup_eligible: boolean;
  created_at: string;
  last_used_at: string | null;
}

export interface PasskeyListResponse {
  passkeys: Passkey[];
}
