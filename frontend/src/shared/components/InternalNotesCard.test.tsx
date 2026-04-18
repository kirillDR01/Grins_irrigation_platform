/**
 * Tests for InternalNotesCard component.
 *
 * Validates: internal-notes-simplification Requirement 7
 * - Collapsed renders value or placeholder
 * - Edit button flips to expanded with draft prefilled
 * - Cancel returns to collapsed and discards changes
 * - Save invokes onSave with the typed string (or null when empty)
 * - isSaving=true disables button and shows "Saving..."
 * - readOnly=true hides the Edit button
 * - data-testid-prefix threads through to interactive elements
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { InternalNotesCard } from './InternalNotesCard';

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock getErrorMessage
vi.mock('@/core/api', () => ({
  getErrorMessage: vi.fn((err: unknown) =>
    err instanceof Error ? err.message : 'Unknown error'
  ),
}));

describe('InternalNotesCard', () => {
  const mockOnSave = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockOnSave.mockReset();
  });

  // ── Collapsed state ──

  it('renders value in collapsed state', () => {
    render(
      <InternalNotesCard
        value="Some notes here"
        onSave={mockOnSave}
        isSaving={false}
      />
    );

    expect(screen.getByText('Some notes here')).toBeInTheDocument();
    expect(screen.getByText('Internal Notes')).toBeInTheDocument();
  });

  it('renders placeholder when value is null', () => {
    render(
      <InternalNotesCard
        value={null}
        onSave={mockOnSave}
        isSaving={false}
      />
    );

    expect(screen.getByText('No internal notes')).toBeInTheDocument();
  });

  it('renders custom placeholder when value is null', () => {
    render(
      <InternalNotesCard
        value={null}
        onSave={mockOnSave}
        isSaving={false}
        placeholder="Nothing here yet"
      />
    );

    expect(screen.getByText('Nothing here yet')).toBeInTheDocument();
  });

  it('renders placeholder when value is empty string', () => {
    render(
      <InternalNotesCard
        value=""
        onSave={mockOnSave}
        isSaving={false}
      />
    );

    expect(screen.getByText('No internal notes')).toBeInTheDocument();
  });

  // ── Edit button → expanded ──

  it('Edit button flips to expanded with draft prefilled', async () => {
    const user = userEvent.setup();

    render(
      <InternalNotesCard
        value="Existing notes"
        onSave={mockOnSave}
        isSaving={false}
      />
    );

    // Click Edit
    await user.click(screen.getByText('Edit'));

    // Textarea should appear with the current value
    const textarea = screen.getByRole('textbox');
    expect(textarea).toBeInTheDocument();
    expect(textarea).toHaveValue('Existing notes');

    // Save Notes and Cancel buttons should be visible
    expect(screen.getByText('Save Notes')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();

    // Edit button should be gone
    expect(screen.queryByText('Edit')).not.toBeInTheDocument();
  });

  it('Edit button prefills empty string when value is null', async () => {
    const user = userEvent.setup();

    render(
      <InternalNotesCard
        value={null}
        onSave={mockOnSave}
        isSaving={false}
      />
    );

    await user.click(screen.getByText('Edit'));

    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveValue('');
  });

  // ── Cancel ──

  it('Cancel returns to collapsed and discards changes', async () => {
    const user = userEvent.setup();

    render(
      <InternalNotesCard
        value="Original notes"
        onSave={mockOnSave}
        isSaving={false}
      />
    );

    // Enter edit mode
    await user.click(screen.getByText('Edit'));

    // Type something different
    const textarea = screen.getByRole('textbox');
    await user.clear(textarea);
    await user.type(textarea, 'Modified notes');

    // Click Cancel
    await user.click(screen.getByText('Cancel'));

    // Should be back in collapsed state with original value
    expect(screen.getByText('Original notes')).toBeInTheDocument();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    expect(screen.getByText('Edit')).toBeInTheDocument();
  });

  // ── Save ──

  it('Save invokes onSave with the typed string', async () => {
    const user = userEvent.setup();
    mockOnSave.mockResolvedValue(undefined);

    render(
      <InternalNotesCard
        value=""
        onSave={mockOnSave}
        isSaving={false}
      />
    );

    await user.click(screen.getByText('Edit'));

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'New notes content');

    await user.click(screen.getByText('Save Notes'));

    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalledWith('New notes content');
    });
  });

  it('Save normalizes empty/whitespace draft to null', async () => {
    const user = userEvent.setup();
    mockOnSave.mockResolvedValue(undefined);

    render(
      <InternalNotesCard
        value="Some notes"
        onSave={mockOnSave}
        isSaving={false}
      />
    );

    await user.click(screen.getByText('Edit'));

    const textarea = screen.getByRole('textbox');
    await user.clear(textarea);
    await user.type(textarea, '   ');

    await user.click(screen.getByText('Save Notes'));

    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalledWith(null);
    });
  });

  it('Save returns to collapsed state on success', async () => {
    const user = userEvent.setup();
    mockOnSave.mockResolvedValue(undefined);
    const { toast } = await import('sonner');

    render(
      <InternalNotesCard
        value="Notes"
        onSave={mockOnSave}
        isSaving={false}
      />
    );

    await user.click(screen.getByText('Edit'));
    await user.click(screen.getByText('Save Notes'));

    await waitFor(() => {
      expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    });

    expect(toast.success).toHaveBeenCalledWith('Notes saved');
  });

  it('Save keeps expanded state on failure and shows error toast', async () => {
    const user = userEvent.setup();
    mockOnSave.mockRejectedValue(new Error('Server error'));
    const { toast } = await import('sonner');

    render(
      <InternalNotesCard
        value="Notes"
        onSave={mockOnSave}
        isSaving={false}
      />
    );

    await user.click(screen.getByText('Edit'));

    const textarea = screen.getByRole('textbox');
    await user.clear(textarea);
    await user.type(textarea, 'Updated notes');

    await user.click(screen.getByText('Save Notes'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to save notes', {
        description: 'Server error',
      });
    });

    // Should still be in expanded state with the user's typed value
    expect(screen.getByRole('textbox')).toHaveValue('Updated notes');
  });

  // ── isSaving ──

  it('isSaving=true disables Save button and shows "Saving..."', async () => {
    const user = userEvent.setup();

    const { rerender } = render(
      <InternalNotesCard
        value="Notes"
        onSave={mockOnSave}
        isSaving={false}
      />
    );

    await user.click(screen.getByText('Edit'));

    // Re-render with isSaving=true
    rerender(
      <InternalNotesCard
        value="Notes"
        onSave={mockOnSave}
        isSaving={true}
      />
    );

    const saveBtn = screen.getByText('Saving...');
    expect(saveBtn.closest('button')).toBeDisabled();
  });

  // ── readOnly ──

  it('readOnly=true hides the Edit button', () => {
    render(
      <InternalNotesCard
        value="Some notes"
        onSave={mockOnSave}
        isSaving={false}
        readOnly
      />
    );

    expect(screen.queryByText('Edit')).not.toBeInTheDocument();
    expect(screen.getByText('Some notes')).toBeInTheDocument();
  });

  // ── data-testid-prefix ──

  it('data-testid-prefix threads through to interactive elements', async () => {
    const user = userEvent.setup();

    render(
      <InternalNotesCard
        value="Notes"
        onSave={mockOnSave}
        isSaving={false}
        data-testid-prefix="customer-"
      />
    );

    // Collapsed state testids
    expect(screen.getByTestId('customer-internal-notes-display')).toBeInTheDocument();
    expect(screen.getByTestId('customer-edit-notes-btn')).toBeInTheDocument();
    expect(screen.getByTestId('customer-notes-editor')).toBeInTheDocument();

    // Switch to expanded
    await user.click(screen.getByTestId('customer-edit-notes-btn'));

    // Expanded state testids
    expect(screen.getByTestId('customer-internal-notes-textarea')).toBeInTheDocument();
    expect(screen.getByTestId('customer-save-notes-btn')).toBeInTheDocument();
    expect(screen.getByTestId('customer-notes-editor')).toBeInTheDocument();
  });

  it('default prefix produces unprefixed testids', async () => {
    const user = userEvent.setup();

    render(
      <InternalNotesCard
        value="Notes"
        onSave={mockOnSave}
        isSaving={false}
      />
    );

    expect(screen.getByTestId('internal-notes-display')).toBeInTheDocument();
    expect(screen.getByTestId('edit-notes-btn')).toBeInTheDocument();
    expect(screen.getByTestId('notes-editor')).toBeInTheDocument();

    await user.click(screen.getByTestId('edit-notes-btn'));

    expect(screen.getByTestId('internal-notes-textarea')).toBeInTheDocument();
    expect(screen.getByTestId('save-notes-btn')).toBeInTheDocument();
  });
});
