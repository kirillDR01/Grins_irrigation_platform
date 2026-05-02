import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ContractSigning } from './ContractSigning';
import type { PortalContract } from '../types';

const mockContractData: PortalContract = {
  company_name: 'Grins Irrigation',
  company_logo_url: 'https://example.com/logo.png',
  company_address: '123 Main St',
  company_phone: '(555) 123-4567',
  customer_name: 'John Smith',
  contract_body: '<p>This is the contract body with <strong>terms</strong> for irrigation services.</p>',
  terms_and_conditions: '<p>Standard terms and conditions apply.</p>',
  is_signed: false,
  signed_at: null,
};

const mockUsePortalContract = vi.fn();
const mockSignContract = vi.fn();

vi.mock('../hooks', () => ({
  usePortalContract: (...args: unknown[]) => mockUsePortalContract(...args),
  useSignContract: () => ({
    mutateAsync: mockSignContract,
    isPending: false,
  }),
}));

function renderWithProviders(token = 'contract-token-123') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/portal/contracts/${token}`]}>
        <Routes>
          <Route path="/portal/contracts/:token" element={<ContractSigning />} />
          <Route path="/portal/contracts/:token/confirmed" element={<div data-testid="confirmed-page">Confirmed</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('ContractSigning', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state', () => {
    mockUsePortalContract.mockReturnValue({ data: undefined, isLoading: true, error: null });
    renderWithProviders();
    expect(screen.getByTestId('contract-loading')).toBeInTheDocument();
  });

  it('renders expired state for 410 error', () => {
    mockUsePortalContract.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: { response: { status: 410 } },
    });
    renderWithProviders();
    expect(screen.getByTestId('contract-expired')).toBeInTheDocument();
    expect(screen.getByText('Link Expired')).toBeInTheDocument();
  });

  it('renders error state for other errors', () => {
    mockUsePortalContract.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: { response: { status: 500 } },
    });
    renderWithProviders();
    expect(screen.getByTestId('contract-error')).toBeInTheDocument();
  });

  it('renders contract details with company branding', () => {
    mockUsePortalContract.mockReturnValue({ data: mockContractData, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByTestId('contract-signing-page')).toBeInTheDocument();
    expect(screen.getByTestId('company-logo')).toBeInTheDocument();
    expect(screen.getByText('Grins Irrigation')).toBeInTheDocument();
    expect(screen.getByText('John Smith')).toBeInTheDocument();
  });

  it('renders contract body HTML', () => {
    mockUsePortalContract.mockReturnValue({ data: mockContractData, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByTestId('contract-body')).toBeInTheDocument();
    expect(screen.getByText('terms')).toBeInTheDocument();
  });

  it('renders terms and conditions when present', () => {
    mockUsePortalContract.mockReturnValue({ data: mockContractData, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByTestId('contract-terms')).toBeInTheDocument();
  });

  it('renders signature section when not signed', () => {
    mockUsePortalContract.mockReturnValue({ data: mockContractData, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByTestId('signature-section')).toBeInTheDocument();
    expect(screen.getByTestId('signature-canvas')).toBeInTheDocument();
    expect(screen.getByTestId('sign-contract-btn')).toBeInTheDocument();
  });

  it('disables sign button when no signature drawn', () => {
    mockUsePortalContract.mockReturnValue({ data: mockContractData, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByTestId('sign-contract-btn')).toBeDisabled();
  });

  it('shows signed notice when contract is already signed', () => {
    const signedContract: PortalContract = {
      ...mockContractData,
      is_signed: true,
      signed_at: '2025-06-15T14:30:00Z',
    };
    mockUsePortalContract.mockReturnValue({ data: signedContract, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByTestId('contract-signed-notice')).toBeInTheDocument();
    expect(screen.queryByTestId('signature-section')).not.toBeInTheDocument();
  });
});
