import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { InvoiceStatusBadge } from './InvoiceStatusBadge';
import type { InvoiceStatus } from '../types';

describe('InvoiceStatusBadge', () => {
  const statuses: InvoiceStatus[] = [
    'draft',
    'sent',
    'viewed',
    'paid',
    'partial',
    'overdue',
    'lien_warning',
    'lien_filed',
    'cancelled',
  ];

  it.each(statuses)('renders %s status badge with correct data-testid', (status) => {
    render(<InvoiceStatusBadge status={status} />);
    expect(screen.getByTestId(`invoice-status-${status}`)).toBeInTheDocument();
  });

  it('renders draft status with gray badge', () => {
    render(<InvoiceStatusBadge status="draft" />);
    const badge = screen.getByTestId('invoice-status-draft');
    expect(badge).toHaveTextContent('Draft');
    expect(badge).toHaveClass('bg-gray-100', 'text-gray-800');
  });

  it('renders sent status with blue badge', () => {
    render(<InvoiceStatusBadge status="sent" />);
    const badge = screen.getByTestId('invoice-status-sent');
    expect(badge).toHaveTextContent('Sent');
    expect(badge).toHaveClass('bg-blue-100', 'text-blue-800');
  });

  it('renders paid status with green badge', () => {
    render(<InvoiceStatusBadge status="paid" />);
    const badge = screen.getByTestId('invoice-status-paid');
    expect(badge).toHaveTextContent('Paid');
    expect(badge).toHaveClass('bg-green-100', 'text-green-800');
  });

  it('renders partial status with yellow badge', () => {
    render(<InvoiceStatusBadge status="partial" />);
    const badge = screen.getByTestId('invoice-status-partial');
    expect(badge).toHaveTextContent('Partial');
    expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800');
  });

  it('renders overdue status with red badge', () => {
    render(<InvoiceStatusBadge status="overdue" />);
    const badge = screen.getByTestId('invoice-status-overdue');
    expect(badge).toHaveTextContent('Overdue');
    expect(badge).toHaveClass('bg-red-100', 'text-red-800');
  });

  it('renders lien_warning status with orange badge', () => {
    render(<InvoiceStatusBadge status="lien_warning" />);
    const badge = screen.getByTestId('invoice-status-lien_warning');
    expect(badge).toHaveTextContent('Lien Warning');
    expect(badge).toHaveClass('bg-orange-100', 'text-orange-800');
  });

  it('renders lien_filed status with dark red badge', () => {
    render(<InvoiceStatusBadge status="lien_filed" />);
    const badge = screen.getByTestId('invoice-status-lien_filed');
    expect(badge).toHaveTextContent('Lien Filed');
    expect(badge).toHaveClass('bg-red-200', 'text-red-900');
  });

  it('renders cancelled status with gray badge', () => {
    render(<InvoiceStatusBadge status="cancelled" />);
    const badge = screen.getByTestId('invoice-status-cancelled');
    expect(badge).toHaveTextContent('Cancelled');
    expect(badge).toHaveClass('bg-gray-100', 'text-gray-500');
  });

  it('applies custom className', () => {
    render(<InvoiceStatusBadge status="draft" className="custom-class" />);
    const badge = screen.getByTestId('invoice-status-draft');
    expect(badge).toHaveClass('custom-class');
  });
});
