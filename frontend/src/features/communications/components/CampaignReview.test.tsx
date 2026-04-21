import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CampaignReview } from './CampaignReview';
import type { AudiencePreview } from '../types/campaign';

// Mock the segment counter to avoid coupling
vi.mock('../utils/segmentCounter', () => ({
  countSegments: vi.fn(() => ({ encoding: 'GSM-7', segments: 1, chars: 50 })),
  renderTemplate: vi.fn((text: string, ctx: Record<string, string>) =>
    text.replace(/\{(\w+)\}/g, (_, key: string) => ctx[key] ?? ''),
  ),
  SENDER_PREFIX: 'Grins Irrigation: ',
  STOP_FOOTER: ' Reply STOP to opt out.',
  ALLOWED_MERGE_FIELDS: ['first_name', 'last_name', 'next_appointment_date'],
}));

const basePreview: AudiencePreview = {
  total: 10,
  customers_count: 5,
  leads_count: 3,
  ad_hoc_count: 2,
  matches: [],
  non_central_count: 0,
};

function renderReview(overrides: Partial<Parameters<typeof CampaignReview>[0]> = {}) {
  const defaults = {
    preview: basePreview,
    messageBody: 'Hello!',
    onSendNow: vi.fn(),
    onSchedule: vi.fn(),
    isSending: false,
  };
  return { ...render(<CampaignReview {...defaults} {...overrides} />), ...defaults, ...overrides };
}

describe('CampaignReview', () => {
  it('renders per-source breakdown', () => {
    renderReview();
    expect(screen.getByTestId('customers-count')).toHaveTextContent('5');
    expect(screen.getByTestId('leads-count')).toHaveTextContent('3');
    expect(screen.getByTestId('adhoc-count')).toHaveTextContent('2');
  });

  it('shows consent filter breakdown', () => {
    renderReview();
    const breakdown = screen.getByTestId('consent-breakdown');
    expect(breakdown).toHaveTextContent('10 total');
    expect(breakdown).toHaveTextContent('10 will send');
  });

  it('shows blocked count when consent filters some', () => {
    // raw total = 5+3+2 = 10, but preview.total = 7 → 3 blocked
    renderReview({ preview: { ...basePreview, total: 7 } });
    expect(screen.getByTestId('consent-breakdown')).toHaveTextContent('3 blocked');
  });

  it('shows time estimate', () => {
    renderReview();
    const estimate = screen.getByTestId('time-estimate');
    // 10 recipients / 140 per hour ≈ 4.3 min → ~5 minutes
    expect(estimate).toHaveTextContent(/minute/);
  });

  it('formats time estimate for large audiences', () => {
    renderReview({ preview: { ...basePreview, total: 1000 } });
    const estimate = screen.getByTestId('time-estimate');
    // 1000/140 ≈ 7.1 hours → ~7.1 hours
    expect(estimate).toHaveTextContent(/hour/);
  });

  describe('typed confirmation for ≥50 recipients', () => {
    const largePreview: AudiencePreview = { ...basePreview, total: 75, customers_count: 75 };

    it('shows typed confirmation input for ≥50 recipients', () => {
      renderReview({ preview: largePreview });
      expect(screen.getByTestId('typed-confirmation')).toBeInTheDocument();
      expect(screen.getByTestId('confirmation-input')).toBeInTheDocument();
    });

    it('disables confirm button until correct text typed', () => {
      renderReview({ preview: largePreview });
      const confirmBtn = screen.getByTestId('confirm-send-btn');
      expect(confirmBtn).toBeDisabled();

      fireEvent.change(screen.getByTestId('confirmation-input'), {
        target: { value: 'SEND 75' },
      });
      expect(confirmBtn).not.toBeDisabled();
    });

    it('does not accept wrong confirmation text', () => {
      renderReview({ preview: largePreview });
      fireEvent.change(screen.getByTestId('confirmation-input'), {
        target: { value: 'SEND 50' },
      });
      expect(screen.getByTestId('confirm-send-btn')).toBeDisabled();
    });
  });

  describe('small audience (<50)', () => {
    it('shows simple confirmation without typed input', () => {
      renderReview();
      expect(screen.getByTestId('simple-confirmation')).toBeInTheDocument();
      expect(screen.queryByTestId('typed-confirmation')).not.toBeInTheDocument();
    });

    it('confirm button is enabled for small audience', () => {
      renderReview();
      expect(screen.getByTestId('confirm-send-btn')).not.toBeDisabled();
    });
  });

  it('calls onSendNow when confirm clicked in send-now mode', () => {
    const onSendNow = vi.fn();
    renderReview({ onSendNow });
    fireEvent.click(screen.getByTestId('confirm-send-btn'));
    expect(onSendNow).toHaveBeenCalledOnce();
  });

  it('calls onSchedule with ISO date when in schedule mode', () => {
    const onSchedule = vi.fn();
    renderReview({ onSchedule });

    fireEvent.click(screen.getByTestId('schedule-btn'));
    fireEvent.change(screen.getByTestId('schedule-date'), { target: { value: '2026-05-01' } });
    fireEvent.change(screen.getByTestId('schedule-time'), { target: { value: '10:30' } });
    fireEvent.click(screen.getByTestId('confirm-send-btn'));

    expect(onSchedule).toHaveBeenCalledWith(expect.stringMatching(/^2026-05-01T10:30:00/));
  });

  it('disables confirm when no recipients', () => {
    renderReview({ preview: { ...basePreview, total: 0 } });
    expect(screen.getByTestId('confirm-send-btn')).toBeDisabled();
  });

  it('disables confirm when isSending', () => {
    renderReview({ isSending: true });
    expect(screen.getByTestId('confirm-send-btn')).toBeDisabled();
  });

  it('shows timezone warning', () => {
    renderReview();
    expect(screen.getByTestId('timezone-warning')).toBeInTheDocument();
    expect(screen.getByTestId('timezone-warning')).toHaveTextContent('8 AM');
  });

  describe('merge field interpolation', () => {
    const previewWithRecipients: AudiencePreview = {
      ...basePreview,
      matches: [
        { phone_masked: '***1234', source_type: 'customer', first_name: 'John', last_name: 'Smith' },
        { phone_masked: '***5678', source_type: 'lead', first_name: 'Jane', last_name: 'Doe' },
      ],
    };

    it('interpolates {first_name} and {last_name} in the message preview', () => {
      renderReview({
        preview: previewWithRecipients,
        messageBody: 'Hi {first_name} {last_name}, your appointment is ready!',
      });
      const body = screen.getByTestId('message-preview-body');
      expect(body).toHaveTextContent('Hi John Smith, your appointment is ready!');
      expect(body).not.toHaveTextContent('{first_name}');
      expect(body).not.toHaveTextContent('{last_name}');
    });

    it('shows which recipient the preview is for', () => {
      renderReview({
        preview: previewWithRecipients,
        messageBody: 'Hi {first_name}!',
      });
      const note = screen.getByTestId('preview-recipient-note');
      expect(note).toHaveTextContent('Preview for: John Smith');
    });

    it('renders raw message when no recipients available', () => {
      renderReview({
        preview: { ...basePreview, matches: [] },
        messageBody: 'Hi {first_name}!',
      });
      expect(screen.getByTestId('message-preview-body')).toHaveTextContent('Hi {first_name}!');
      expect(screen.queryByTestId('preview-recipient-note')).not.toBeInTheDocument();
    });
  });
});
