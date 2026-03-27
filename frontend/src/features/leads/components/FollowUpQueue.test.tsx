import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { FollowUpQueue } from './FollowUpQueue';
import { leadApi } from '../api/leadApi';
import type { FollowUpLead } from '../types';

vi.mock('../api/leadApi', () => ({
  leadApi: {
    followUpQueue: vi.fn(),
    update: vi.fn(),
  },
}));

const mockFollowUpLeads: FollowUpLead[] = [
  {
    id: 'fu-001',
    name: 'Alice Brown',
    phone: '6125551111',
    email: null,
    address: null,
    city: null,
    state: null,
    zip_code: '55401',
    situation: 'repair',
    notes: 'Broken sprinkler head',
    source_site: 'residential',
    status: 'new',
    assigned_to: null,
    customer_id: null,
    contacted_at: null,
    converted_at: null,
    lead_source: 'phone_call',
    source_detail: 'Inbound call',
    intake_tag: 'follow_up',
    action_tags: [],
    sms_consent: false,
    terms_accepted: false,
    email_marketing_consent: false,
    created_at: '2025-01-20T06:00:00Z',
    updated_at: '2025-01-20T06:00:00Z',
    time_since_created: 14, // red urgency (>=12h)
  },
  {
    id: 'fu-002',
    name: 'Bob Green',
    phone: '6125552222',
    email: 'bob@example.com',
    address: null,
    city: null,
    state: null,
    zip_code: '55402',
    situation: 'new_system',
    notes: null,
    source_site: 'residential',
    status: 'contacted',
    assigned_to: null,
    customer_id: null,
    contacted_at: null,
    converted_at: null,
    lead_source: 'website',
    source_detail: null,
    intake_tag: 'follow_up',
    action_tags: [],
    sms_consent: true,
    terms_accepted: true,
    email_marketing_consent: true,
    created_at: '2025-01-20T14:00:00Z',
    updated_at: '2025-01-20T14:00:00Z',
    time_since_created: 5, // yellow urgency (2-12h)
  },
];

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>{children}</BrowserRouter>
      </QueryClientProvider>
    );
  };
}

describe('FollowUpQueue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when queue is empty', async () => {
    vi.mocked(leadApi.followUpQueue).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
    });

    const { container } = render(<FollowUpQueue />, { wrapper: createWrapper() });

    // Wait for query to settle
    await waitFor(() => {
      expect(leadApi.followUpQueue).toHaveBeenCalled();
    });

    expect(container.querySelector('[data-testid="follow-up-queue"]')).not.toBeInTheDocument();
  });

  it('renders queue with leads and count badge', async () => {
    vi.mocked(leadApi.followUpQueue).mockResolvedValue({
      items: mockFollowUpLeads,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<FollowUpQueue />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('follow-up-queue')).toBeInTheDocument();
    });

    expect(screen.getByText('Follow-Up Queue')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument(); // count badge
    expect(screen.getByTestId('follow-up-lead-fu-001')).toBeInTheDocument();
    expect(screen.getByTestId('follow-up-lead-fu-002')).toBeInTheDocument();
    expect(screen.getByText('Alice Brown')).toBeInTheDocument();
    expect(screen.getByText('Bob Green')).toBeInTheDocument();
  });

  it('shows urgency indicators based on time_since_created', async () => {
    vi.mocked(leadApi.followUpQueue).mockResolvedValue({
      items: mockFollowUpLeads,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<FollowUpQueue />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('follow-up-queue')).toBeInTheDocument();
    });

    // 14h → red, 5h → yellow
    expect(screen.getByText('14h ago')).toBeInTheDocument();
    expect(screen.getByText('5h ago')).toBeInTheDocument();
  });

  it('renders move-to-schedule and mark-lost action buttons', async () => {
    vi.mocked(leadApi.followUpQueue).mockResolvedValue({
      items: mockFollowUpLeads,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<FollowUpQueue />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('follow-up-queue')).toBeInTheDocument();
    });

    expect(screen.getByTestId('move-schedule-fu-001')).toBeInTheDocument();
    expect(screen.getByTestId('mark-lost-fu-001')).toBeInTheDocument();
    expect(screen.getByTestId('move-schedule-fu-002')).toBeInTheDocument();
    expect(screen.getByTestId('mark-lost-fu-002')).toBeInTheDocument();
  });

  it('calls update API with intake_tag=schedule on move-to-schedule click', async () => {
    const user = userEvent.setup();
    vi.mocked(leadApi.followUpQueue).mockResolvedValue({
      items: mockFollowUpLeads,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });
    vi.mocked(leadApi.update).mockResolvedValue({ ...mockFollowUpLeads[0], intake_tag: 'schedule' });

    render(<FollowUpQueue />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('move-schedule-fu-001')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('move-schedule-fu-001'));

    await waitFor(() => {
      expect(leadApi.update).toHaveBeenCalledWith('fu-001', { intake_tag: 'schedule' });
    });
  });

  it('calls update API with status=lost on mark-lost click', async () => {
    const user = userEvent.setup();
    vi.mocked(leadApi.followUpQueue).mockResolvedValue({
      items: mockFollowUpLeads,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });
    vi.mocked(leadApi.update).mockResolvedValue({ ...mockFollowUpLeads[0], status: 'lost' });

    render(<FollowUpQueue />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('mark-lost-fu-001')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('mark-lost-fu-001'));

    await waitFor(() => {
      expect(leadApi.update).toHaveBeenCalledWith('fu-001', { status: 'lost' });
    });
  });

  it('collapses and expands on header click', async () => {
    const user = userEvent.setup();
    vi.mocked(leadApi.followUpQueue).mockResolvedValue({
      items: mockFollowUpLeads,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<FollowUpQueue />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('follow-up-queue')).toBeInTheDocument();
    });

    // Initially expanded — leads visible
    expect(screen.getByText('Alice Brown')).toBeInTheDocument();

    // Click header to collapse
    await user.click(screen.getByText('Follow-Up Queue'));

    // Leads should be hidden
    expect(screen.queryByText('Alice Brown')).not.toBeInTheDocument();

    // Click again to expand
    await user.click(screen.getByText('Follow-Up Queue'));
    expect(screen.getByText('Alice Brown')).toBeInTheDocument();
  });
});
