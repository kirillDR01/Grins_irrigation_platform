import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MarkDeclinedDialog } from './MarkDeclinedDialog';

describe('MarkDeclinedDialog', () => {
  it('renders title and required label', () => {
    render(
      <MarkDeclinedDialog
        open
        onOpenChange={vi.fn()}
        onConfirm={vi.fn()}
      />,
    );
    expect(screen.getByTestId('mark-declined-dialog')).toBeInTheDocument();
    expect(screen.getByText('Mark as Declined?')).toBeInTheDocument();
    expect(screen.getByText('Reason (required)')).toBeInTheDocument();
  });

  it('Confirm button is disabled when reason is empty', () => {
    render(
      <MarkDeclinedDialog
        open
        onOpenChange={vi.fn()}
        onConfirm={vi.fn()}
      />,
    );
    expect(screen.getByTestId('confirm-mark-declined-btn')).toBeDisabled();
  });

  it('Confirm button is disabled when reason is whitespace only', async () => {
    const user = userEvent.setup();
    render(
      <MarkDeclinedDialog
        open
        onOpenChange={vi.fn()}
        onConfirm={vi.fn()}
      />,
    );
    const ta = screen.getByTestId('decline-reason-input');
    await user.type(ta, '   ');
    expect(screen.getByTestId('confirm-mark-declined-btn')).toBeDisabled();
  });

  it('calls onConfirm with the trimmed reason', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(
      <MarkDeclinedDialog
        open
        onOpenChange={vi.fn()}
        onConfirm={onConfirm}
      />,
    );
    const ta = screen.getByTestId('decline-reason-input');
    await user.type(ta, '  Customer chose competitor  ');
    await user.click(screen.getByTestId('confirm-mark-declined-btn'));
    expect(onConfirm).toHaveBeenCalledWith('Customer chose competitor');
  });

  it('disables confirm button when isPending', () => {
    render(
      <MarkDeclinedDialog
        open
        onOpenChange={vi.fn()}
        onConfirm={vi.fn()}
        isPending
      />,
    );
    expect(screen.getByTestId('confirm-mark-declined-btn')).toBeDisabled();
    expect(screen.getByText('Saving…')).toBeInTheDocument();
  });
});
