import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PollOptionsEditor, type PollOptionsEditorProps } from './PollOptionsEditor';
import type { PollOption } from '../types/campaign';

// Mock date-fns format to avoid locale issues in tests
vi.mock('date-fns', () => ({
  format: (date: Date, fmt: string) => {
    if (fmt === 'yyyy-MM-dd') {
      return date.toISOString().slice(0, 10);
    }
    if (fmt === 'MMM d, yyyy') {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }
    if (fmt === 'MMM d') {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
    return date.toISOString();
  },
}));

function makeOptions(count: number): PollOption[] {
  const keys = ['1', '2', '3', '4', '5'] as const;
  return Array.from({ length: count }, (_, i) => ({
    key: keys[i],
    label: `Option ${keys[i]}`,
    start_date: '2026-04-10',
    end_date: '2026-04-17',
  }));
}

function renderEditor(overrides: Partial<PollOptionsEditorProps> = {}) {
  const defaults: PollOptionsEditorProps = {
    enabled: true,
    onEnabledChange: vi.fn(),
    options: makeOptions(2),
    onOptionsChange: vi.fn(),
  };
  const props = { ...defaults, ...overrides };
  const result = render(<PollOptionsEditor {...props} />);
  return { ...result, props };
}

describe('PollOptionsEditor', () => {
  // --- Toggle ---

  it('renders toggle', () => {
    renderEditor({ enabled: false });
    expect(screen.getByTestId('poll-toggle')).toBeInTheDocument();
  });

  it('does not show option rows when disabled', () => {
    renderEditor({ enabled: false });
    expect(screen.queryByTestId('poll-option-row-1')).not.toBeInTheDocument();
  });

  it('shows option rows when enabled', () => {
    renderEditor();
    expect(screen.getByTestId('poll-option-row-1')).toBeInTheDocument();
    expect(screen.getByTestId('poll-option-row-2')).toBeInTheDocument();
  });

  it('calls onEnabledChange and seeds 2 options when toggled on with empty options', () => {
    const onEnabledChange = vi.fn();
    const onOptionsChange = vi.fn();
    renderEditor({ enabled: false, options: [], onEnabledChange, onOptionsChange });

    fireEvent.click(screen.getByTestId('poll-toggle'));
    expect(onEnabledChange).toHaveBeenCalledWith(true);
    expect(onOptionsChange).toHaveBeenCalledWith([
      { key: '1', label: '', start_date: '', end_date: '' },
      { key: '2', label: '', start_date: '', end_date: '' },
    ]);
  });

  it('does not re-seed options when toggled on with existing options', () => {
    const onOptionsChange = vi.fn();
    renderEditor({ enabled: false, options: makeOptions(3), onOptionsChange });

    fireEvent.click(screen.getByTestId('poll-toggle'));
    expect(onOptionsChange).not.toHaveBeenCalled();
  });

  // --- Add / Remove ---

  it('adds an option when "Add option" clicked', () => {
    const onOptionsChange = vi.fn();
    const options = makeOptions(2);
    renderEditor({ options, onOptionsChange });

    fireEvent.click(screen.getByTestId('poll-add-option-btn'));
    expect(onOptionsChange).toHaveBeenCalledWith([
      ...options,
      { key: '3', label: '', start_date: '', end_date: '' },
    ]);
  });

  it('disables "Add option" at 5 options', () => {
    renderEditor({ options: makeOptions(5) });
    expect(screen.getByTestId('poll-add-option-btn')).toBeDisabled();
  });

  it('does not add beyond 5 options', () => {
    const onOptionsChange = vi.fn();
    renderEditor({ options: makeOptions(5), onOptionsChange });

    fireEvent.click(screen.getByTestId('poll-add-option-btn'));
    expect(onOptionsChange).not.toHaveBeenCalled();
  });

  it('removes an option and re-keys remaining', () => {
    const onOptionsChange = vi.fn();
    const options = makeOptions(3);
    renderEditor({ options, onOptionsChange });

    fireEvent.click(screen.getByTestId('poll-option-remove-2'));
    const call = onOptionsChange.mock.calls[0][0] as PollOption[];
    expect(call).toHaveLength(2);
    expect(call[0].key).toBe('1');
    expect(call[1].key).toBe('2');
  });

  it('disables remove buttons at 2 options (minimum)', () => {
    renderEditor({ options: makeOptions(2) });
    expect(screen.getByTestId('poll-option-remove-1')).toBeDisabled();
    expect(screen.getByTestId('poll-option-remove-2')).toBeDisabled();
  });

  // --- Date validation ---

  it('shows date error when end_date < start_date', () => {
    const options: PollOption[] = [
      { key: '1', label: 'A', start_date: '2026-04-20', end_date: '2026-04-10' },
      { key: '2', label: 'B', start_date: '2026-04-10', end_date: '2026-04-17' },
    ];
    renderEditor({ options });
    expect(screen.getByTestId('poll-date-errors')).toBeInTheDocument();
    expect(screen.getByTestId('poll-date-errors')).toHaveTextContent(
      'Option 1: end date must be on or after start date',
    );
  });

  it('does not show date error when dates are valid', () => {
    renderEditor({ options: makeOptions(2) });
    expect(screen.queryByTestId('poll-date-errors')).not.toBeInTheDocument();
  });

  // --- Live preview ---

  it('renders live preview when enabled with options', () => {
    renderEditor();
    expect(screen.getByTestId('poll-preview')).toBeInTheDocument();
    expect(screen.getByTestId('poll-preview')).toHaveTextContent('Reply with 1, 2');
  });

  it('does not render preview when disabled', () => {
    renderEditor({ enabled: false });
    expect(screen.queryByTestId('poll-preview')).not.toBeInTheDocument();
  });

  // --- Label editing ---

  it('calls onOptionsChange when label is edited', () => {
    const onOptionsChange = vi.fn();
    renderEditor({ onOptionsChange });

    fireEvent.change(screen.getByTestId('poll-option-label-1'), {
      target: { value: 'New label' },
    });
    const call = onOptionsChange.mock.calls[0][0] as PollOption[];
    expect(call[0].label).toBe('New label');
  });
});
