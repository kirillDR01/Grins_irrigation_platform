/**
 * StaffForm — render, validation hint, and submit (Cluster F).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import type { ReactNode } from 'react';

import { StaffForm } from './StaffForm';
import { staffApi } from '../api/staffApi';

vi.mock('../api/staffApi', () => ({
  staffApi: {
    create: vi.fn(),
    update: vi.fn(),
  },
}));

vi.mock('@/features/auth/components/AuthProvider', () => ({
  useAuth: () => ({
    user: {
      id: 'admin-id',
      email: 'admin@example.com',
      role: 'admin' as const,
    },
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
    updateUser: vi.fn(),
    setAuthState: vi.fn(),
    loginWithPasskey: vi.fn(),
  }),
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

function createHarness() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
  return { Wrapper };
}

describe('StaffForm (Cluster F)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the admin auth section when the current user is admin', () => {
    const { Wrapper } = createHarness();
    render(
      <StaffForm open={true} onOpenChange={() => {}} mode="create" />,
      { wrapper: Wrapper },
    );

    expect(screen.getByTestId('staff-form-auth-section')).toBeInTheDocument();
    expect(screen.getByTestId('staff-form-username')).toBeInTheDocument();
    expect(screen.getByTestId('staff-form-password')).toBeInTheDocument();
    expect(screen.getByTestId('staff-form-login-enabled')).toBeInTheDocument();
  });

  it('shows password-strength hint under the password field', () => {
    const { Wrapper } = createHarness();
    render(
      <StaffForm open={true} onOpenChange={() => {}} mode="create" />,
      { wrapper: Wrapper },
    );

    expect(
      screen.getByText(/at least 8 characters, including a letter and a number/i),
    ).toBeInTheDocument();
  });

  it('rejects a weak password with inline validation', async () => {
    const user = userEvent.setup();
    const { Wrapper } = createHarness();
    render(
      <StaffForm open={true} onOpenChange={() => {}} mode="create" />,
      { wrapper: Wrapper },
    );

    await user.type(screen.getByTestId('staff-form-name'), 'Alice');
    await user.type(screen.getByTestId('staff-form-phone'), '6125551234');
    await user.type(screen.getByTestId('staff-form-password'), 'short');
    await user.click(screen.getByTestId('staff-form-submit'));

    await waitFor(() => {
      expect(
        screen.getByText(/password must be at least 8 characters/i),
      ).toBeInTheDocument();
    });
    expect(staffApi.create).not.toHaveBeenCalled();
  });

  it('submits valid create with credentials', async () => {
    const user = userEvent.setup();
    vi.mocked(staffApi.create).mockResolvedValue({
      id: 'new-id',
      name: 'Alice',
      phone: '6125551234',
      email: null,
      role: 'tech',
      skill_level: null,
      certifications: null,
      is_available: true,
      availability_notes: null,
      hourly_rate: null,
      is_active: true,
      username: 'alice',
      is_login_enabled: true,
      last_login: null,
      locked_until: null,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    });
    const onOpenChange = vi.fn();
    const { Wrapper } = createHarness();
    render(
      <StaffForm open={true} onOpenChange={onOpenChange} mode="create" />,
      { wrapper: Wrapper },
    );

    await user.type(screen.getByTestId('staff-form-name'), 'Alice');
    await user.type(screen.getByTestId('staff-form-phone'), '6125551234');
    await user.type(screen.getByTestId('staff-form-username'), 'alice');
    await user.type(screen.getByTestId('staff-form-password'), 'Goodpass1');
    await user.click(screen.getByTestId('staff-form-login-enabled'));
    await user.click(screen.getByTestId('staff-form-submit'));

    await waitFor(() => {
      expect(staffApi.create).toHaveBeenCalledTimes(1);
    });
    const payload = vi.mocked(staffApi.create).mock.calls[0]?.[0];
    expect(payload?.username).toBe('alice');
    expect(payload?.password).toBe('Goodpass1');
    expect(payload?.is_login_enabled).toBe(true);
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
