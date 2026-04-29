import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ResourceSuggestionsList } from './ResourceSuggestionsList';
import type { ResourceSuggestion } from '../types';

const suggestions: ResourceSuggestion[] = [
  {
    id: 's1',
    type: 'prejob_prep',
    title: 'Bring extra backflow fittings',
    description: 'Customer had fitting issues last visit.',
    job_id: 'j1',
    action_label: 'View history',
    created_at: new Date().toISOString(),
  },
  {
    id: 's2',
    type: 'upsell_opportunity',
    title: 'Controller upgrade opportunity',
    description: 'Controller is 8 years old — recommend upgrade.',
    job_id: 'j2',
    action_label: 'Initiate quote',
    created_at: new Date().toISOString(),
  },
  {
    id: 's3',
    type: 'parts_low',
    title: 'Backflow fittings running low',
    description: 'Only 2 left. Supply house is 5 min away.',
    job_id: null,
    action_label: 'Navigate to supply house',
    created_at: new Date().toISOString(),
  },
];

describe('ResourceSuggestionsList', () => {
  it('renders with data-testid="resource-suggestions-list"', () => {
    render(<ResourceSuggestionsList suggestions={suggestions} onAccept={vi.fn()} />);
    expect(screen.getByTestId('resource-suggestions-list')).toBeInTheDocument();
  });

  it('renders suggestion items with correct data-testid', () => {
    render(<ResourceSuggestionsList suggestions={suggestions} onAccept={vi.fn()} />);
    expect(screen.getByTestId('resource-suggestion-s1')).toBeInTheDocument();
    expect(screen.getByTestId('resource-suggestion-s2')).toBeInTheDocument();
    expect(screen.getByTestId('resource-suggestion-s3')).toBeInTheDocument();
  });

  it('shows suggestion titles and descriptions', () => {
    render(<ResourceSuggestionsList suggestions={suggestions} onAccept={vi.fn()} />);
    expect(screen.getByText('Bring extra backflow fittings')).toBeInTheDocument();
    expect(screen.getByText('Customer had fitting issues last visit.')).toBeInTheDocument();
  });

  it('shows correct label for prejob_prep type', () => {
    render(<ResourceSuggestionsList suggestions={[suggestions[0]]} onAccept={vi.fn()} />);
    expect(screen.getByText('Pre-Job Prep')).toBeInTheDocument();
  });

  it('shows correct label for upsell_opportunity type', () => {
    render(<ResourceSuggestionsList suggestions={[suggestions[1]]} onAccept={vi.fn()} />);
    expect(screen.getByText('Upsell Opportunity')).toBeInTheDocument();
  });

  it('shows correct label for parts_low type', () => {
    render(<ResourceSuggestionsList suggestions={[suggestions[2]]} onAccept={vi.fn()} />);
    expect(screen.getByText('Parts Low')).toBeInTheDocument();
  });

  it('shows action label buttons', () => {
    render(<ResourceSuggestionsList suggestions={suggestions} onAccept={vi.fn()} />);
    expect(screen.getByText('View history →')).toBeInTheDocument();
    expect(screen.getByText('Initiate quote →')).toBeInTheDocument();
    expect(screen.getByText('Navigate to supply house →')).toBeInTheDocument();
  });

  it('calls onAccept with suggestion id when action button clicked', () => {
    const onAccept = vi.fn();
    render(<ResourceSuggestionsList suggestions={suggestions} onAccept={onAccept} />);
    fireEvent.click(screen.getByText('View history →'));
    expect(onAccept).toHaveBeenCalledWith('s1');
  });

  it('shows empty state when no suggestions', () => {
    render(<ResourceSuggestionsList suggestions={[]} onAccept={vi.fn()} />);
    expect(screen.getByText('No suggestions.')).toBeInTheDocument();
  });
});
