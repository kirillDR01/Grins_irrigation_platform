import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { FacetRail } from './FacetRail';
import type { JobReadyToSchedule } from '../types/index';
import type { FacetState } from '../types/pick-jobs';
import { initialFacets } from '../types/pick-jobs';

// Mock Sheet to avoid duplicate rendering complexity in tests
vi.mock('@/components/ui/sheet', () => ({
  Sheet: () => null,
  SheetContent: () => null,
  SheetHeader: () => null,
  SheetTitle: () => null,
  SheetTrigger: () => null,
}));

const mockJobs: JobReadyToSchedule[] = [
  {
    job_id: '1',
    customer_id: 'c1',
    customer_name: 'John Doe',
    city: 'Minneapolis',
    job_type: 'Spring Startup',
    estimated_duration_minutes: 60,
    customer_tags: ['priority', 'new_customer'],
    priority_level: 2,
    requested_week: '2024-04-15',
    notes: '',
  },
  {
    job_id: '2',
    customer_id: 'c2',
    customer_name: 'Jane Smith',
    city: 'St. Paul',
    job_type: 'Repair',
    estimated_duration_minutes: 90,
    customer_tags: ['red_flag'],
    priority_level: 1,
    requested_week: '2024-04-22',
    notes: '',
  },
];

describe('FacetRail', () => {
  const mockOnChange = vi.fn();
  const mockOnClearAll = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all five facet groups', () => {
    render(
      <FacetRail
        jobs={mockJobs}
        facets={initialFacets}
        onChange={mockOnChange}
        onClearAll={mockOnClearAll}
      />
    );

    expect(screen.getByTestId('facet-group-city')).toBeInTheDocument();
    expect(screen.getByTestId('facet-group-tags')).toBeInTheDocument();
    expect(screen.getByTestId('facet-group-job-type')).toBeInTheDocument();
    expect(screen.getByTestId('facet-group-priority')).toBeInTheDocument();
    expect(screen.getByTestId('facet-group-week')).toBeInTheDocument();
  });

  it('renders correct facet values', () => {
    render(
      <FacetRail
        jobs={mockJobs}
        facets={initialFacets}
        onChange={mockOnChange}
        onClearAll={mockOnClearAll}
      />
    );

    expect(screen.getByTestId('facet-value-city-Minneapolis')).toBeInTheDocument();
    expect(screen.getByTestId('facet-value-city-St. Paul')).toBeInTheDocument();
    expect(screen.getByTestId('facet-value-tags-priority')).toBeInTheDocument();
    expect(screen.getByTestId('facet-value-jobType-Spring Startup')).toBeInTheDocument();
  });

  it('toggles facet checkbox and calls onChange', () => {
    render(
      <FacetRail
        jobs={mockJobs}
        facets={initialFacets}
        onChange={mockOnChange}
        onClearAll={mockOnClearAll}
      />
    );

    const minneapolisCheckbox = screen.getByTestId('facet-value-city-Minneapolis').querySelector('button');
    fireEvent.click(minneapolisCheckbox!);

    expect(mockOnChange).toHaveBeenCalledTimes(1);
    const updatedFacets = mockOnChange.mock.calls[0][0] as FacetState;
    expect(updatedFacets.city.has('Minneapolis')).toBe(true);
  });

  it('shows Clear button when group has selections', () => {
    const facetsWithSelection: FacetState = {
      ...initialFacets,
      city: new Set(['Minneapolis']),
    };

    render(
      <FacetRail
        jobs={mockJobs}
        facets={facetsWithSelection}
        onChange={mockOnChange}
        onClearAll={mockOnClearAll}
      />
    );

    const cityGroup = screen.getByTestId('facet-group-city');
    expect(within(cityGroup).getByText('Clear')).toBeInTheDocument();
  });

  it('shows Clear all filters link when any facet is active', () => {
    const facetsWithSelection: FacetState = {
      ...initialFacets,
      city: new Set(['Minneapolis']),
    };

    render(
      <FacetRail
        jobs={mockJobs}
        facets={facetsWithSelection}
        onChange={mockOnChange}
        onClearAll={mockOnClearAll}
      />
    );

    expect(screen.getByText('Clear all filters')).toBeInTheDocument();
  });

  it('clicking Clear all filters calls onClearAll', () => {
    const facetsWithSelection: FacetState = {
      ...initialFacets,
      city: new Set(['Minneapolis']),
    };

    render(
      <FacetRail
        jobs={mockJobs}
        facets={facetsWithSelection}
        onChange={mockOnChange}
        onClearAll={mockOnClearAll}
      />
    );

    fireEvent.click(screen.getByText('Clear all filters'));
    expect(mockOnClearAll).toHaveBeenCalledTimes(1);
  });

  it('displays human-readable priority labels', () => {
    render(
      <FacetRail
        jobs={mockJobs}
        facets={initialFacets}
        onChange={mockOnChange}
        onClearAll={mockOnClearAll}
      />
    );

    expect(screen.getByText('High')).toBeInTheDocument();
    expect(screen.getByText('Urgent')).toBeInTheDocument();
  });

  it('handles empty jobs array', () => {
    render(
      <FacetRail
        jobs={[]}
        facets={initialFacets}
        onChange={mockOnChange}
        onClearAll={mockOnClearAll}
      />
    );

    expect(screen.getByTestId('facet-rail')).toBeInTheDocument();
    expect(screen.queryByTestId('facet-group-city')).not.toBeInTheDocument();
  });
});
