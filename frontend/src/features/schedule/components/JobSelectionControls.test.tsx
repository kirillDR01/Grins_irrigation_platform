import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { JobSelectionControls } from './JobSelectionControls';

describe('JobSelectionControls', () => {
  const mockJobIds = ['job-1', 'job-2', 'job-3'];
  const mockOnSelectAll = vi.fn();
  const mockOnDeselectAll = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Select All link', () => {
    render(
      <JobSelectionControls
        jobIds={mockJobIds}
        excludedJobIds={new Set()}
        onSelectAll={mockOnSelectAll}
        onDeselectAll={mockOnDeselectAll}
      />
    );

    expect(screen.getByTestId('select-all-btn')).toBeInTheDocument();
    // Check for the label text (there are multiple "Select All" elements)
    expect(screen.getAllByText('Select All').length).toBeGreaterThan(0);
  });

  it('renders Deselect All link', () => {
    render(
      <JobSelectionControls
        jobIds={mockJobIds}
        excludedJobIds={new Set()}
        onSelectAll={mockOnSelectAll}
        onDeselectAll={mockOnDeselectAll}
      />
    );

    expect(screen.getByTestId('deselect-all-btn')).toBeInTheDocument();
    expect(screen.getByText('Deselect All')).toBeInTheDocument();
  });

  it('calls onSelectAll when Select All is clicked', () => {
    render(
      <JobSelectionControls
        jobIds={mockJobIds}
        excludedJobIds={new Set(['job-1'])}
        onSelectAll={mockOnSelectAll}
        onDeselectAll={mockOnDeselectAll}
      />
    );

    fireEvent.click(screen.getByTestId('select-all-btn'));
    expect(mockOnSelectAll).toHaveBeenCalledTimes(1);
  });

  it('calls onDeselectAll when Deselect All is clicked', () => {
    render(
      <JobSelectionControls
        jobIds={mockJobIds}
        excludedJobIds={new Set()}
        onSelectAll={mockOnSelectAll}
        onDeselectAll={mockOnDeselectAll}
      />
    );

    fireEvent.click(screen.getByTestId('deselect-all-btn'));
    expect(mockOnDeselectAll).toHaveBeenCalledTimes(1);
  });

  it('displays correct selection count', () => {
    render(
      <JobSelectionControls
        jobIds={mockJobIds}
        excludedJobIds={new Set(['job-1'])}
        onSelectAll={mockOnSelectAll}
        onDeselectAll={mockOnDeselectAll}
      />
    );

    expect(screen.getByText('2 of 3 jobs selected')).toBeInTheDocument();
  });

  it('returns null when no jobs', () => {
    const { container } = render(
      <JobSelectionControls
        jobIds={[]}
        excludedJobIds={new Set()}
        onSelectAll={mockOnSelectAll}
        onDeselectAll={mockOnDeselectAll}
      />
    );

    expect(container.firstChild).toBeNull();
  });

  it('has correct data-testid attributes', () => {
    render(
      <JobSelectionControls
        jobIds={mockJobIds}
        excludedJobIds={new Set()}
        onSelectAll={mockOnSelectAll}
        onDeselectAll={mockOnDeselectAll}
      />
    );

    expect(screen.getByTestId('job-selection-controls')).toBeInTheDocument();
    expect(screen.getByTestId('select-all-btn')).toBeInTheDocument();
    expect(screen.getByTestId('deselect-all-btn')).toBeInTheDocument();
  });

  it('renders select all checkbox', () => {
    render(
      <JobSelectionControls
        jobIds={mockJobIds}
        excludedJobIds={new Set()}
        onSelectAll={mockOnSelectAll}
        onDeselectAll={mockOnDeselectAll}
      />
    );

    expect(screen.getByTestId('select-all-checkbox')).toBeInTheDocument();
  });

  it('shows clear selection button when items are selected', () => {
    render(
      <JobSelectionControls
        jobIds={mockJobIds}
        excludedJobIds={new Set()}
        onSelectAll={mockOnSelectAll}
        onDeselectAll={mockOnDeselectAll}
      />
    );

    expect(screen.getByTestId('clear-selection-btn')).toBeInTheDocument();
  });

  it('calls onDeselectAll when clear selection is clicked', () => {
    render(
      <JobSelectionControls
        jobIds={mockJobIds}
        excludedJobIds={new Set()}
        onSelectAll={mockOnSelectAll}
        onDeselectAll={mockOnDeselectAll}
      />
    );

    fireEvent.click(screen.getByTestId('clear-selection-btn'));
    expect(mockOnDeselectAll).toHaveBeenCalledTimes(1);
  });
});
