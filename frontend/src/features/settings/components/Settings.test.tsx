/**
 * Tests for Settings page enhancement components.
 * Validates: Requirements 87.3, 87.4, 87.5, 87.6
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BusinessInfo } from './BusinessInfo';
import { InvoiceDefaults } from './InvoiceDefaults';
import { NotificationPrefs } from './NotificationPrefs';
import { EstimateDefaults } from './EstimateDefaults';

// Mock the hooks module
const mockSettings = {
  company_name: "Grin's Irrigation",
  company_address: 'Eden Prairie, MN',
  company_phone: '(612) 555-0000',
  company_email: 'info@grins.com',
  company_logo_url: null,
  company_website: 'https://grins.com',
  default_payment_terms_days: 30,
  late_fee_percentage: 1.5,
  lien_warning_days: 45,
  lien_filing_days: 120,
  day_of_reminder_time: '07:00',
  sms_time_window_start: '08:00',
  sms_time_window_end: '21:00',
  enable_delay_notifications: true,
  default_valid_days: 30,
  follow_up_intervals_days: '3,7,14,21',
  enable_auto_follow_ups: true,
};

const mockMutateAsync = vi.fn().mockResolvedValue(mockSettings);
const mockUploadMutateAsync = vi.fn().mockResolvedValue({ url: 'https://s3.example.com/logo.png' });

vi.mock('../hooks', () => ({
  useSettings: vi.fn(() => ({
    data: mockSettings,
    isLoading: false,
    error: null,
  })),
  useUpdateSettings: vi.fn(() => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  })),
  useUploadLogo: vi.fn(() => ({
    mutateAsync: mockUploadMutateAsync,
    isPending: false,
  })),
  settingsKeys: {
    all: ['settings'] as const,
    detail: () => ['settings', 'detail'] as const,
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('BusinessInfo', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders business information fields with loaded data', async () => {
    render(<BusinessInfo />, { wrapper: createWrapper() });

    expect(screen.getByTestId('business-info-section')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId('bi-company-name-input')).toHaveValue("Grin's Irrigation");
    });
    expect(screen.getByTestId('bi-company-phone-input')).toHaveValue('(612) 555-0000');
    expect(screen.getByTestId('bi-company-address-input')).toHaveValue('Eden Prairie, MN');
    expect(screen.getByTestId('bi-company-email-input')).toHaveValue('info@grins.com');
    expect(screen.getByTestId('bi-company-website-input')).toHaveValue('https://grins.com');
  });

  it('submits updated business info on save', async () => {
    const user = userEvent.setup();
    render(<BusinessInfo />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('bi-company-name-input')).toHaveValue("Grin's Irrigation");
    });

    const nameInput = screen.getByTestId('bi-company-name-input');
    await user.clear(nameInput);
    await user.type(nameInput, 'New Company Name');
    await user.click(screen.getByTestId('save-business-info-btn'));

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({ company_name: 'New Company Name' })
      );
    });
  });

  it('shows validation error for empty company name', async () => {
    const user = userEvent.setup();
    render(<BusinessInfo />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('bi-company-name-input')).toHaveValue("Grin's Irrigation");
    });

    const nameInput = screen.getByTestId('bi-company-name-input');
    await user.clear(nameInput);
    await user.click(screen.getByTestId('save-business-info-btn'));

    await waitFor(() => {
      expect(screen.getByText('Company name is required')).toBeInTheDocument();
    });
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it('renders logo upload button', () => {
    render(<BusinessInfo />, { wrapper: createWrapper() });
    expect(screen.getByTestId('upload-logo-btn')).toBeInTheDocument();
  });
});

describe('InvoiceDefaults', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders invoice default fields with loaded data', async () => {
    render(<InvoiceDefaults />, { wrapper: createWrapper() });

    expect(screen.getByTestId('invoice-defaults-section')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId('id-payment-terms-input')).toHaveValue(30);
    });
    expect(screen.getByTestId('id-late-fee-input')).toHaveValue(1.5);
    expect(screen.getByTestId('id-lien-warning-input')).toHaveValue(45);
    expect(screen.getByTestId('id-lien-filing-input')).toHaveValue(120);
  });

  it('submits updated invoice defaults on save', async () => {
    const user = userEvent.setup();
    render(<InvoiceDefaults />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('id-payment-terms-input')).toHaveValue(30);
    });

    const termsInput = screen.getByTestId('id-payment-terms-input');
    await user.clear(termsInput);
    await user.type(termsInput, '45');
    await user.click(screen.getByTestId('save-invoice-defaults-btn'));

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({ default_payment_terms_days: 45 })
      );
    });
  });
});

describe('NotificationPrefs', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders notification preference fields with loaded data', async () => {
    render(<NotificationPrefs />, { wrapper: createWrapper() });

    expect(screen.getByTestId('notification-prefs-section')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId('np-reminder-time-input')).toHaveValue('07:00');
    });
    expect(screen.getByTestId('np-sms-start-input')).toHaveValue('08:00');
    expect(screen.getByTestId('np-sms-end-input')).toHaveValue('21:00');
  });

  it('renders delay notifications toggle as checked', async () => {
    render(<NotificationPrefs />, { wrapper: createWrapper() });

    await waitFor(() => {
      const toggle = screen.getByTestId('np-delay-toggle');
      expect(toggle).toBeInTheDocument();
      expect(toggle.getAttribute('data-state')).toBe('checked');
    });
  });

  it('submits updated notification prefs on save', async () => {
    const user = userEvent.setup();
    render(<NotificationPrefs />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('np-reminder-time-input')).toHaveValue('07:00');
    });

    await user.click(screen.getByTestId('save-notification-prefs-btn'));

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          day_of_reminder_time: '07:00',
          sms_time_window_start: '08:00',
          sms_time_window_end: '21:00',
          enable_delay_notifications: true,
        })
      );
    });
  });
});

describe('EstimateDefaults', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders estimate default fields with loaded data', async () => {
    render(<EstimateDefaults />, { wrapper: createWrapper() });

    expect(screen.getByTestId('estimate-defaults-section')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId('ed-valid-days-input')).toHaveValue(30);
    });
    expect(screen.getByTestId('ed-follow-up-intervals-input')).toHaveValue('3,7,14,21');
  });

  it('renders auto follow-ups toggle as checked', async () => {
    render(<EstimateDefaults />, { wrapper: createWrapper() });

    await waitFor(() => {
      const toggle = screen.getByTestId('ed-auto-followups-toggle');
      expect(toggle).toBeInTheDocument();
      expect(toggle.getAttribute('data-state')).toBe('checked');
    });
  });

  it('shows validation error for invalid follow-up intervals', async () => {
    const user = userEvent.setup();
    render(<EstimateDefaults />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('ed-follow-up-intervals-input')).toHaveValue('3,7,14,21');
    });

    const intervalsInput = screen.getByTestId('ed-follow-up-intervals-input');
    await user.clear(intervalsInput);
    await user.type(intervalsInput, 'abc');
    await user.click(screen.getByTestId('save-estimate-defaults-btn'));

    await waitFor(() => {
      expect(screen.getByText('Must be comma-separated numbers (e.g. 3,7,14,21)')).toBeInTheDocument();
    });
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it('submits updated estimate defaults on save', async () => {
    const user = userEvent.setup();
    render(<EstimateDefaults />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('ed-valid-days-input')).toHaveValue(30);
    });

    const validDaysInput = screen.getByTestId('ed-valid-days-input');
    await user.clear(validDaysInput);
    await user.type(validDaysInput, '60');
    await user.click(screen.getByTestId('save-estimate-defaults-btn'));

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({ default_valid_days: 60 })
      );
    });
  });
});
