/**
 * BusinessSettingsPanel.test.tsx — H-12 (bughunt 2026-04-16).
 *
 * Verifies:
 *  - panel renders current threshold values from useBusinessSettings
 *  - save button PATCHes /settings/business via useUpdateBusinessSettings
 *  - success path shows a toast
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const toastSuccess = vi.fn();
const toastError = vi.fn();

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}));

vi.mock('../hooks/useBusinessSettings', () => ({
  useBusinessSettings: vi.fn(),
  useUpdateBusinessSettings: vi.fn(),
}));

import {
  useBusinessSettings,
  useUpdateBusinessSettings,
} from '../hooks/useBusinessSettings';
import { BusinessSettingsPanel } from './BusinessSettingsPanel';

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe('BusinessSettingsPanel (H-12)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    toastSuccess.mockClear();
    toastError.mockClear();
  });

  it('renders current threshold values from the API', async () => {
    vi.mocked(useBusinessSettings).mockReturnValue({
      data: {
        lien_days_past_due: 75,
        lien_min_amount: 900,
        upcoming_due_days: 10,
        confirmation_no_reply_days: 4,
      },
      isLoading: false,
      error: null,
      // @ts-expect-error — partial mock
    });
    vi.mocked(useUpdateBusinessSettings).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      // @ts-expect-error — partial mock
    });

    render(<BusinessSettingsPanel />, { wrapper: createWrapper() });

    expect(screen.getByTestId('business-settings-panel')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId('input-lien-days-past-due')).toHaveValue(75);
      expect(screen.getByTestId('input-lien-min-amount')).toHaveValue(900);
      expect(screen.getByTestId('input-upcoming-due-days')).toHaveValue(10);
      expect(screen.getByTestId('input-confirmation-no-reply-days')).toHaveValue(4);
    });
  });

  it('saves changes via PATCH /settings/business and shows success toast', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({
      lien_days_past_due: 90,
      lien_min_amount: 1000,
      upcoming_due_days: 7,
      confirmation_no_reply_days: 3,
    });
    vi.mocked(useBusinessSettings).mockReturnValue({
      data: {
        lien_days_past_due: 60,
        lien_min_amount: 500,
        upcoming_due_days: 7,
        confirmation_no_reply_days: 3,
      },
      isLoading: false,
      error: null,
      // @ts-expect-error — partial mock
    });
    vi.mocked(useUpdateBusinessSettings).mockReturnValue({
      mutateAsync,
      isPending: false,
      // @ts-expect-error — partial mock
    });

    const user = userEvent.setup();
    render(<BusinessSettingsPanel />, { wrapper: createWrapper() });

    const daysInput = await screen.findByTestId('input-lien-days-past-due');
    await user.clear(daysInput);
    await user.type(daysInput, '90');

    const minInput = screen.getByTestId('input-lien-min-amount');
    await user.clear(minInput);
    await user.type(minInput, '1000');

    await user.click(screen.getByTestId('save-business-settings-btn'));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalled();
    });
    const payload = mutateAsync.mock.calls[0][0];
    expect(payload).toMatchObject({
      lien_days_past_due: 90,
      // Decimal is sent as string to preserve exactness across JSON.
      lien_min_amount: '1000',
    });
    await waitFor(() => {
      expect(toastSuccess).toHaveBeenCalledWith('Business settings saved');
    });
  });

  it('shows error toast when mutation rejects', async () => {
    const mutateAsync = vi.fn().mockRejectedValue(new Error('boom'));
    vi.mocked(useBusinessSettings).mockReturnValue({
      data: {
        lien_days_past_due: 60,
        lien_min_amount: 500,
        upcoming_due_days: 7,
        confirmation_no_reply_days: 3,
      },
      isLoading: false,
      error: null,
      // @ts-expect-error — partial mock
    });
    vi.mocked(useUpdateBusinessSettings).mockReturnValue({
      mutateAsync,
      isPending: false,
      // @ts-expect-error — partial mock
    });

    const user = userEvent.setup();
    render(<BusinessSettingsPanel />, { wrapper: createWrapper() });
    await user.click(screen.getByTestId('save-business-settings-btn'));

    await waitFor(() => {
      expect(toastError).toHaveBeenCalledWith('Failed to save business settings');
    });
  });
});
