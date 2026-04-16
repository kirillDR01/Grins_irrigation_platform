import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { MassNotifyPanel } from './MassNotifyPanel';
import { MASS_NOTIFICATION_CONFIG } from '../types';

vi.mock('../hooks', () => ({
  useMassNotify: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
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
