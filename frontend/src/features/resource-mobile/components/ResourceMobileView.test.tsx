/**
 * Tests for ResourceMobileView composed page component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';

vi.mock('./ResourceScheduleView', () => ({
  ResourceScheduleView: () => <div data-testid="resource-schedule-view" />,
}));

vi.mock('@/features/ai', () => ({
  ResourceMobileChat: () => <div data-testid="resource-mobile-chat" />,
  SchedulingChat: () => null,
  PreJobChecklist: () => null,
  AILoadingState: () => null,
  AIErrorState: () => null,
  AIStreamingText: () => null,
  AIQueryChat: () => null,
  AIScheduleGenerator: () => null,
  AICategorization: () => null,
  AICommunicationDrafts: () => null,
  AIEstimateGenerator: () => null,
  MorningBriefing: () => null,
  CommunicationsQueue: () => null,
  useSchedulingChat: () => ({ messages: [], sendMessage: vi.fn(), isLoading: false }),
  schedulingChatKeys: { all: ['scheduling-chat'] },
}));

import { ResourceMobileView } from './ResourceMobileView';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}

describe('ResourceMobileView', () => {
  it('renders with data-testid="resource-mobile-page"', () => {
    render(<ResourceMobileView />, { wrapper });
    expect(screen.getByTestId('resource-mobile-page')).toBeInTheDocument();
  });

  it('renders ResourceScheduleView child', () => {
    render(<ResourceMobileView />, { wrapper });
    expect(screen.getByTestId('resource-schedule-view')).toBeInTheDocument();
  });

  it('renders ResourceMobileChat child', () => {
    render(<ResourceMobileView />, { wrapper });
    expect(screen.getByTestId('resource-mobile-chat')).toBeInTheDocument();
  });

  it('renders schedule view before chat (correct DOM ordering)', () => {
    render(<ResourceMobileView />, { wrapper });
    const page = screen.getByTestId('resource-mobile-page');
    const children = Array.from(page.children);
    const scheduleIdx = children.findIndex(
      (el) => el.getAttribute('data-testid') === 'resource-schedule-view'
    );
    const chatIdx = children.findIndex(
      (el) => el.getAttribute('data-testid') === 'resource-mobile-chat'
    );
    expect(scheduleIdx).toBeLessThan(chatIdx);
  });
});
