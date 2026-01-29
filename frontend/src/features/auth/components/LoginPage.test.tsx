/**
 * Tests for LoginPage component.
 * Requirements: 19.1-19.7
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { LoginPage } from './LoginPage';
import * as AuthProviderModule from './AuthProvider';

// Mock useAuth hook
const mockLogin = vi.fn();
const mockUseAuth = vi.spyOn(AuthProviderModule, 'useAuth');

// Mock useNavigate and useLocation
const mockNavigate = vi.fn();
let mockLocationState: { from?: string } | null = null;

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ state: mockLocationState }),
  };
});

function renderLoginPage() {
  return render(
    <BrowserRouter>
      <LoginPage />
    </BrowserRouter>
  );
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLocationState = null;
    mockUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      login: mockLogin,
      logout: vi.fn(),
      refreshToken: vi.fn(),
    });
  });

  it('renders login page with data-testid', () => {
    renderLoginPage();
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
  });

  it('renders username input', () => {
    renderLoginPage();
    expect(screen.getByTestId('username-input')).toBeInTheDocument();
    expect(screen.getByLabelText('Username')).toBeInTheDocument();
  });

  it('renders password input', () => {
    renderLoginPage();
    expect(screen.getByTestId('password-input')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
  });

  it('renders remember me checkbox', () => {
    renderLoginPage();
    expect(screen.getByTestId('remember-me-checkbox')).toBeInTheDocument();
    expect(screen.getByText('Remember me')).toBeInTheDocument();
  });

  it('renders sign in button', () => {
    renderLoginPage();
    expect(screen.getByTestId('login-btn')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('toggles password visibility', async () => {
    const user = userEvent.setup();
    renderLoginPage();

    const passwordInput = screen.getByTestId('password-input');
    const toggleButton = screen.getByTestId('password-toggle');

    // Initially password is hidden
    expect(passwordInput).toHaveAttribute('type', 'password');

    // Click toggle to show password
    await user.click(toggleButton);
    expect(passwordInput).toHaveAttribute('type', 'text');

    // Click toggle to hide password again
    await user.click(toggleButton);
    expect(passwordInput).toHaveAttribute('type', 'password');
  });

  it('shows loading state during login', async () => {
    const user = userEvent.setup();
    // Make login take some time
    mockLogin.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );

    renderLoginPage();

    await user.type(screen.getByTestId('username-input'), 'testuser');
    await user.type(screen.getByTestId('password-input'), 'password123');
    await user.click(screen.getByTestId('login-btn'));

    // Should show loading state
    expect(screen.getByText(/signing in/i)).toBeInTheDocument();
  });

  it('shows error alert on invalid credentials', async () => {
    const user = userEvent.setup();
    mockLogin.mockRejectedValue(new Error('Invalid username or password'));

    renderLoginPage();

    await user.type(screen.getByTestId('username-input'), 'wronguser');
    await user.type(screen.getByTestId('password-input'), 'wrongpass');
    await user.click(screen.getByTestId('login-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('login-error')).toBeInTheDocument();
    });
    expect(screen.getByText('Invalid username or password')).toBeInTheDocument();
  });

  it('calls login with correct credentials', async () => {
    const user = userEvent.setup();
    mockLogin.mockResolvedValue(undefined);

    renderLoginPage();

    await user.type(screen.getByTestId('username-input'), 'testuser');
    await user.type(screen.getByTestId('password-input'), 'password123');
    await user.click(screen.getByTestId('login-btn'));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password123',
        remember_me: false,
      });
    });
  });

  it('includes remember_me when checkbox is checked', async () => {
    const user = userEvent.setup();
    mockLogin.mockResolvedValue(undefined);

    renderLoginPage();

    await user.type(screen.getByTestId('username-input'), 'testuser');
    await user.type(screen.getByTestId('password-input'), 'password123');
    await user.click(screen.getByTestId('remember-me-checkbox'));
    await user.click(screen.getByTestId('login-btn'));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password123',
        remember_me: true,
      });
    });
  });

  it('navigates to dashboard on successful login', async () => {
    const user = userEvent.setup();
    mockLogin.mockResolvedValue(undefined);

    renderLoginPage();

    await user.type(screen.getByTestId('username-input'), 'testuser');
    await user.type(screen.getByTestId('password-input'), 'password123');
    await user.click(screen.getByTestId('login-btn'));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });
  });

  it('navigates to original destination from location state', async () => {
    const user = userEvent.setup();
    mockLogin.mockResolvedValue(undefined);
    mockLocationState = { from: '/customers' };

    renderLoginPage();

    await user.type(screen.getByTestId('username-input'), 'testuser');
    await user.type(screen.getByTestId('password-input'), 'password123');
    await user.click(screen.getByTestId('login-btn'));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/customers', { replace: true });
    });
  });

  it('disables inputs during loading', async () => {
    const user = userEvent.setup();
    mockLogin.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 500))
    );

    renderLoginPage();

    await user.type(screen.getByTestId('username-input'), 'testuser');
    await user.type(screen.getByTestId('password-input'), 'password123');
    await user.click(screen.getByTestId('login-btn'));

    // Inputs should be disabled during loading
    expect(screen.getByTestId('username-input')).toBeDisabled();
    expect(screen.getByTestId('password-input')).toBeDisabled();
    expect(screen.getByTestId('login-btn')).toBeDisabled();
  });

  it('requires username field (HTML5 validation)', () => {
    renderLoginPage();
    const usernameInput = screen.getByTestId('username-input');
    expect(usernameInput).toHaveAttribute('required');
  });

  it('requires password field (HTML5 validation)', () => {
    renderLoginPage();
    const passwordInput = screen.getByTestId('password-input');
    expect(passwordInput).toHaveAttribute('required');
  });

  it('has required attribute on username and password inputs', () => {
    renderLoginPage();

    // Both inputs should have required attribute for HTML5 validation
    const usernameInput = screen.getByTestId('username-input');
    const passwordInput = screen.getByTestId('password-input');
    
    expect(usernameInput).toHaveAttribute('required');
    expect(passwordInput).toHaveAttribute('required');
  });

  it('clears error when retrying login', async () => {
    const user = userEvent.setup();
    mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'));
    mockLogin.mockResolvedValueOnce(undefined);

    renderLoginPage();

    // First attempt - fails
    await user.type(screen.getByTestId('username-input'), 'wronguser');
    await user.type(screen.getByTestId('password-input'), 'wrongpass');
    await user.click(screen.getByTestId('login-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('login-error')).toBeInTheDocument();
    });

    // Clear and retry with correct credentials
    await user.clear(screen.getByTestId('username-input'));
    await user.clear(screen.getByTestId('password-input'));
    await user.type(screen.getByTestId('username-input'), 'testuser');
    await user.type(screen.getByTestId('password-input'), 'password123');
    await user.click(screen.getByTestId('login-btn'));

    // Error should be cleared during retry
    await waitFor(() => {
      expect(screen.queryByTestId('login-error')).not.toBeInTheDocument();
    });
  });
});
