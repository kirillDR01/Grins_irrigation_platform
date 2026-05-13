/**
 * Tests for TagEditorSheet — the Sheet wrapper around <TagPicker>.
 * Internals were moved into the shared TagPicker; per-tag behaviour is
 * covered by TagPicker.test.tsx. Here we only verify the sheet chrome
 * + that the picker is passed the right customerId.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TagEditorSheet } from './TagEditorSheet';

vi.mock('@/features/customers/components/TagPicker', () => ({
  TagPicker: ({ customerId }: { customerId: string }) => (
    <div data-testid="tag-picker-mock" data-customer-id={customerId} />
  ),
}));

describe('TagEditorSheet', () => {
  it('renders sheet title + subtitle with customer name', () => {
    render(
      <TagEditorSheet
        customerId="cust-001"
        customerName="Jane Smith"
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText('Edit tags')).toBeInTheDocument();
    expect(
      screen.getByText(/Tags apply to Jane Smith across every job/i),
    ).toBeInTheDocument();
  });

  it('mounts TagPicker with the customer id', () => {
    render(
      <TagEditorSheet
        customerId="cust-042"
        customerName="Acme"
        onClose={vi.fn()}
      />,
    );
    const picker = screen.getByTestId('tag-picker-mock');
    expect(picker).toBeInTheDocument();
    expect(picker.getAttribute('data-customer-id')).toBe('cust-042');
  });

  it('Done button calls onClose', async () => {
    const onClose = vi.fn();
    render(
      <TagEditorSheet
        customerId="cust-001"
        customerName="Jane"
        onClose={onClose}
      />,
    );
    await userEvent.click(screen.getByRole('button', { name: /done/i }));
    expect(onClose).toHaveBeenCalled();
  });
});
