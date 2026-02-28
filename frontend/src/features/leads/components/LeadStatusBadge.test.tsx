import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LeadStatusBadge } from './LeadStatusBadge';
import type { LeadStatus } from '../types';

describe('LeadStatusBadge', () => {
  const allStatuses: LeadStatus[] = [
    'new',
    'contacted',
    'qualified',
    'converted',
    'lost',
    'spam',
  ];

  const expectedLabels: Record<LeadStatus, string> = {
    new: 'New',
    contacted: 'Contacted',
    qualified: 'Qualified',
    converted: 'Converted',
    lost: 'Lost',
    spam: 'Spam',
  };

  const expectedColorClasses: Record<LeadStatus, string[]> = {
    new: ['bg-blue-100', 'text-blue-800'],
    contacted: ['bg-yellow-100', 'text-yellow-800'],
    qualified: ['bg-purple-100', 'text-purple-800'],
    converted: ['bg-green-100', 'text-green-800'],
    lost: ['bg-gray-100', 'text-gray-800'],
    spam: ['bg-red-100', 'text-red-800'],
  };

  describe('rendering', () => {
    it.each(allStatuses)('renders %s status with correct label', (status) => {
      render(<LeadStatusBadge status={status} />);

      const badge = screen.getByTestId('lead-status-badge');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveTextContent(expectedLabels[status]);
    });

    it.each(allStatuses)('renders %s status with correct color classes', (status) => {
      render(<LeadStatusBadge status={status} />);

      const badge = screen.getByTestId('lead-status-badge');
      for (const cls of expectedColorClasses[status]) {
        expect(badge.className).toContain(cls);
      }
    });
  });

  describe('data-testid', () => {
    it('uses default data-testid', () => {
      render(<LeadStatusBadge status="new" />);
      expect(screen.getByTestId('lead-status-badge')).toBeInTheDocument();
    });

    it('accepts custom data-testid', () => {
      render(<LeadStatusBadge status="new" data-testid="custom-badge" />);
      expect(screen.getByTestId('custom-badge')).toBeInTheDocument();
    });
  });

  describe('className', () => {
    it('applies custom className', () => {
      render(<LeadStatusBadge status="new" className="custom-class" />);

      const badge = screen.getByTestId('lead-status-badge');
      expect(badge).toHaveClass('custom-class');
    });
  });
});
