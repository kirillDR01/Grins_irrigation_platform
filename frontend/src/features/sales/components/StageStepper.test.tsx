// StageStepper.test.tsx — Requirements: 7.1–7.8, Property 5
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import * as fc from 'fast-check';
import { StageStepper } from './StageStepper';
import { STAGES, STAGE_INDEX, type StageKey } from '../types/pipeline';

const STAGE_KEYS: StageKey[] = STAGES.map((s) => s.key);

function renderStepper(currentStage: StageKey, overrides?: Partial<Parameters<typeof StageStepper>[0]>) {
  const onStageOverride = vi.fn();
  const onMarkLost = vi.fn();
  render(
    <StageStepper
      currentStage={currentStage}
      onStageOverride={onStageOverride}
      onMarkLost={onMarkLost}
      {...overrides}
    />,
  );
  return { onStageOverride, onMarkLost };
}

describe('StageStepper', () => {
  it('renders 5 steps', () => {
    renderStepper('schedule_estimate');
    expect(screen.getByTestId('stage-stepper')).toBeInTheDocument();
    STAGES.forEach((s) => {
      expect(screen.getByTestId(`stage-step-${s.key}`)).toBeInTheDocument();
    });
  });

  it('renders 3 phase labels', () => {
    renderStepper('schedule_estimate');
    expect(screen.getByText('Plan')).toBeInTheDocument();
    expect(screen.getByText('Sign')).toBeInTheDocument();
    expect(screen.getByText('Close')).toBeInTheDocument();
  });

  it('first step is active when currentStage is schedule_estimate', () => {
    renderStepper('schedule_estimate');
    expect(screen.getByTestId('stage-step-schedule_estimate')).toHaveAttribute('data-state', 'active');
    expect(screen.getByTestId('stage-step-send_estimate')).toHaveAttribute('data-state', 'future');
  });

  it('pending_approval shows waiting state', () => {
    renderStepper('pending_approval');
    expect(screen.getByTestId('stage-step-pending_approval')).toHaveAttribute('data-state', 'waiting');
  });

  it('steps before current are done', () => {
    renderStepper('send_contract');
    expect(screen.getByTestId('stage-step-schedule_estimate')).toHaveAttribute('data-state', 'done');
    expect(screen.getByTestId('stage-step-send_estimate')).toHaveAttribute('data-state', 'done');
    expect(screen.getByTestId('stage-step-pending_approval')).toHaveAttribute('data-state', 'done');
    expect(screen.getByTestId('stage-step-send_contract')).toHaveAttribute('data-state', 'active');
    expect(screen.getByTestId('stage-step-closed_won')).toHaveAttribute('data-state', 'future');
  });

  it('override button opens StageOverrideMenu and selecting a stage fires onStageOverride', async () => {
    const user = userEvent.setup();
    const { onStageOverride } = renderStepper('send_estimate');
    await user.click(screen.getByTestId('stage-stepper-override'));
    // Menu opens with all 5 stages.
    expect(await screen.findByTestId('stage-override-menu')).toBeInTheDocument();
    expect(screen.getByTestId('stage-override-schedule_estimate')).toBeInTheDocument();
    expect(screen.getByTestId('stage-override-send_estimate')).toBeInTheDocument();
    expect(screen.getByTestId('stage-override-pending_approval')).toBeInTheDocument();
    expect(screen.getByTestId('stage-override-send_contract')).toBeInTheDocument();
    expect(screen.getByTestId('stage-override-closed_won')).toBeInTheDocument();
    // Selecting a non-current stage fires the callback with that stage key.
    await user.click(screen.getByTestId('stage-override-pending_approval'));
    expect(onStageOverride).toHaveBeenCalledOnce();
    expect(onStageOverride).toHaveBeenCalledWith('pending_approval');
  });

  it('selecting the current stage does not fire onStageOverride', async () => {
    const user = userEvent.setup();
    const { onStageOverride } = renderStepper('send_estimate');
    await user.click(screen.getByTestId('stage-stepper-override'));
    const currentItem = await screen.findByTestId('stage-override-send_estimate');
    expect(currentItem).toHaveAttribute('aria-disabled', 'true');
    // Click attempt — disabled DropdownMenuItem won't dispatch onSelect.
    await user.click(currentItem);
    expect(onStageOverride).not.toHaveBeenCalled();
  });

  it('Mark Lost button calls onMarkLost', async () => {
    const user = userEvent.setup();
    const { onMarkLost } = renderStepper('send_estimate');
    await user.click(screen.getByTestId('stage-stepper-mark-lost'));
    expect(onMarkLost).toHaveBeenCalledOnce();
  });

  it('calendar badge renders when visitScheduled is true', () => {
    renderStepper('schedule_estimate', { visitScheduled: true, visitLabel: 'Apr 19 2pm' });
    expect(screen.getByText('Apr 19 2pm')).toBeInTheDocument();
  });

  it('calendar badge does not render when visitScheduled is false', () => {
    renderStepper('schedule_estimate', { visitScheduled: false });
    expect(screen.queryByText(/Scheduled/)).not.toBeInTheDocument();
  });
});

// Property 5: StageStepper Step State Computation
describe('Property 5: StageStepper step state computation', () => {
  it('all steps before current are done, current is active/waiting, rest are future', () => {
    fc.assert(
      fc.property(fc.constantFrom(...STAGE_KEYS), (stageKey) => {
        const { unmount } = render(
          <StageStepper
            currentStage={stageKey}
            onStageOverride={() => {}}
            onMarkLost={() => {}}
          />,
        );
        const currentIdx = STAGE_INDEX[stageKey];
        STAGES.forEach((s, i) => {
          const el = document.querySelector(`[data-testid="stage-step-${s.key}"]`);
          expect(el).not.toBeNull();
          const state = el!.getAttribute('data-state');
          if (i < currentIdx) {
            expect(state).toBe('done');
          } else if (i === currentIdx) {
            const expected = s.key === 'pending_approval' ? 'waiting' : 'active';
            expect(state).toBe(expected);
          } else {
            expect(state).toBe('future');
          }
        });
        unmount();
      }),
      { numRuns: 100 },
    );
  });
});
