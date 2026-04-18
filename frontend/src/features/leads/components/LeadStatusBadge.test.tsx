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
    contacted: 'Contacted (Awaiting Response)',
    qualified: 'Archived',
    converted: 'Archived',
    lost: 'Archived',
    spam: 'Archived',
  };

  const expectedColorClasses: Record<LeadStatus, string[]> = {
    new: ['bg-blue-100', 'text-blue-800'],
    contacted: ['bg-yellow-100', 'text-yellow-800'],
    qualified: ['bg-gray-100', 'text-gray-600'],
    converted: ['bg-gray-100', 'text-gray-600'],
    lost: ['bg-gray-100', 'text-gray-600'],
    spam: ['bg-gray-100', 'text-gray-600'],
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
