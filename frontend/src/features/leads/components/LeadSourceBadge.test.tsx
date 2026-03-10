import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LeadSourceBadge } from './LeadSourceBadge';
import type { LeadSource } from '../types';
import { LEAD_SOURCE_COLORS, LEAD_SOURCE_LABELS } from '../types';

describe('LeadSourceBadge', () => {
  const allSources: LeadSource[] = [
    'website', 'google_form', 'phone_call', 'text_message', 'google_ad',
    'social_media', 'qr_code', 'email_campaign', 'text_campaign', 'referral', 'other',
  ];

  it.each(allSources)('renders correct label and data-testid for source "%s"', (source) => {
    render(<LeadSourceBadge source={source} />);
    const badge = screen.getByTestId(`lead-source-${source}`);
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent(LEAD_SOURCE_LABELS[source]);
  });

  it.each(allSources)('applies correct color class for source "%s"', (source) => {
    render(<LeadSourceBadge source={source} />);
    const badge = screen.getByTestId(`lead-source-${source}`);
    const expectedColor = LEAD_SOURCE_COLORS[source];
    // Each color string contains two classes (bg-* and text-*)
    for (const cls of expectedColor.split(' ')) {
      expect(badge.className).toContain(cls);
    }
  });

  it('applies additional className when provided', () => {
    render(<LeadSourceBadge source="website" className="ml-2" />);
    const badge = screen.getByTestId('lead-source-website');
    expect(badge.className).toContain('ml-2');
  });
});
