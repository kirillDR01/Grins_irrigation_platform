import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProcessingStatusBadge } from './ProcessingStatusBadge';
import type { ProcessingStatus } from '../types';
import { PROCESSING_STATUS_LABELS } from '../types';

describe('ProcessingStatusBadge', () => {
  const statuses: ProcessingStatus[] = ['imported', 'lead_created', 'skipped', 'error'];

  it.each(statuses)('renders correct label for "%s" status', (status) => {
    render(<ProcessingStatusBadge status={status} />);
    expect(screen.getByTestId(`status-${status}`)).toHaveTextContent(
      PROCESSING_STATUS_LABELS[status]
    );
  });

  it('renders blue badge for imported status', () => {
    render(<ProcessingStatusBadge status="imported" />);
    const badge = screen.getByTestId('status-imported');
    expect(badge.className).toContain('bg-blue-100');
    expect(badge.className).toContain('text-blue-800');
  });

  it('renders green badge for lead_created status', () => {
    render(<ProcessingStatusBadge status="lead_created" />);
    const badge = screen.getByTestId('status-lead_created');
    expect(badge.className).toContain('bg-green-100');
    expect(badge.className).toContain('text-green-800');
  });

  it('renders gray badge for skipped status', () => {
    render(<ProcessingStatusBadge status="skipped" />);
    const badge = screen.getByTestId('status-skipped');
    expect(badge.className).toContain('bg-gray-100');
    expect(badge.className).toContain('text-gray-800');
  });

  it('renders red badge for error status', () => {
    render(<ProcessingStatusBadge status="error" />);
    const badge = screen.getByTestId('status-error');
    expect(badge.className).toContain('bg-red-100');
    expect(badge.className).toContain('text-red-800');
  });

  it('applies custom className', () => {
    render(<ProcessingStatusBadge status="imported" className="ml-2" />);
    const badge = screen.getByTestId('status-imported');
    expect(badge.className).toContain('ml-2');
  });
});
