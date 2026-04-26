import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ForceConvertDialog } from './ForceConvertDialog';

describe('ForceConvertDialog', () => {
  it('renders title and description when open', () => {
    render(
      <ForceConvertDialog
        open
        onOpenChange={vi.fn()}
        isPending={false}
        onConfirm={vi.fn()}
      />,
    );
    expect(screen.getByTestId('force-convert-dialog')).toBeInTheDocument();
    expect(screen.getByText('Force Convert to Job?')).toBeInTheDocument();
    expect(screen.getByText(/No customer signature is on file/)).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(
      <ForceConvertDialog
        open={false}
        onOpenChange={vi.fn()}
        isPending={false}
        onConfirm={vi.fn()}
      />,
    );
    expect(screen.queryByTestId('force-convert-dialog')).not.toBeInTheDocument();
  });

  it('calls onConfirm when Force Convert clicked', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(
      <ForceConvertDialog
        open
        onOpenChange={vi.fn()}
        isPending={false}
        onConfirm={onConfirm}
      />,
    );
    await user.click(screen.getByTestId('confirm-force-convert-btn'));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it('calls onOpenChange(false) when Cancel clicked', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(
      <ForceConvertDialog
        open
        onOpenChange={onOpenChange}
        isPending={false}
        onConfirm={vi.fn()}
      />,
    );
    await user.click(screen.getByTestId('cancel-force-convert-btn'));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('disables both buttons and shows spinner label when isPending', () => {
    render(
      <ForceConvertDialog
        open
        onOpenChange={vi.fn()}
        isPending
        onConfirm={vi.fn()}
      />,
    );
    expect(screen.getByTestId('confirm-force-convert-btn')).toBeDisabled();
    expect(screen.getByTestId('cancel-force-convert-btn')).toBeDisabled();
    expect(screen.getByText('Converting…')).toBeInTheDocument();
  });
});
