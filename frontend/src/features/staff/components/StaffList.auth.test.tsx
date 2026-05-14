/**
 * StaffList — auth-state badges (Cluster F).
 *
 * Validates that the list view renders the correct badge variant for each
 * combination of is_login_enabled / locked_until / last_login.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import type { ReactNode } from 'react';

import { StaffList } from './StaffList';
import { staffApi } from '../api/staffApi';
import type { Staff } from '../types';

vi.mock('../api/staffApi', () => ({
  staffApi: {
    list: vi.fn(),
    getById: vi.fn(),
    getAvailable: vi.fn(),
  },
}));

function makeStaff(overrides: Partial<Staff>): Staff {
  return {
    id: 'staff-1',
    name: 'Alice Example',
    phone: '6125551234',
    email: 'alice@example.com',
    role: 'tech',
    skill_level: 'senior',
    certifications: null,
    is_available: true,
    availability_notes: null,
    hourly_rate: null,
    is_active: true,
    username: null,
    is_login_enabled: false,
    last_login: null,
    locked_until: null,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

function createHarness() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
  return { Wrapper };
}

describe('StaffList auth-state badges (Cluster F)', () => {
  beforeEach(() => {
    vi.mocked(staffApi.list).mockReset();
  });

  it('shows "No login" badge for staff without login enabled', async () => {
    vi.mocked(staffApi.list).mockResolvedValue({
      items: [makeStaff({ id: 'a', is_login_enabled: false })],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });
    const { Wrapper } = createHarness();
    render(<StaffList />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('login-disabled-badge')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('login-enabled-badge')).not.toBeInTheDocument();
    expect(screen.queryByTestId('locked-badge')).not.toBeInTheDocument();
  });

  it('shows "Login enabled" badge for staff with login enabled', async () => {
    vi.mocked(staffApi.list).mockResolvedValue({
      items: [makeStaff({ id: 'b', is_login_enabled: true })],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });
    const { Wrapper } = createHarness();
    render(<StaffList />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('login-enabled-badge')).toBeInTheDocument();
    });
  });

  it('shows the red "Locked" badge when locked_until is in the future', async () => {
    const future = new Date(Date.now() + 60 * 60 * 1000).toISOString();
    vi.mocked(staffApi.list).mockResolvedValue({
      items: [
        makeStaff({
          id: 'c',
          is_login_enabled: true,
          locked_until: future,
        }),
      ],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });
    const { Wrapper } = createHarness();
    render(<StaffList />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('locked-badge')).toBeInTheDocument();
    });
    // Login-enabled and Locked must both appear together.
    expect(screen.getByTestId('login-enabled-badge')).toBeInTheDocument();
  });

  it('renders "Never" when last_login is null', async () => {
    vi.mocked(staffApi.list).mockResolvedValue({
      items: [makeStaff({ id: 'd', last_login: null })],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });
    const { Wrapper } = createHarness();
    render(<StaffList />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('staff-last-login-d')).toHaveTextContent('Never');
    });
  });
});
