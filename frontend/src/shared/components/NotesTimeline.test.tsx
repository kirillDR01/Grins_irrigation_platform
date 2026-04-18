/**
 * Tests for NotesTimeline component.
 *
 * Validates: april-16th-fixes-enhancements Requirement 4
 * - Notes render newest-first
 * - Stage tags display correctly
 * - Add note form works
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NotesTimeline } from './NotesTimeline';
import type { NoteEntry } from '@/shared/hooks/useNotes';

// Mock the useNotes hooks
const mockNotes: NoteEntry[] = [
  {
    id: 'note-3',
    subject_type: 'customer',
    subject_id: 'cust-1',
    author_id: 'staff-1',
    author_name: 'Viktor Grin',
    body: 'Newest note - customer stage',
    origin_lead_id: null,
    is_system: false,
    created_at: '2025-04-16T15:00:00Z',
    updated_at: '2025-04-16T15:00:00Z',
    stage_tag: 'Customer',
  },
  {
    id: 'note-2',
    subject_type: 'sales_entry',
    subject_id: 'sales-1',
    author_id: 'staff-1',
    author_name: 'Viktor Grin',
    body: 'Stage transition: Lead → Sales',
    origin_lead_id: 'lead-1',
    is_system: true,
    created_at: '2025-04-15T12:00:00Z',
    updated_at: '2025-04-15T12:00:00Z',
    stage_tag: 'Sales',
  },
  {
    id: 'note-1',
    subject_type: 'lead',
    subject_id: 'lead-1',
    author_id: 'staff-2',
    author_name: 'Vas Tech',
    body: 'Oldest note - lead stage',
    origin_lead_id: 'lead-1',
    is_system: false,
    created_at: '2025-04-14T10:00:00Z',
    updated_at: '2025-04-14T10:00:00Z',
    stage_tag: 'Lead',
  },
];

const mockMutateAsync = vi.fn();

vi.mock('@/shared/hooks/useNotes', () => ({
  useNotes: vi.fn(() => ({
    data: mockNotes,
    isLoading: false,
    error: null,
  })),
  useCreateNote: vi.fn(() => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  })),
  noteKeys: {
    all: ['notes'],
    bySubject: (type: string, id: string) => ['notes', type, id],
  },
}));

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

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

describe('NotesTimeline', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMutateAsync.mockReset();
  });

  it('renders notes timeline container', () => {
    render(
      <NotesTimeline subjectType="customer" subjectId="cust-1" />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByTestId('notes-timeline')).toBeInTheDocument();
  });

  it('renders notes newest-first', () => {
    render(
      <NotesTimeline subjectType="customer" subjectId="cust-1" />,
      { wrapper: createWrapper() }
    );

    const noteItems = screen.getAllByTestId(/^note-item-/);
    expect(noteItems).toHaveLength(3);

    // First note should be the newest (note-3)
    expect(noteItems[0]).toHaveAttribute('data-testid', 'note-item-note-3');
    // Last note should be the oldest (note-1)
    expect(noteItems[2]).toHaveAttribute('data-testid', 'note-item-note-1');
  });

  it('displays stage tags correctly', () => {
    render(
      <NotesTimeline subjectType="customer" subjectId="cust-1" />,
      { wrapper: createWrapper() }
    );

    // All three stage tags should be present
    expect(screen.getByText('Customer')).toBeInTheDocument();
    expect(screen.getByText('Sales')).toBeInTheDocument();
    expect(screen.getByText('Lead')).toBeInTheDocument();
  });

  it('displays system badge for system notes', () => {
    render(
      <NotesTimeline subjectType="customer" subjectId="cust-1" />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText('System')).toBeInTheDocument();
  });

  it('displays author names', () => {
    render(
      <NotesTimeline subjectType="customer" subjectId="cust-1" />,
      { wrapper: createWrapper() }
    );

    expect(screen.getAllByText('Viktor Grin')).toHaveLength(2);
    expect(screen.getByText('Vas Tech')).toBeInTheDocument();
  });

  it('displays note bodies', () => {
    render(
      <NotesTimeline subjectType="customer" subjectId="cust-1" />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText('Newest note - customer stage')).toBeInTheDocument();
    expect(screen.getByText('Stage transition: Lead → Sales')).toBeInTheDocument();
    expect(screen.getByText('Oldest note - lead stage')).toBeInTheDocument();
  });

  it('renders add note form when not readOnly', () => {
    render(
      <NotesTimeline subjectType="customer" subjectId="cust-1" />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByTestId('add-note-form')).toBeInTheDocument();
    expect(screen.getByTestId('note-input')).toBeInTheDocument();
    expect(screen.getByTestId('submit-note-btn')).toBeInTheDocument();
  });

  it('hides add note form when readOnly', () => {
    render(
      <NotesTimeline subjectType="customer" subjectId="cust-1" readOnly />,
      { wrapper: createWrapper() }
    );

    expect(screen.queryByTestId('add-note-form')).not.toBeInTheDocument();
  });

  it('submit button is disabled when input is empty', () => {
    render(
      <NotesTimeline subjectType="customer" subjectId="cust-1" />,
      { wrapper: createWrapper() }
    );

    const submitBtn = screen.getByTestId('submit-note-btn');
    expect(submitBtn).toBeDisabled();
  });

  it('submits a new note when form is filled and submitted', async () => {
    const user = userEvent.setup();
    mockMutateAsync.mockResolvedValue({
      id: 'note-4',
      body: 'New test note',
    });

    render(
      <NotesTimeline subjectType="customer" subjectId="cust-1" />,
      { wrapper: createWrapper() }
    );

    const input = screen.getByTestId('note-input');
    await user.type(input, 'New test note');

    const submitBtn = screen.getByTestId('submit-note-btn');
    expect(submitBtn).not.toBeDisabled();

    await user.click(submitBtn);

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith('New test note');
    });
  });

  it('limits displayed notes when maxEntries is set', () => {
    render(
      <NotesTimeline
        subjectType="customer"
        subjectId="cust-1"
        readOnly
        maxEntries={2}
      />,
      { wrapper: createWrapper() }
    );

    const noteItems = screen.getAllByTestId(/^note-item-/);
    expect(noteItems).toHaveLength(2);

    // Should show "Showing X of Y" indicator
    expect(screen.getByText(/Showing 2 of 3 notes/)).toBeInTheDocument();
  });

  it('shows note count in header', () => {
    render(
      <NotesTimeline subjectType="customer" subjectId="cust-1" />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText('(3)')).toBeInTheDocument();
  });
});
