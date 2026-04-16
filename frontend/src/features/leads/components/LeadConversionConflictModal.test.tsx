import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { LeadConversionConflictModal } from './LeadConversionConflictModal';
import type { DuplicateConflictCustomer } from '../types';

function makeDup(
  overrides: Partial<DuplicateConflictCustomer> = {},
): DuplicateConflictCustomer {
  return {
    id: 'cust-abc',
    first_name: 'Alice',
    last_name: 'Smith',
    phone: '+19527373312',
    email: 'alice@test.example',
    ...overrides,
  };
}

describe('LeadConversionConflictModal (CR-6)', () => {
  it('renders list of duplicate customers', () => {
    render(
      <LeadConversionConflictModal
        open={true}
        onClose={vi.fn()}
        duplicates={[
          makeDup({ id: 'cust-1', first_name: 'Alice', last_name: 'Smith' }),
          makeDup({
            id: 'cust-2',
            first_name: 'Bob',
            last_name: 'Smith',
            phone: '+19527373313',
          }),
        ]}
        onUseExisting={vi.fn()}
        onConvertAnyway={vi.fn()}
        phone="+19527373312"
        email="alice@test.example"
      />,
    );

    expect(
      screen.getByTestId('lead-conversion-conflict-modal'),
    ).toBeInTheDocument();
    expect(screen.getByText(/Alice Smith/)).toBeInTheDocument();
    expect(screen.getByText(/Bob Smith/)).toBeInTheDocument();
    // Both "Use existing" buttons are rendered.
    expect(screen.getByTestId('use-existing-cust-1')).toBeInTheDocument();
    expect(screen.getByTestId('use-existing-cust-2')).toBeInTheDocument();
  });

  it('fires onConvertAnyway when button clicked', async () => {
    const user = userEvent.setup();
    const onConvertAnyway = vi.fn();
    render(
      <LeadConversionConflictModal
        open={true}
        onClose={vi.fn()}
        duplicates={[makeDup()]}
        onUseExisting={vi.fn()}
        onConvertAnyway={onConvertAnyway}
      />,
    );

    await user.click(screen.getByTestId('convert-anyway-btn'));
    expect(onConvertAnyway).toHaveBeenCalledTimes(1);
  });

  it('fires onUseExisting with correct customer id', async () => {
    const user = userEvent.setup();
    const onUseExisting = vi.fn();
    const dup = makeDup({ id: 'cust-xyz' });
    render(
      <LeadConversionConflictModal
        open={true}
        onClose={vi.fn()}
        duplicates={[dup]}
        onUseExisting={onUseExisting}
        onConvertAnyway={vi.fn()}
      />,
    );

    await user.click(screen.getByTestId('use-existing-cust-xyz'));
    expect(onUseExisting).toHaveBeenCalledTimes(1);
    const arg = onUseExisting.mock.calls[0][0];
    expect(arg.id).toBe('cust-xyz');
  });

  it('fires onClose when Cancel clicked', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <LeadConversionConflictModal
        open={true}
        onClose={onClose}
        duplicates={[makeDup()]}
        onUseExisting={vi.fn()}
        onConvertAnyway={vi.fn()}
      />,
    );

    await user.click(screen.getByTestId('cancel-convert-btn'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('disables convert-anyway button while isConverting is true', () => {
    render(
      <LeadConversionConflictModal
        open={true}
        onClose={vi.fn()}
        duplicates={[makeDup()]}
        onUseExisting={vi.fn()}
        onConvertAnyway={vi.fn()}
        isConverting={true}
      />,
    );

    expect(screen.getByTestId('convert-anyway-btn')).toBeDisabled();
    expect(screen.getByTestId('cancel-convert-btn')).toBeDisabled();
  });
});
