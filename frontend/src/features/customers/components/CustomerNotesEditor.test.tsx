/**
 * CustomerNotesEditor tests — auto-save-on-blur behavior.
 *
 * Validates: Cluster A — shared customer.internal_notes editor.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CustomerNotesEditor } from './CustomerNotesEditor';

const mockMutate = vi.fn();
const mockInvalidateAfterCustomerInternalNotesSave = vi.fn();

vi.mock('@/features/customers/hooks/useCustomerMutations', () => ({
  useUpdateCustomer: () => ({
    mutate: mockMutate,
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

vi.mock('@/shared/utils/invalidationHelpers', () => ({
  invalidateAfterCustomerInternalNotesSave: (...args: unknown[]) =>
    mockInvalidateAfterCustomerInternalNotesSave(...args),
}));

vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

function renderEditor(props: Partial<Parameters<typeof CustomerNotesEditor>[0]> = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <CustomerNotesEditor customerId="cust-1" {...props} />
    </QueryClientProvider>,
  );
}

describe('CustomerNotesEditor', () => {
  beforeEach(() => {
    mockMutate.mockClear();
    mockInvalidateAfterCustomerInternalNotesSave.mockClear();
  });

  it('renders with the initial value', () => {
    renderEditor({ initialValue: 'original blob' });
    const textarea = screen.getByTestId(
      'customer-notes-editor-textarea',
    ) as HTMLTextAreaElement;
    expect(textarea.value).toBe('original blob');
  });

  it('does not fire mutate on blur when the value is unchanged', async () => {
    const user = userEvent.setup();
    renderEditor({ initialValue: 'same value' });
    const textarea = screen.getByTestId('customer-notes-editor-textarea');
    await user.click(textarea);
    await user.tab(); // blur without typing
    expect(mockMutate).not.toHaveBeenCalled();
  });

  it('fires exactly one mutate on blur with changed value', async () => {
    const user = userEvent.setup();
    renderEditor({ initialValue: '' });
    const textarea = screen.getByTestId('customer-notes-editor-textarea');
    await user.click(textarea);
    await user.type(textarea, 'new note');
    await user.tab(); // blur

    await waitFor(() => expect(mockMutate).toHaveBeenCalledTimes(1));
    const [firstCall] = mockMutate.mock.calls;
    expect(firstCall[0]).toEqual({
      id: 'cust-1',
      data: { internal_notes: 'new note' },
    });
  });

  it('does not allow editing when readOnly', () => {
    renderEditor({ initialValue: 'frozen', readOnly: true });
    const textarea = screen.getByTestId(
      'customer-notes-editor-textarea',
    ) as HTMLTextAreaElement;
    expect(textarea).toBeDisabled();
  });
});
