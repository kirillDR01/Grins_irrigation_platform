import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CampaignResponsesView } from './CampaignResponsesView';
import type { Campaign, CampaignResponseSummary, CampaignResponseRow } from '../types/campaign';

// --- Mock data ---

const mockCampaign: Campaign = {
  id: 'camp-1',
  name: 'Spring Schedule',
  campaign_type: 'sms',
  status: 'sent',
  body: 'Pick a week',
  target_audience: null,
  subject: null,
  scheduled_at: null,
  sent_at: '2026-04-01T10:00:00Z',
  created_by: 's1',
  created_at: '2026-04-01T09:00:00Z',
  updated_at: '2026-04-01T09:00:00Z',
  poll_options: [
    { key: '1', label: 'Week of Apr 10', start_date: '2026-04-10', end_date: '2026-04-17' },
    { key: '2', label: 'Week of Apr 17', start_date: '2026-04-17', end_date: '2026-04-24' },
  ],
};

const mockSummary: CampaignResponseSummary = {
  campaign_id: 'camp-1',
  total_sent: 50,
  total_replied: 30,
  buckets: [
    { option_key: '1', option_label: 'Week of Apr 10', status: 'parsed', count: 15 },
    { option_key: '2', option_label: 'Week of Apr 17', status: 'parsed', count: 10 },
    { option_key: null, option_label: null, status: 'needs_review', count: 3 },
    { option_key: null, option_label: null, status: 'opted_out', count: 2 },
  ],
};

const mockRows: CampaignResponseRow[] = [
  {
    id: 'r1',
    campaign_id: 'camp-1',
    sent_message_id: 'sm1',
    customer_id: 'cust1',
    lead_id: null,
    phone: '+16125551234',
    recipient_name: 'Jane Doe',
    recipient_address: '123 Main St',
    selected_option_key: '1',
    selected_option_label: 'Week of Apr 10',
    raw_reply_body: '1',
    provider_message_id: 'pm1',
    status: 'parsed',
    received_at: '2026-04-02T14:00:00Z',
    created_at: '2026-04-02T14:00:00Z',
  },
  {
    id: 'r2',
    campaign_id: 'camp-1',
    sent_message_id: 'sm2',
    customer_id: null,
    lead_id: 'lead1',
    phone: '+16125555678',
    recipient_name: null,
    recipient_address: null,
    selected_option_key: '1',
    selected_option_label: 'Week of Apr 10',
    raw_reply_body: 'Option 1',
    provider_message_id: 'pm2',
    status: 'parsed',
    received_at: '2026-04-02T15:00:00Z',
    created_at: '2026-04-02T15:00:00Z',
  },
];

// --- Hook mocks ---

let mockSummaryReturn: unknown;
let mockResponsesReturn: unknown;

vi.mock('../hooks/useCampaignResponses', () => ({
  useCampaignResponseSummary: () => mockSummaryReturn,
  useCampaignResponses: () => mockResponsesReturn,
}));

describe('CampaignResponsesView', () => {
  const onBack = vi.fn();

  beforeEach(() => {
    onBack.mockReset();
    mockSummaryReturn = { data: mockSummary, isLoading: false };
    mockResponsesReturn = {
      data: { items: mockRows, total: 2, page: 1, page_size: 20 },
      isLoading: false,
    };
  });

  // --- Summary header ---

  it('renders summary header with correct counts', () => {
    render(<CampaignResponsesView campaign={mockCampaign} onBack={onBack} />);
    const header = screen.getByTestId('response-summary-header');
    expect(header).toHaveTextContent('50'); // total sent
    expect(header).toHaveTextContent('30'); // total replied
    expect(header).toHaveTextContent('25'); // parsed (15+10)
    expect(header).toHaveTextContent('3');  // needs review
    expect(header).toHaveTextContent('2');  // opted out
  });

  it('shows loading state while summary is loading', () => {
    mockSummaryReturn = { data: undefined, isLoading: true };
    render(<CampaignResponsesView campaign={mockCampaign} onBack={onBack} />);
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  // --- Per-option buckets ---

  it('renders per-option buckets with correct labels and counts', () => {
    render(<CampaignResponsesView campaign={mockCampaign} onBack={onBack} />);
    const bucket1 = screen.getByTestId('bucket-option-1');
    expect(bucket1).toHaveTextContent('Week of Apr 10');
    expect(bucket1).toHaveTextContent('15 responses');

    const bucket2 = screen.getByTestId('bucket-option-2');
    expect(bucket2).toHaveTextContent('Week of Apr 17');
    expect(bucket2).toHaveTextContent('10 responses');
  });

  it('renders needs review bucket with count', () => {
    render(<CampaignResponsesView campaign={mockCampaign} onBack={onBack} />);
    const bucket = screen.getByTestId('bucket-needs-review');
    expect(bucket).toHaveTextContent('3 responses');
  });

  it('renders opted out bucket with count', () => {
    render(<CampaignResponsesView campaign={mockCampaign} onBack={onBack} />);
    const bucket = screen.getByTestId('bucket-opted-out');
    expect(bucket).toHaveTextContent('2 responses');
  });

  // --- Drill-down table ---

  it('opens drill-down table on View click for an option bucket', () => {
    render(<CampaignResponsesView campaign={mockCampaign} onBack={onBack} />);
    expect(screen.queryByTestId('drilldown-table')).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId('view-option-1-btn'));
    expect(screen.getByTestId('drilldown-table')).toBeInTheDocument();
    // Verify table columns
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Phone')).toBeInTheDocument();
    expect(screen.getByText('Raw Reply')).toBeInTheDocument();
    expect(screen.getByText('Received At')).toBeInTheDocument();
  });

  it('renders response rows in drill-down table', () => {
    render(<CampaignResponsesView campaign={mockCampaign} onBack={onBack} />);
    fireEvent.click(screen.getByTestId('view-option-1-btn'));
    const rows = screen.getAllByTestId('response-row');
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent('Jane Doe');
    expect(rows[1]).toHaveTextContent('—'); // null recipient_name
  });

  it('opens drill-down for needs review bucket', () => {
    render(<CampaignResponsesView campaign={mockCampaign} onBack={onBack} />);
    fireEvent.click(screen.getByTestId('view-needs-review-btn'));
    const table = screen.getByTestId('drilldown-table');
    expect(table).toBeInTheDocument();
    // Card title inside drill-down shows "Needs Review"
    expect(table.querySelector('[data-slot="card-title"]')).toHaveTextContent('Needs Review');
  });

  it('opens drill-down for opted out bucket', () => {
    render(<CampaignResponsesView campaign={mockCampaign} onBack={onBack} />);
    fireEvent.click(screen.getByTestId('view-opted-out-btn'));
    const table = screen.getByTestId('drilldown-table');
    expect(table).toBeInTheDocument();
    expect(table.querySelector('[data-slot="card-title"]')).toHaveTextContent('Opted Out');
  });

  // --- CSV download ---

  it('renders export all CSV link with correct href', () => {
    render(<CampaignResponsesView campaign={mockCampaign} onBack={onBack} />);
    const link = screen.getByTestId('export-all-csv-btn');
    expect(link).toHaveAttribute(
      'href',
      expect.stringContaining(`/campaigns/camp-1/responses/export.csv`),
    );
    expect(link).toHaveAttribute('download');
  });

  it('renders per-option CSV link with option_key param', () => {
    render(<CampaignResponsesView campaign={mockCampaign} onBack={onBack} />);
    const link = screen.getByTestId('csv-option-1-btn');
    expect(link).toHaveAttribute(
      'href',
      expect.stringContaining('export.csv?option_key=1'),
    );
  });

  // --- Back button ---

  it('calls onBack when back button is clicked', () => {
    render(<CampaignResponsesView campaign={mockCampaign} onBack={onBack} />);
    fireEvent.click(screen.getByText('Back'));
    expect(onBack).toHaveBeenCalledOnce();
  });

  // --- Campaign title ---

  it('displays campaign name in title', () => {
    render(<CampaignResponsesView campaign={mockCampaign} onBack={onBack} />);
    expect(screen.getByText('Spring Schedule — Responses')).toBeInTheDocument();
  });
});
