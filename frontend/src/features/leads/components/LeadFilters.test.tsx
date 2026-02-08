import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { LeadFilters } from './LeadFilters';
import type { LeadListParams } from '../types';

describe('LeadFilters', () => {
  let onChange: ReturnType<typeof vi.fn>;
  const defaultParams: LeadListParams = {
    page: 1,
    page_size: 20,
  };

  beforeEach(() => {
    onChange = vi.fn();
  });

  it('renders all filter elements with correct data-testid attributes', () => {
    render(<LeadFilters params={defaultParams} onChange={onChange} />);

    expect(screen.getByTestId('lead-filters')).toBeInTheDocument();
    expect(screen.getByTestId('lead-search-input')).toBeInTheDocument();
    expect(screen.getByTestId('lead-status-filter')).toBeInTheDocument();
    expect(screen.getByTestId('lead-situation-filter')).toBeInTheDocument();
    expect(screen.getByTestId('lead-date-from')).toBeInTheDocument();
    expect(screen.getByTestId('lead-date-to')).toBeInTheDocument();
  });

  it('renders search input with placeholder text', () => {
    render(<LeadFilters params={defaultParams} onChange={onChange} />);

    const searchInput = screen.getByTestId('lead-search-input');
    expect(searchInput).toHaveAttribute(
      'placeholder',
      'Search by name or phone...'
    );
  });

  it('renders status filter with "All Statuses" default', () => {
    render(<LeadFilters params={defaultParams} onChange={onChange} />);

    expect(screen.getByText('All Statuses')).toBeInTheDocument();
  });

  it('renders situation filter with "All Situations" default', () => {
    render(<LeadFilters params={defaultParams} onChange={onChange} />);

    expect(screen.getByText('All Situations')).toBeInTheDocument();
  });

  it('calls onChange with debounced search value', async () => {
    const user = userEvent.setup();
    render(<LeadFilters params={defaultParams} onChange={onChange} />);

    const searchInput = screen.getByTestId('lead-search-input');
    await user.type(searchInput, 'John');

    await waitFor(
      () => {
        expect(onChange).toHaveBeenCalledWith({
          search: 'John',
          page: 1,
        });
      },
      { timeout: 1000 }
    );
  });

  it('calls onChange with undefined search when input is cleared', async () => {
    const user = userEvent.setup();
    render(
      <LeadFilters
        params={{ ...defaultParams, search: 'test' }}
        onChange={onChange}
      />
    );

    const searchInput = screen.getByTestId('lead-search-input');
    await user.clear(searchInput);

    await waitFor(
      () => {
        expect(onChange).toHaveBeenCalledWith({
          search: undefined,
          page: 1,
        });
      },
      { timeout: 1000 }
    );
  });

  it('calls onChange when date_from is set', async () => {
    const user = userEvent.setup();
    render(<LeadFilters params={defaultParams} onChange={onChange} />);

    const dateFrom = screen.getByTestId('lead-date-from');
    await user.type(dateFrom, '2025-01-15');

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ page: 1 })
    );
  });

  it('calls onChange when date_to is set', async () => {
    const user = userEvent.setup();
    render(<LeadFilters params={defaultParams} onChange={onChange} />);

    const dateTo = screen.getByTestId('lead-date-to');
    await user.type(dateTo, '2025-01-31');

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ page: 1 })
    );
  });

  it('displays current filter values from params', () => {
    render(
      <LeadFilters
        params={{
          ...defaultParams,
          date_from: '2025-01-01',
          date_to: '2025-01-31',
        }}
        onChange={onChange}
      />
    );

    const dateFrom = screen.getByTestId('lead-date-from') as HTMLInputElement;
    const dateTo = screen.getByTestId('lead-date-to') as HTMLInputElement;

    expect(dateFrom.value).toBe('2025-01-01');
    expect(dateTo.value).toBe('2025-01-31');
  });

  it('initializes search input from params.search', () => {
    render(
      <LeadFilters
        params={{ ...defaultParams, search: 'existing search' }}
        onChange={onChange}
      />
    );

    const searchInput = screen.getByTestId(
      'lead-search-input'
    ) as HTMLInputElement;
    expect(searchInput.value).toBe('existing search');
  });
});
