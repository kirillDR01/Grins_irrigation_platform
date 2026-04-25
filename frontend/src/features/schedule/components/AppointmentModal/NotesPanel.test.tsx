/**
 * Tests for NotesPanel — inline expansion panel for internal notes.
 * Validates: Requirements 6.1–6.11, 11.2, 11.3, 12.2, 12.3, 13.3
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NotesPanel } from './NotesPanel';

// ── Mock hooks ───────────────────────────────────────────────────────────────

const mockMutateAsync = vi.fn();

vi.mock('../../hooks/useAppointmentNotes', () => ({
  useAppointmentNotes: vi.fn(() => ({
    data: {
      appointment_id: 'appt-001',
      body: 'Gate code 4521#. Dog is friendly.',
      updated_at: '2025-06-15T14:30:00Z',
      updated_by: { id: 'staff-1', name: 'Viktor K.', role: 'tech' },
    },
    isLoading: false,
    error: null,
  })),
  useSaveAppointmentNotes: vi.fn(() => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  })),
  appointmentNoteKeys: {
    all: ['appointment-notes'] as const,
    detail: (id: string) => ['appointment-notes', id] as const,
  },
}));

const mockToastError = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: unknown[]) => mockToastError(...args),
    success: vi.fn(),
  },
}));

// ── Helpers ──────────────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

interface RenderOptions {
  editing?: boolean;
  onSetEditing?: (editing: boolean) => void;
}

function renderNotesPanel(opts: RenderOptions = {}) {
  const onSetEditing = opts.onSetEditing ?? vi.fn();
  return {
    onSetEditing,
    ...render(
      <NotesPanel
        appointmentId="appt-001"
        editing={opts.editing ?? false}
        onSetEditing={onSetEditing}
      />,
      { wrapper: createWrapper() },
    ),
  };
}

// ── View mode ────────────────────────────────────────────────────────────────

describe('NotesPanel — View mode', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMutateAsync.mockResolvedValue({});
  });

  it('renders "INTERNAL NOTES" eyebrow', () => {
    renderNotesPanel();
    expect(screen.getByText('INTERNAL NOTES')).toBeInTheDocument();
  });

  it('renders the note body text', () => {
    renderNotesPanel();
    expect(screen.getByText('Gate code 4521#. Dog is friendly.')).toBeInTheDocument();
  });

  it('renders Edit affordance in view mode', () => {
    renderNotesPanel();
    expect(screen.getByRole('button', { name: /edit notes/i })).toBeInTheDocument();
    expect(screen.getByText('Edit')).toBeInTheDocument();
  });

  it('renders the panel with data-testid', () => {
    renderNotesPanel();
    expect(screen.getByTestId('notes-panel')).toBeInTheDocument();
  });
});

// ── Edit mode transition ─────────────────────────────────────────────────────

describe('NotesPanel — Edit mode', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMutateAsync.mockResolvedValue({});
  });

  it('renders textarea pre-filled with current body when editing', () => {
    renderNotesPanel({ editing: true });

    const textarea = screen.getByTestId('notes-textarea') as HTMLTextAreaElement;
    expect(textarea).toBeInTheDocument();
    expect(textarea.value).toBe('Gate code 4521#. Dog is friendly.');
  });

  it('hides Edit affordance in edit mode', () => {
    renderNotesPanel({ editing: true });
    expect(screen.queryByRole('button', { name: /edit notes/i })).not.toBeInTheDocument();
  });

  it('renders Cancel and Save Notes buttons in edit mode', () => {
    renderNotesPanel({ editing: true });
    expect(screen.getByTestId('notes-cancel-btn')).toBeInTheDocument();
    expect(screen.getByTestId('notes-save-btn')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
    expect(screen.getByText('Save Notes')).toBeInTheDocument();
  });
});

// ── Cancel discards changes ──────────────────────────────────────────────────

describe('NotesPanel — Cancel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMutateAsync.mockResolvedValue({});
  });

  it('calls onSetEditing(false) when Cancel is clicked', async () => {
    const user = userEvent.setup();
    const { onSetEditing } = renderNotesPanel({ editing: true });

    await user.click(screen.getByTestId('notes-cancel-btn'));
    expect(onSetEditing).toHaveBeenCalledWith(false);
  });
});

// ── Save Notes triggers mutation ─────────────────────────────────────────────

describe('NotesPanel — Save Notes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMutateAsync.mockResolvedValue({});
  });

  it('calls mutateAsync when Save Notes is clicked', async () => {
    const user = userEvent.setup();
    renderNotesPanel({ editing: true });

    await user.click(screen.getByTestId('notes-save-btn'));

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        appointmentId: 'appt-001',
        body: 'Gate code 4521#. Dog is friendly.',
      });
    });
  });

  it('calls onSetEditing(false) on successful save', async () => {
    const user = userEvent.setup();
    const { onSetEditing } = renderNotesPanel({ editing: true });

    await user.click(screen.getByTestId('notes-save-btn'));

    await waitFor(() => {
      expect(onSetEditing).toHaveBeenCalledWith(false);
    });
  });
});

// ── Escape key cancels editing ───────────────────────────────────────────────

describe('NotesPanel — Escape key', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMutateAsync.mockResolvedValue({});
  });

  it('calls onSetEditing(false) when Escape is pressed in textarea', async () => {
    const user = userEvent.setup();
    const { onSetEditing } = renderNotesPanel({ editing: true });

    const textarea = screen.getByTestId('notes-textarea');
    textarea.focus();
    await user.keyboard('{Escape}');

    expect(onSetEditing).toHaveBeenCalledWith(false);
  });
});

// ── ⌘+Enter / Ctrl+Enter saves notes ────────────────────────────────────────

describe('NotesPanel — Keyboard save shortcut', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMutateAsync.mockResolvedValue({});
  });

  it('saves notes on Ctrl+Enter', async () => {
    renderNotesPanel({ editing: true });

    const textarea = screen.getByTestId('notes-textarea');
    textarea.focus();

    // Fire Ctrl+Enter via native event since userEvent doesn't support meta combos well
    textarea.dispatchEvent(
      new KeyboardEvent('keydown', {
        key: 'Enter',
        ctrlKey: true,
        bubbles: true,
      }),
    );

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalled();
    });
  });

  it('saves notes on Meta+Enter (⌘+Enter)', async () => {
    renderNotesPanel({ editing: true });

    const textarea = screen.getByTestId('notes-textarea');
    textarea.focus();

    textarea.dispatchEvent(
      new KeyboardEvent('keydown', {
        key: 'Enter',
        metaKey: true,
        bubbles: true,
      }),
    );

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalled();
    });
  });
});

// ── Error toast on save failure ──────────────────────────────────────────────

describe('NotesPanel — Error handling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows error toast on save failure and remains in edit mode', async () => {
    mockMutateAsync.mockRejectedValueOnce(new Error('Network error'));
    const user = userEvent.setup();
    const { onSetEditing } = renderNotesPanel({ editing: true });

    await user.click(screen.getByTestId('notes-save-btn'));

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Couldn't save notes — try again");
    });

    // Should re-enter edit mode (onSetEditing(true) called after failure)
    await waitFor(() => {
      expect(onSetEditing).toHaveBeenCalledWith(true);
    });
  });
});
