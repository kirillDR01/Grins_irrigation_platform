import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { OnboardingIncompleteQueue } from './OnboardingIncompleteQueue';
import * as hooks from '../hooks/useAgreements';

vi.mock('../hooks/useAgreements', () => ({
  useOnboardingIncomplete: vi.fn(),
  agreementKeys: {
    all: ['agreements'],
    lists: () => ['agreements', 'list'],
    list: (p: unknown) => ['agreements', 'list', p],
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}

describe('OnboardingIncompleteQueue', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders empty state', () => {
    vi.mocked(hooks.useOnboardingIncomplete).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useOnboardingIncomplete>);

    render(<OnboardingIncompleteQueue />, { wrapper });
    expect(screen.getByText(/no incomplete onboarding/i)).toBeInTheDocument();
  });

  it('renders agreements with no property', () => {
    vi.mocked(hooks.useOnboardingIncomplete).mockReturnValue({
      data: [
        {
          id: 'o1',
          agreement_number: 'AGR-2026-030',
          customer_name: 'Charlie Onboard',
          created_at: '2026-03-01T00:00:00Z',
        },
      ],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useOnboardingIncomplete>);

    render(<OnboardingIncompleteQueue />, { wrapper });
    expect(screen.getByTestId('onboarding-incomplete-queue')).toBeInTheDocument();
    expect(screen.getByTestId('onboarding-row-o1')).toBeInTheDocument();
    expect(screen.getByText('AGR-2026-030')).toBeInTheDocument();
    expect(screen.getByText('Charlie Onboard')).toBeInTheDocument();
    expect(screen.getByText('No property')).toBeInTheDocument();
  });

  it('renders error state', () => {
    vi.mocked(hooks.useOnboardingIncomplete).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('fail'),
    } as unknown as ReturnType<typeof hooks.useOnboardingIncomplete>);

    render(<OnboardingIncompleteQueue />, { wrapper });
    expect(screen.getByText(/failed to load onboarding queue/i)).toBeInTheDocument();
  });
});
