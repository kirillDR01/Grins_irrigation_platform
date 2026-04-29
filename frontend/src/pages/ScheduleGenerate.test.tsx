/**
 * Tests for ScheduleGenerate page wrapper.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';

vi.mock('@/features/schedule', () => ({
  AIScheduleView: () => <div data-testid="ai-schedule-page" />,
  ScheduleGenerationPage: () => null,
}));

import { ScheduleGeneratePage } from './ScheduleGenerate';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}

describe('ScheduleGeneratePage', () => {
  it('renders AIScheduleView', () => {
    render(<ScheduleGeneratePage />, { wrapper });
    expect(screen.getByTestId('ai-schedule-page')).toBeInTheDocument();
  });
});
