/**
 * Tests for ScheduleMobile page wrapper.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';

vi.mock('@/features/resource-mobile', () => ({
  ResourceMobileView: () => <div data-testid="resource-mobile-page" />,
}));

import { ScheduleMobilePage } from './ScheduleMobile';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}

describe('ScheduleMobilePage', () => {
  it('renders ResourceMobileView', () => {
    render(<ScheduleMobilePage />, { wrapper });
    expect(screen.getByTestId('resource-mobile-page')).toBeInTheDocument();
  });
});
