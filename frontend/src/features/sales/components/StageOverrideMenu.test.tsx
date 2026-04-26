import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StageOverrideMenu } from './StageOverrideMenu';

describe('StageOverrideMenu', () => {
  it('renders all 5 canonical stages when opened', async () => {
    const user = userEvent.setup();
    render(
      <StageOverrideMenu currentStage="schedule_estimate" onSelect={vi.fn()}>
        <button data-testid="trigger">open</button>
      </StageOverrideMenu>,
    );
    await user.click(screen.getByTestId('trigger'));
    expect(await screen.findByTestId('stage-override-menu')).toBeInTheDocument();
    expect(screen.getByTestId('stage-override-schedule_estimate')).toBeInTheDocument();
    expect(screen.getByTestId('stage-override-send_estimate')).toBeInTheDocument();
    expect(screen.getByTestId('stage-override-pending_approval')).toBeInTheDocument();
    expect(screen.getByTestId('stage-override-send_contract')).toBeInTheDocument();
    expect(screen.getByTestId('stage-override-closed_won')).toBeInTheDocument();
  });

  it('selecting a non-current stage fires onSelect with that stage key', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <StageOverrideMenu currentStage="schedule_estimate" onSelect={onSelect}>
        <button data-testid="trigger">open</button>
      </StageOverrideMenu>,
    );
    await user.click(screen.getByTestId('trigger'));
    await user.click(await screen.findByTestId('stage-override-pending_approval'));
    expect(onSelect).toHaveBeenCalledWith('pending_approval');
  });

  it('disables the current stage item', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <StageOverrideMenu currentStage="send_estimate" onSelect={onSelect}>
        <button data-testid="trigger">open</button>
      </StageOverrideMenu>,
    );
    await user.click(screen.getByTestId('trigger'));
    const currentItem = await screen.findByTestId('stage-override-send_estimate');
    expect(currentItem).toHaveAttribute('aria-disabled', 'true');
  });
});
