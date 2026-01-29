/**
 * Tests for UserMenu component.
 * Requirements: 19.8
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { UserMenu } from './UserMenu';
import * as AuthProviderModule from './AuthProvider';

// Mock useAuth hook
const mockLogout = vi.fn();
const mockUseAuth = vi.spyOn(AuthProviderModule, 'useAuth');

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function renderUserMenu() {
  return render(
    <BrowserRouter>
      <UserMenu />
    </BrowserRouter>
  );
}

describe('UserMenu', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns null when no user', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      login: vi.fn(),
      logout: mockLogout,
      refreshToken: vi.fn(),
    });

    const { container } = renderUserMenu();
    expect(container.firstChild).toBeNull();
  });

  it('displays user name', () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: '1',
        username: 'testuser',
        name: 'John Doe',
        email: 'john@example.com',
        role: 'admin',
        is_active: true,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: mockLogout,
      refreshToken: vi.fn(),
    });

    renderUserMenu();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('displays user initials', () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: '1',
        username: 'testuser',
        name: 'John Doe',
        email: 'john@example.com',
        role: 'admin',
        is_active: true,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: mockLogout,
      refreshToken: vi.fn(),
    });

    renderUserMenu();
    expect(screen.getByText('JD')).toBeInTheDocument();
  });

  it('opens dropdown on click', async () => {
    const user = userEvent.setup();
    mockUseAuth.mockReturnValue({
      user: {
        id: '1',
        username: 'testuser',
        name: 'John Doe',
        email: 'john@example.com',
        role: 'admin',
        is_active: true,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: mockLogout,
      refreshToken: vi.fn(),
    });

    renderUserMenu();

    await user.click(screen.getByTestId('user-menu'));

    expect(screen.getByTestId('user-menu-dropdown')).toBeInTheDocument();
    expect(screen.getByTestId('user-menu-name')).toHaveTextContent('John Doe');
    expect(screen.getByTestId('user-menu-email')).toHaveTextContent('john@example.com');
  });

  it('shows settings option in dropdown', async () => {
    const user = userEvent.setup();
    mockUseAuth.mockReturnValue({
      user: {
        id: '1',
        username: 'testuser',
        name: 'John Doe',
        email: 'john@example.com',
        role: 'admin',
        is_active: true,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: mockLogout,
      refreshToken: vi.fn(),
    });

    renderUserMenu();

    await user.click(screen.getByTestId('user-menu'));

    expect(screen.getByTestId('settings-btn')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('shows logout option in dropdown', async () => {
    const user = userEvent.setup();
    mockUseAuth.mockReturnValue({
      user: {
        id: '1',
        username: 'testuser',
        name: 'John Doe',
        email: 'john@example.com',
        role: 'admin',
        is_active: true,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: mockLogout,
      refreshToken: vi.fn(),
    });

    renderUserMenu();

    await user.click(screen.getByTestId('user-menu'));

    expect(screen.getByTestId('logout-btn')).toBeInTheDocument();
    expect(screen.getByText('Log out')).toBeInTheDocument();
  });

  it('calls logout and navigates to login on logout click', async () => {
    const user = userEvent.setup();
    mockLogout.mockResolvedValue(undefined);
    mockUseAuth.mockReturnValue({
      user: {
        id: '1',
        username: 'testuser',
        name: 'John Doe',
        email: 'john@example.com',
        role: 'admin',
        is_active: true,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: mockLogout,
      refreshToken: vi.fn(),
    });

    renderUserMenu();

    await user.click(screen.getByTestId('user-menu'));
    await user.click(screen.getByTestId('logout-btn'));

    expect(mockLogout).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });

  it('navigates to settings on settings click', async () => {
    const user = userEvent.setup();
    mockUseAuth.mockReturnValue({
      user: {
        id: '1',
        username: 'testuser',
        name: 'John Doe',
        email: 'john@example.com',
        role: 'admin',
        is_active: true,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: mockLogout,
      refreshToken: vi.fn(),
    });

    renderUserMenu();

    await user.click(screen.getByTestId('user-menu'));
    await user.click(screen.getByTestId('settings-btn'));

    expect(mockNavigate).toHaveBeenCalledWith('/settings');
  });

  it('shows username when email is null', async () => {
    const user = userEvent.setup();
    mockUseAuth.mockReturnValue({
      user: {
        id: '1',
        username: 'testuser',
        name: 'John Doe',
        email: null,
        role: 'admin',
        is_active: true,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: mockLogout,
      refreshToken: vi.fn(),
    });

    renderUserMenu();

    await user.click(screen.getByTestId('user-menu'));

    expect(screen.getByTestId('user-menu-email')).toHaveTextContent('testuser');
  });
});
