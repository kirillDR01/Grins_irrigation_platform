import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LeadSituationBadge } from './LeadSituationBadge';
import type { LeadSituation } from '../types';

describe('LeadSituationBadge', () => {
  const allSituations: LeadSituation[] = [
    'new_system',
    'upgrade',
    'repair',
    'exploring',
  ];

  const expectedLabels: Record<LeadSituation, string> = {
    new_system: 'New System',
    upgrade: 'Upgrade',
    repair: 'Repair',
    exploring: 'Exploring',
  };

  describe('rendering', () => {
    it.each(allSituations)('renders %s situation with correct label', (situation) => {
      render(<LeadSituationBadge situation={situation} />);

      const badge = screen.getByTestId('lead-situation-badge');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveTextContent(expectedLabels[situation]);
    });

    it.each(allSituations)('renders %s situation with styling', (situation) => {
      render(<LeadSituationBadge situation={situation} />);

      const badge = screen.getByTestId('lead-situation-badge');
      // All badges should have the base badge classes
      expect(badge.className).toContain('inline-flex');
      expect(badge.className).toContain('rounded-full');
      expect(badge.className).toContain('text-xs');
      expect(badge.className).toContain('font-medium');
    });
  });

  describe('data-testid', () => {
    it('uses default data-testid', () => {
      render(<LeadSituationBadge situation="new_system" />);
      expect(screen.getByTestId('lead-situation-badge')).toBeInTheDocument();
    });

    it('accepts custom data-testid', () => {
      render(<LeadSituationBadge situation="repair" data-testid="custom-badge" />);
      expect(screen.getByTestId('custom-badge')).toBeInTheDocument();
    });
  });

  describe('className', () => {
    it('applies custom className', () => {
      render(<LeadSituationBadge situation="upgrade" className="custom-class" />);

      const badge = screen.getByTestId('lead-situation-badge');
      expect(badge).toHaveClass('custom-class');
    });
  });
});
