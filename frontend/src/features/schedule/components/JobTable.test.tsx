import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { JobTable } from './JobTable';
import type { JobReadyToSchedule } from '../types/index';

// Mock PropertyTags to avoid complex rendering
vi.mock('@/shared/components/PropertyTags', () => ({
  PropertyTags: () => null,
}));

const makeJob = (overrides: Partial<JobReadyToSchedule> = {}): JobReadyToSchedule => ({
  job_id: 'job-1',
  customer_id: 'cust-1',
  customer_name: 'Alice Smith',
  city: 'Minneapolis',
  job_type: 'Spring Startup',
  estimated_duration_minutes: 60,
  customer_tags: [],
  priority_level: 0,
  requested_week: '2024-04-15',
  notes: '',
  ...overrides,
});

const defaultProps = {
  jobs: [] as JobReadyToSchedule[],
  searchRef: { current: null } as React.RefObject<HTMLInputElement>,
  search: '',
  onSearchChange: vi.fn(),
  selectedJobIds: new Set<string>(),
  onToggleJob: vi.fn(),
  onToggleAllVisible: vi.fn(),
  sortKey: 'priority' as const,
  sortDir: 'desc' as const,
  onSort: vi.fn(),
  anyFilterActive: false,
  onClearAllFilters: vi.fn(),
};

function renderTable(props = {}) {
  return render(
    <BrowserRouter>
      <JobTable {...defaultProps} {...props} />
    </BrowserRouter>
  );
}

describe('JobTable', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ─── Rendering ───────────────────────────────────────────────────────────

  it('renders the table container', () => {
    renderTable();
    expect(screen.getByTestId('job-table')).toBeInTheDocument();
  });

  it('renders rows for each job', () => {
    const jobs = [makeJob({ job_id: 'j1' }), makeJob({ job_id: 'j2', customer_name: 'Bob Jones' })];
    renderTable({ jobs });
    expect(screen.getByTestId('job-row-j1')).toBeInTheDocument();
    expect(screen.getByTestId('job-row-j2')).toBeInTheDocument();
  });

  it('renders columns in correct order: customer, job type, tags, city, requested, priority, duration, equipment', () => {
    const jobs = [makeJob({ job_id: 'j1', estimated_duration_minutes: 45, requires_equipment: ['Backflow kit'] })];
    renderTable({ jobs });
    const row = screen.getByTestId('job-row-j1');
    const cells = within(row).getAllByRole('cell');
    // checkbox, customer, job type, tags, city, requested, priority, duration, equipment
    expect(cells).toHaveLength(9);
    expect(cells[1]).toHaveTextContent('Alice Smith');
    expect(cells[2]).toHaveTextContent('Spring Startup');
    expect(cells[4]).toHaveTextContent('Minneapolis');
    expect(cells[7]).toHaveTextContent('45m');
    expect(cells[8]).toHaveTextContent('Backflow kit');
  });

  // ─── Selection ───────────────────────────────────────────────────────────

  it('row click calls onToggleJob with job id', () => {
    const onToggleJob = vi.fn();
    const jobs = [makeJob({ job_id: 'j1' })];
    renderTable({ jobs, onToggleJob });
    fireEvent.click(screen.getByTestId('job-row-j1'));
    expect(onToggleJob).toHaveBeenCalledWith('j1');
  });

  it('selected row has teal background class', () => {
    const jobs = [makeJob({ job_id: 'j1' })];
    renderTable({ jobs, selectedJobIds: new Set(['j1']) });
    expect(screen.getByTestId('job-row-j1').className).toContain('bg-teal-50');
  });

  it('unselected row does not have teal background', () => {
    const jobs = [makeJob({ job_id: 'j1' })];
    renderTable({ jobs, selectedJobIds: new Set() });
    expect(screen.getByTestId('job-row-j1').className).not.toContain('bg-teal-50');
  });

  it('row checkbox calls onToggleJob', () => {
    const onToggleJob = vi.fn();
    const jobs = [makeJob({ job_id: 'j1' })];
    renderTable({ jobs, onToggleJob });
    const checkbox = screen.getByTestId('job-row-checkbox-j1');
    fireEvent.click(checkbox);
    expect(onToggleJob).toHaveBeenCalledWith('j1');
  });

  // ─── Tri-state header checkbox ────────────────────────────────────────────

  it('header checkbox is unchecked when no jobs selected', () => {
    const jobs = [makeJob({ job_id: 'j1' }), makeJob({ job_id: 'j2' })];
    renderTable({ jobs, selectedJobIds: new Set() });
    const selectAll = screen.getByTestId('job-table-select-all');
    expect(selectAll).toHaveAttribute('aria-checked', 'false');
  });

  it('header checkbox is checked when all visible jobs selected', () => {
    const jobs = [makeJob({ job_id: 'j1' }), makeJob({ job_id: 'j2' })];
    renderTable({ jobs, selectedJobIds: new Set(['j1', 'j2']) });
    const selectAll = screen.getByTestId('job-table-select-all');
    expect(selectAll).toHaveAttribute('aria-checked', 'true');
  });

  it('header checkbox is indeterminate when some visible jobs selected', () => {
    const jobs = [makeJob({ job_id: 'j1' }), makeJob({ job_id: 'j2' })];
    renderTable({ jobs, selectedJobIds: new Set(['j1']) });
    const selectAll = screen.getByTestId('job-table-select-all');
    expect(selectAll).toHaveAttribute('aria-checked', 'mixed');
  });

  it('header checkbox click calls onToggleAllVisible', () => {
    const onToggleAllVisible = vi.fn();
    const jobs = [makeJob({ job_id: 'j1' })];
    renderTable({ jobs, onToggleAllVisible });
    fireEvent.click(screen.getByTestId('job-table-select-all'));
    expect(onToggleAllVisible).toHaveBeenCalledTimes(1);
  });

  it('header checkbox has aria-label "Select all visible jobs"', () => {
    const jobs = [makeJob({ job_id: 'j1' })];
    renderTable({ jobs });
    expect(screen.getByTestId('job-table-select-all')).toHaveAttribute('aria-label', 'Select all visible jobs');
  });

  // ─── Inline notes row ────────────────────────────────────────────────────

  it('renders inline notes row for jobs with notes', () => {
    const jobs = [makeJob({ job_id: 'j1', notes: 'Gate code is 1234' })];
    renderTable({ jobs });
    expect(screen.getByText('Gate code is 1234')).toBeInTheDocument();
  });

  it('does not render notes row for jobs without notes', () => {
    const jobs = [makeJob({ job_id: 'j1', notes: '' })];
    renderTable({ jobs });
    // Only one row for the job itself
    expect(screen.getAllByRole('row')).toHaveLength(2); // header + 1 job row
  });

  // ─── Tag pills ───────────────────────────────────────────────────────────

  it('renders customer tag pills using CUSTOMER_TAG_CONFIG labels', () => {
    const jobs = [makeJob({ job_id: 'j1', customer_tags: ['priority'] })];
    renderTable({ jobs });
    // CUSTOMER_TAG_CONFIG['priority'].label should be rendered in the tags cell
    const row = screen.getByTestId('job-row-j1');
    const cells = within(row).getAllByRole('cell');
    // Tags cell is index 3
    expect(within(cells[3]).getByText('Priority')).toBeInTheDocument();
  });

  it('renders red_flag tag pill', () => {
    const jobs = [makeJob({ job_id: 'j1', customer_tags: ['red_flag'] })];
    renderTable({ jobs });
    expect(screen.getByText('Red Flag')).toBeInTheDocument();
  });

  // ─── Priority column ─────────────────────────────────────────────────────

  it('renders star icon for priority_level 1', () => {
    const jobs = [makeJob({ job_id: 'j1', priority_level: 1 })];
    renderTable({ jobs });
    const row = screen.getByTestId('job-row-j1');
    const cells = within(row).getAllByRole('cell');
    // Priority cell is index 6 — should contain an SVG star (lucide-star class)
    expect(cells[6].querySelector('svg.lucide-star')).toBeTruthy();
  });

  it('renders em-dash for priority_level 0', () => {
    const jobs = [makeJob({ job_id: 'j1', priority_level: 0 })];
    renderTable({ jobs });
    const row = screen.getByTestId('job-row-j1');
    const cells = within(row).getAllByRole('cell');
    // Priority cell is index 6 — should contain the em-dash span
    expect(within(cells[6]).getByText('—')).toBeInTheDocument();
  });

  // ─── Sort headers ────────────────────────────────────────────────────────

  it('clicking Customer header calls onSort with customer/asc when not active', () => {
    const onSort = vi.fn();
    const jobs = [makeJob({ job_id: 'j1' })];
    renderTable({ jobs, onSort, sortKey: 'priority', sortDir: 'desc' });
    fireEvent.click(screen.getByRole('button', { name: /customer/i }));
    expect(onSort).toHaveBeenCalledWith('customer', 'asc');
  });

  it('clicking active asc column calls onSort with desc', () => {
    const onSort = vi.fn();
    const jobs = [makeJob({ job_id: 'j1' })];
    renderTable({ jobs, onSort, sortKey: 'customer', sortDir: 'asc' });
    fireEvent.click(screen.getByRole('button', { name: /customer/i }));
    expect(onSort).toHaveBeenCalledWith('customer', 'desc');
  });

  it('clicking active desc column reverts to default sort (priority desc)', () => {
    const onSort = vi.fn();
    const jobs = [makeJob({ job_id: 'j1' })];
    renderTable({ jobs, onSort, sortKey: 'customer', sortDir: 'desc' });
    fireEvent.click(screen.getByRole('button', { name: /customer/i }));
    expect(onSort).toHaveBeenCalledWith('priority', 'desc');
  });

  it('active sort column has aria-sort="ascending"', () => {
    const jobs = [makeJob({ job_id: 'j1' })];
    renderTable({ jobs, sortKey: 'customer', sortDir: 'asc' });
    const th = screen.getByRole('columnheader', { name: /customer/i });
    expect(th).toHaveAttribute('aria-sort', 'ascending');
  });

  it('active sort column has aria-sort="descending"', () => {
    const jobs = [makeJob({ job_id: 'j1' })];
    renderTable({ jobs, sortKey: 'customer', sortDir: 'desc' });
    const th = screen.getByRole('columnheader', { name: /customer/i });
    expect(th).toHaveAttribute('aria-sort', 'descending');
  });

  it('inactive sort column has aria-sort="none"', () => {
    const jobs = [makeJob({ job_id: 'j1' })];
    renderTable({ jobs, sortKey: 'priority', sortDir: 'desc' });
    const th = screen.getByRole('columnheader', { name: /customer/i });
    expect(th).toHaveAttribute('aria-sort', 'none');
  });

  // ─── Empty states ────────────────────────────────────────────────────────

  it('shows "All jobs are scheduled" when no jobs and no filters active', () => {
    renderTable({ jobs: [], anyFilterActive: false });
    expect(screen.getByText(/All jobs are scheduled/i)).toBeInTheDocument();
  });

  it('shows "No jobs match these filters" when no jobs and filters active', () => {
    renderTable({ jobs: [], anyFilterActive: true });
    expect(screen.getByText(/No jobs match these filters/i)).toBeInTheDocument();
  });

  it('shows "Clear all filters" button in filter-active empty state', () => {
    renderTable({ jobs: [], anyFilterActive: true });
    expect(screen.getByRole('button', { name: /clear all filters/i })).toBeInTheDocument();
  });

  it('"Clear all filters" button calls onClearAllFilters', () => {
    const onClearAllFilters = vi.fn();
    renderTable({ jobs: [], anyFilterActive: true, onClearAllFilters });
    fireEvent.click(screen.getByRole('button', { name: /clear all filters/i }));
    expect(onClearAllFilters).toHaveBeenCalledTimes(1);
  });

  // ─── Search toolbar ───────────────────────────────────────────────────────

  it('renders search input with correct placeholder', () => {
    renderTable();
    expect(screen.getByTestId('job-search')).toHaveAttribute(
      'placeholder',
      'Search customer, address, phone, job type…'
    );
  });

  it('search input calls onSearchChange on change', async () => {
    const onSearchChange = vi.fn();
    const user = userEvent.setup();
    renderTable({ onSearchChange });
    await user.type(screen.getByTestId('job-search'), 'Alice');
    expect(onSearchChange).toHaveBeenCalled();
  });

  it('pressing Escape on search input calls onSearchChange with empty string', () => {
    const onSearchChange = vi.fn();
    renderTable({ search: 'Alice', onSearchChange });
    fireEvent.keyDown(screen.getByTestId('job-search'), { key: 'Escape' });
    expect(onSearchChange).toHaveBeenCalledWith('');
  });

  it('displays job count next to search', () => {
    const jobs = [makeJob({ job_id: 'j1' }), makeJob({ job_id: 'j2' })];
    renderTable({ jobs });
    expect(screen.getByText('2 jobs')).toBeInTheDocument();
  });

  it('displays singular "job" for single result', () => {
    const jobs = [makeJob({ job_id: 'j1' })];
    renderTable({ jobs });
    expect(screen.getByText('1 job')).toBeInTheDocument();
  });
});
