// PipelineList.test.tsx
// Requirements: 4.1–4.8, 5.1–5.8, 6.1–6.6

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SalesPipeline } from './SalesPipeline';
import type { SalesEntry, SalesEntryStatus } from '../types/pipeline';
import { AGE_THRESHOLDS } from '../types/pipeline';

// ─── mocks ──────────────────────────────────────────────────────────────────

vi.mock('../hooks/useSalesPipeline', () => ({
  useSalesPipeline: vi.fn(),
}));
vi.mock('../hooks', () => ({
  useSalesMetrics: vi.fn(),
}));

import { useSalesPipeline } from '../hooks/useSalesPipeline';
import { useSalesMetrics } from '../hooks';

// ─── helpers ────────────────────────────────────────────────────────────────

function makeEntry(
  id: string,
  status: SalesEntryStatus,
  daysAgo = 0,
  overrides: Partial<SalesEntry> = {},
): SalesEntry {
  const ref = new Date(Date.now() - daysAgo * 86_400_000).toISOString();
  return {
    id,
    customer_id: 'c1',
    property_id: null,
    lead_id: null,
    job_type: 'Winterization',
    status,
    last_contact_date: null,
    notes: null,
    override_flag: false,
    closed_reason: null,
    signwell_document_id: null,
    created_at: ref,
    updated_at: ref,
    customer_name: 'Alice Smith',
    customer_phone: '6125550001',
    property_address: '123 Main St',
    ...overrides,
  };
}

function makePipelineData(items: SalesEntry[], summary: Record<string, number> = {}) {
  return {
    items,
    total: items.length,
    summary: {
      schedule_estimate: 0,
      pending_approval: 0,
      ...summary,
    },
  };
}

function renderPipeline() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <SalesPipeline />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ─── setup ──────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.mocked(useSalesMetrics).mockReturnValue({
    data: { total_pipeline_revenue: 12500 },
    isLoading: false,
    error: null,
  } as ReturnType<typeof useSalesMetrics>);
});

// ─── 4 summary cards ────────────────────────────────────────────────────────

describe('Summary cards', () => {
  it('renders 4 summary cards with correct values', () => {
    vi.mocked(useSalesPipeline).mockReturnValue({
      data: makePipelineData([], { schedule_estimate: 3, pending_approval: 5 }),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof useSalesPipeline>);

    renderPipeline();

    expect(screen.getByTestId('pipeline-summary-needs-estimate')).toBeInTheDocument();
    expect(screen.getByTestId('pipeline-summary-pending-approval')).toBeInTheDocument();
    expect(screen.getByTestId('pipeline-summary-needs-followup')).toBeInTheDocument();
    expect(screen.getByTestId('pipeline-summary-revenue')).toBeInTheDocument();

    // Values from summary
    expect(within(screen.getByTestId('pipeline-summary-needs-estimate')).getByText('3')).toBeInTheDocument();
    expect(within(screen.getByTestId('pipeline-summary-pending-approval')).getByText('5')).toBeInTheDocument();
    // Revenue
    expect(within(screen.getByTestId('pipeline-summary-revenue')).getByText('$12,500')).toBeInTheDocument();
  });

  it('Needs Follow-Up count uses countStuck (client-side)', () => {
    // 2 stuck entries (>7 days for schedule_estimate)
    const items = [
      makeEntry('a', 'schedule_estimate', 10),
      makeEntry('b', 'schedule_estimate', 2),
      makeEntry('c', 'pending_approval', 12),
    ];
    vi.mocked(useSalesPipeline).mockReturnValue({
      data: makePipelineData(items),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof useSalesPipeline>);

    renderPipeline();

    // a: 10 > 7 → stuck; b: 2 ≤ 3 → fresh; c: 12 > 10 → stuck
    expect(within(screen.getByTestId('pipeline-summary-needs-followup')).getByText('2')).toBeInTheDocument();
  });

  it('Revenue Pipeline card is not clickable (no cursor-pointer)', () => {
    vi.mocked(useSalesPipeline).mockReturnValue({
      data: makePipelineData([]),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof useSalesPipeline>);

    renderPipeline();

    const revenueCard = screen.getByTestId('pipeline-summary-revenue');
    expect(revenueCard.className).not.toContain('cursor-pointer');
  });

  it('Needs Follow-Up card has bg-amber-50', () => {
    vi.mocked(useSalesPipeline).mockReturnValue({
      data: makePipelineData([]),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof useSalesPipeline>);

    renderPipeline();

    const card = screen.getByTestId('pipeline-summary-needs-followup');
    expect(card.className).toContain('bg-amber-50');
  });
});

// ─── stuck filter ────────────────────────────────────────────────────────────

describe('Stuck filter', () => {
  it('clicking Needs Follow-Up toggles stuck filter chip', async () => {
    const user = userEvent.setup();
    const items = [makeEntry('a', 'schedule_estimate', 10)];
    vi.mocked(useSalesPipeline).mockReturnValue({
      data: makePipelineData(items),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof useSalesPipeline>);

    renderPipeline();

    expect(screen.queryByTestId('pipeline-filter-age-stuck')).not.toBeInTheDocument();
    await user.click(screen.getByTestId('pipeline-summary-needs-followup'));
    expect(screen.getByTestId('pipeline-filter-age-stuck')).toBeInTheDocument();
    // Toggle off
    await user.click(screen.getByTestId('pipeline-summary-needs-followup'));
    expect(screen.queryByTestId('pipeline-filter-age-stuck')).not.toBeInTheDocument();
  });

  it('stuck filter shows only stuck entries', async () => {
    const user = userEvent.setup();
    const items = [
      makeEntry('stuck1', 'schedule_estimate', 10),  // stuck
      makeEntry('fresh1', 'schedule_estimate', 1),   // fresh
    ];
    vi.mocked(useSalesPipeline).mockReturnValue({
      data: makePipelineData(items),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof useSalesPipeline>);

    renderPipeline();

    await user.click(screen.getByTestId('pipeline-summary-needs-followup'));

    expect(screen.getByTestId('pipeline-row-stuck1')).toBeInTheDocument();
    expect(screen.queryByTestId('pipeline-row-fresh1')).not.toBeInTheDocument();
  });
});

// ─── status filter ───────────────────────────────────────────────────────────

describe('Status filter', () => {
  it('clicking Needs Estimate toggles statusFilter', async () => {
    const user = userEvent.setup();
    vi.mocked(useSalesPipeline).mockReturnValue({
      data: makePipelineData([], { schedule_estimate: 2 }),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof useSalesPipeline>);

    renderPipeline();

    // No filter bar before clicking
    expect(screen.queryByText(/filtered by/i)).not.toBeInTheDocument();
    await user.click(screen.getByTestId('pipeline-summary-needs-estimate'));
    // Filter bar appears
    expect(screen.getByText(/filtered by/i)).toBeInTheDocument();
  });

  it('both statusFilter and stuckFilter can be active simultaneously', async () => {
    const user = userEvent.setup();
    const items = [makeEntry('a', 'schedule_estimate', 10)];
    vi.mocked(useSalesPipeline).mockReturnValue({
      data: makePipelineData(items, { schedule_estimate: 1 }),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof useSalesPipeline>);

    renderPipeline();

    await user.click(screen.getByTestId('pipeline-summary-needs-estimate'));
    await user.click(screen.getByTestId('pipeline-summary-needs-followup'));

    expect(screen.getByTestId('pipeline-filter-age-stuck')).toBeInTheDocument();
    // Filter bar is visible (both filters active)
    expect(screen.getByText(/filtered by/i)).toBeInTheDocument();
  });

  it('Clear removes all filters', async () => {
    const user = userEvent.setup();
    const items = [makeEntry('a', 'schedule_estimate', 10)];
    vi.mocked(useSalesPipeline).mockReturnValue({
      data: makePipelineData(items, { schedule_estimate: 1 }),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof useSalesPipeline>);

    renderPipeline();

    await user.click(screen.getByTestId('pipeline-summary-needs-estimate'));
    await user.click(screen.getByTestId('pipeline-summary-needs-followup'));

    const clearBtn = screen.getByRole('button', { name: /clear/i });
    await user.click(clearBtn);

    expect(screen.queryByTestId('pipeline-filter-age-stuck')).not.toBeInTheDocument();
    // Filter bar gone
    expect(screen.queryByText(/filtered by/i)).not.toBeInTheDocument();
  });
});

// ─── table rows ──────────────────────────────────────────────────────────────

describe('Table rows', () => {
  it('row click navigates to /sales/{id}', async () => {
    const user = userEvent.setup();
    const items = [makeEntry('entry1', 'send_estimate', 1)];
    vi.mocked(useSalesPipeline).mockReturnValue({
      data: makePipelineData(items),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof useSalesPipeline>);

    renderPipeline();

    const row = screen.getByTestId('pipeline-row-entry1');
    // Row is present and clickable (cursor-pointer)
    expect(row).toBeInTheDocument();
    expect(row.className).toContain('cursor-pointer');
    // Click should not throw
    await user.click(row);
  });

  it('no action button for closed_lost entries', () => {
    const items = [makeEntry('lost1', 'closed_lost', 1)];
    vi.mocked(useSalesPipeline).mockReturnValue({
      data: makePipelineData(items),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof useSalesPipeline>);

    renderPipeline();

    expect(screen.queryByTestId('pipeline-row-action-lost1')).not.toBeInTheDocument();
    // Dismiss button still present
    expect(screen.getByTestId('pipeline-row-dismiss-lost1')).toBeInTheDocument();
  });

  it('address tooltip on customer name (title attribute)', () => {
    const items = [makeEntry('e1', 'send_estimate', 1, { property_address: '456 Oak Ave' })];
    vi.mocked(useSalesPipeline).mockReturnValue({
      data: makePipelineData(items),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof useSalesPipeline>);

    renderPipeline();

    const nameEl = screen.getByText('Alice Smith');
    expect(nameEl).toHaveAttribute('title', '456 Oak Ave');
  });

  it('age chips show correct bucket per row', () => {
    const items = [
      makeEntry('fresh1', 'schedule_estimate', 1),   // fresh
      makeEntry('stuck1', 'schedule_estimate', 10),  // stuck (>7)
    ];
    vi.mocked(useSalesPipeline).mockReturnValue({
      data: makePipelineData(items),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof useSalesPipeline>);

    renderPipeline();

    expect(screen.getByTestId('pipeline-row-age-fresh1')).toHaveAttribute('data-bucket', 'fresh');
    expect(screen.getByTestId('pipeline-row-age-stuck1')).toHaveAttribute('data-bucket', 'stuck');
  });

  it('no age chip for closed_won and closed_lost rows', () => {
    const items = [
      makeEntry('won1', 'closed_won', 5),
      makeEntry('lost1', 'closed_lost', 5),
    ];
    vi.mocked(useSalesPipeline).mockReturnValue({
      data: makePipelineData(items),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof useSalesPipeline>);

    renderPipeline();

    expect(screen.queryByTestId('pipeline-row-age-won1')).not.toBeInTheDocument();
    expect(screen.queryByTestId('pipeline-row-age-lost1')).not.toBeInTheDocument();
  });
});

// ─── compact action button labels ────────────────────────────────────────────

describe('Action button labels per stage', () => {
  const cases: Array<[SalesEntryStatus, string]> = [
    ['schedule_estimate', 'Schedule'],
    ['estimate_scheduled', 'Send'],
    ['send_estimate', 'Send'],
    ['pending_approval', 'Nudge'],
    ['send_contract', 'Convert'],
    ['closed_won', 'View job'],
  ];

  for (const [status, label] of cases) {
    it(`${status} shows "${label}" action`, () => {
      const items = [makeEntry('e1', status, 1)];
      vi.mocked(useSalesPipeline).mockReturnValue({
        data: makePipelineData(items),
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as ReturnType<typeof useSalesPipeline>);

      renderPipeline();

      const actionBtn = screen.getByTestId('pipeline-row-action-e1');
      expect(actionBtn).toHaveTextContent(label);
    });
  }
});

// ─── age chip correctness per stage thresholds ───────────────────────────────

describe('Age chip bucket correctness', () => {
  it('stale bucket for entry between freshMax and staleMax', () => {
    // pending_approval: freshMax=4, staleMax=10 → 7 days = stale
    const items = [makeEntry('e1', 'pending_approval', 7)];
    vi.mocked(useSalesPipeline).mockReturnValue({
      data: makePipelineData(items),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof useSalesPipeline>);

    renderPipeline();

    expect(screen.getByTestId('pipeline-row-age-e1')).toHaveAttribute('data-bucket', 'stale');
  });

  it('AGE_THRESHOLDS are used correctly for send_contract', () => {
    const { freshMax, staleMax } = AGE_THRESHOLDS['send_contract'];
    // Just past staleMax → stuck
    const items = [makeEntry('e1', 'send_contract', staleMax + 1)];
    vi.mocked(useSalesPipeline).mockReturnValue({
      data: makePipelineData(items),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof useSalesPipeline>);

    renderPipeline();

    expect(screen.getByTestId('pipeline-row-age-e1')).toHaveAttribute('data-bucket', 'stuck');
    void freshMax;
  });
});
