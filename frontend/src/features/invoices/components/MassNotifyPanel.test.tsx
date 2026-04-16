import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';

import { MassNotifyPanel } from './MassNotifyPanel';
import { MASS_NOTIFICATION_CONFIG } from '../types';

vi.mock('../hooks', () => ({
  useMassNotify: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

vi.mock('@/features/settings', () => ({
  useBusinessSettings: () => ({
    data: {
      lien_days_past_due: 60,
      lien_min_amount: 500,
      upcoming_due_days: 7,
      confirmation_no_reply_days: 3,
    },
    isLoading: false,
    error: null,
  }),
}));

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={client}>
        <BrowserRouter>{children}</BrowserRouter>
      </QueryClientProvider>
    );
  };
}

describe('MassNotifyPanel (CR-5)', () => {
  it('does not include lien_eligible in MASS_NOTIFICATION_CONFIG', () => {
    // CR-5: The lien-notice flow moved to the Lien Review Queue.
    // The config used by the panel's Select must not advertise lien_eligible.
    const configKeys = Object.keys(MASS_NOTIFICATION_CONFIG);
    expect(configKeys).not.toContain('lien_eligible');
    expect(configKeys).toEqual(expect.arrayContaining(['past_due', 'due_soon']));
  });

  it('renders the mass-notify button that opens the dialog', async () => {
    const user = userEvent.setup();
    render(<MassNotifyPanel />, { wrapper: createWrapper() });

    expect(screen.getByTestId('mass-notify-btn')).toBeInTheDocument();

    await user.click(screen.getByTestId('mass-notify-btn'));
    expect(screen.getByTestId('mass-notify-dialog')).toBeInTheDocument();
    // Ensure there are no residual lien-specific inputs inside the dialog.
    expect(screen.queryByTestId('mass-notify-lien-days')).not.toBeInTheDocument();
    expect(screen.queryByTestId('mass-notify-lien-amount')).not.toBeInTheDocument();
  });
});
