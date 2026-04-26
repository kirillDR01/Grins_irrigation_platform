import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SubSheetHeader } from './SubSheetHeader';

describe('SubSheetHeader', () => {
  it('renders the title', () => {
    render(<SubSheetHeader title="Edit tags" onBack={vi.fn()} />);
    expect(screen.getByText('Edit tags')).toBeInTheDocument();
  });

  it('fires onBack when the back button is clicked', async () => {
    const user = userEvent.setup();
    const onBack = vi.fn();
    render(<SubSheetHeader title="Edit tags" onBack={onBack} />);

    await user.click(screen.getByTestId('subsheet-back-btn'));

    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it('renders an optional rightAction slot', () => {
    render(
      <SubSheetHeader
        title="Collect payment"
        onBack={vi.fn()}
        rightAction={<span data-testid="custom-right">Skip</span>}
      />
    );
    expect(screen.getByTestId('custom-right')).toBeInTheDocument();
  });

  it('uses a 44 × 44 px touch target for the back button', () => {
    render(<SubSheetHeader title="Edit tags" onBack={vi.fn()} />);
    const btn = screen.getByTestId('subsheet-back-btn');
    expect(btn.className).toMatch(/h-11/);
    expect(btn.className).toMatch(/w-11/);
  });
});
