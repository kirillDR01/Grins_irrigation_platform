/**
 * Tests for PasskeyManager — list / add / revoke flows.
 *
 * Uses a real QueryClient (per the project's frontend-testing standard
 * in .kiro/steering/frontend-testing.md) but mocks the webauthnApi and
 * the @simplewebauthn/browser library so jsdom doesn't need to drive
 * navigator.credentials.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { PasskeyManager } from './PasskeyManager';
import type { Passkey, PasskeyListResponse } from '../types/webauthn';

// --- Mocks ----------------------------------------------------------------

vi.mock('../api/webauthn', () => ({
  webauthnApi: {
    listPasskeys: vi.fn(),
    registerBegin: vi.fn(),
    registerFinish: vi.fn(),
    revokePasskey: vi.fn(),
  },
}));

vi.mock('@simplewebauthn/browser', () => ({
  startRegistration: vi.fn(),
  startAuthentication: vi.fn(),
  browserSupportsWebAuthnAutofill: vi.fn().mockResolvedValue(false),
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Eslint-friendly typed handles to the mocks.
import { webauthnApi } from '../api/webauthn';
import { startRegistration } from '@simplewebauthn/browser';
import { toast } from 'sonner';

const mockedListPasskeys = webauthnApi.listPasskeys as unknown as Mock;
const mockedRegisterBegin = webauthnApi.registerBegin as unknown as Mock;
const mockedRegisterFinish = webauthnApi.registerFinish as unknown as Mock;
const mockedRevokePasskey = webauthnApi.revokePasskey as unknown as Mock;
const mockedStartRegistration = startRegistration as unknown as Mock;

// --- Test helpers ---------------------------------------------------------

function makePasskey(overrides: Partial<Passkey> = {}): Passkey {
  return {
    id: 'cred-1',
    device_name: 'Test Device',
    credential_device_type: 'multi_device',
    backup_eligible: true,
    created_at: '2026-04-25T00:00:00Z',
    last_used_at: null,
    ...overrides,
  };
}

function renderManager(): ReturnType<typeof render> {
  // Fresh QueryClient per render so cache state never leaks across tests.
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <PasskeyManager />
    </QueryClientProvider>
  );
}

// --- Tests ----------------------------------------------------------------

describe('PasskeyManager', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the security card container', async () => {
    mockedListPasskeys.mockResolvedValue({
      passkeys: [],
    } satisfies PasskeyListResponse);
    renderManager();
    expect(await screen.findByTestId('security-page')).toBeInTheDocument();
  });

  it('shows the empty state when there are no passkeys', async () => {
    mockedListPasskeys.mockResolvedValue({
      passkeys: [],
    } satisfies PasskeyListResponse);
    renderManager();
    expect(
      await screen.findByTestId('passkey-empty-state')
    ).toBeInTheDocument();
  });

  it('renders one row per passkey returned by the API', async () => {
    mockedListPasskeys.mockResolvedValue({
      passkeys: [
        makePasskey({ id: 'cred-1', device_name: 'Mac' }),
        makePasskey({ id: 'cred-2', device_name: 'iPhone' }),
      ],
    } satisfies PasskeyListResponse);
    renderManager();
    const rows = await screen.findAllByTestId('passkey-row');
    expect(rows).toHaveLength(2);
    expect(screen.getByText('Mac')).toBeInTheDocument();
    expect(screen.getByText('iPhone')).toBeInTheDocument();
  });

  it('opens the add-passkey dialog when Add is clicked', async () => {
    mockedListPasskeys.mockResolvedValue({
      passkeys: [],
    } satisfies PasskeyListResponse);
    renderManager();
    const user = userEvent.setup();
    await screen.findByTestId('passkey-empty-state');

    await user.click(screen.getByTestId('add-passkey-btn'));

    expect(await screen.findByTestId('passkey-form')).toBeInTheDocument();
    expect(screen.getByTestId('device-name-input')).toBeInTheDocument();
  });

  it("validates 'Required' on empty submission via RHF + Zod", async () => {
    mockedListPasskeys.mockResolvedValue({
      passkeys: [],
    } satisfies PasskeyListResponse);
    renderManager();
    const user = userEvent.setup();
    await screen.findByTestId('passkey-empty-state');

    await user.click(screen.getByTestId('add-passkey-btn'));
    await screen.findByTestId('passkey-form');
    await user.click(screen.getByTestId('submit-passkey-btn'));

    expect(await screen.findByText('Required')).toBeInTheDocument();
    expect(mockedRegisterBegin).not.toHaveBeenCalled();
  });

  it('runs the full add flow on a valid device name', async () => {
    mockedListPasskeys.mockResolvedValue({
      passkeys: [],
    } satisfies PasskeyListResponse);
    mockedRegisterBegin.mockResolvedValue({
      handle: 'h',
      options: { challenge: 'c' },
    });
    mockedStartRegistration.mockResolvedValue({ id: 'cred-id' });
    mockedRegisterFinish.mockResolvedValue(makePasskey({ id: 'new-cred' }));
    renderManager();
    const user = userEvent.setup();
    await screen.findByTestId('passkey-empty-state');

    await user.click(screen.getByTestId('add-passkey-btn'));
    await screen.findByTestId('passkey-form');
    await user.type(
      screen.getByTestId('device-name-input'),
      'My Test MacBook'
    );
    await user.click(screen.getByTestId('submit-passkey-btn'));

    await waitFor(() => {
      expect(mockedRegisterBegin).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(mockedStartRegistration).toHaveBeenCalledWith({
        optionsJSON: { challenge: 'c' },
      });
    });
    await waitFor(() => {
      expect(mockedRegisterFinish).toHaveBeenCalledWith({
        handle: 'h',
        device_name: 'My Test MacBook',
        credential: { id: 'cred-id' },
      });
    });
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Passkey added');
    });
  });

  it('silently ignores user-cancelled biometric prompt (NotAllowedError)', async () => {
    mockedListPasskeys.mockResolvedValue({
      passkeys: [],
    } satisfies PasskeyListResponse);
    mockedRegisterBegin.mockResolvedValue({
      handle: 'h',
      options: { challenge: 'c' },
    });
    const cancel = Object.assign(new Error('cancelled'), {
      name: 'NotAllowedError',
    });
    mockedStartRegistration.mockRejectedValue(cancel);
    renderManager();
    const user = userEvent.setup();
    await screen.findByTestId('passkey-empty-state');

    await user.click(screen.getByTestId('add-passkey-btn'));
    await screen.findByTestId('passkey-form');
    await user.type(screen.getByTestId('device-name-input'), 'X');
    await user.click(screen.getByTestId('submit-passkey-btn'));

    await waitFor(() => {
      expect(mockedStartRegistration).toHaveBeenCalled();
    });
    // No toast.success, no toast.error — pure silent abort.
    expect(toast.success).not.toHaveBeenCalled();
    expect(toast.error).not.toHaveBeenCalled();
  });

  it('calls revokePasskey on confirm and toasts on success', async () => {
    mockedListPasskeys
      .mockResolvedValueOnce({
        passkeys: [makePasskey({ id: 'cred-1', device_name: 'Mac' })],
      } satisfies PasskeyListResponse)
      .mockResolvedValueOnce({
        passkeys: [],
      } satisfies PasskeyListResponse);
    mockedRevokePasskey.mockResolvedValue(undefined);
    renderManager();
    const user = userEvent.setup();

    await screen.findByTestId('passkey-table');
    await user.click(screen.getByTestId('revoke-passkey-btn'));

    // The confirm dialog uses the same Dialog primitive — confirm via the
    // 'Remove' button (no data-testid; located by accessible name).
    const removeBtn = await screen.findByRole('button', { name: 'Remove' });
    await user.click(removeBtn);

    await waitFor(() => {
      expect(mockedRevokePasskey).toHaveBeenCalledWith('cred-1');
    });
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Passkey removed');
    });
  });
});
