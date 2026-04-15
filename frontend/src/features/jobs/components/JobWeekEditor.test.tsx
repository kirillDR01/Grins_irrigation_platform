import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { JobWeekEditor } from './JobWeekEditor';
import { jobApi } from '../api/jobApi';
import type { Job, JobStatus } from '../types';

vi.mock('../api/jobApi', () => ({
  jobApi: { update: vi.fn() },
}));

const mockUpdate = vi.mocked(jobApi.update);

function makeJob(
  overrides: Partial<Pick<Job, 'id' | 'status' | 'target_start_date' | 'target_end_date'>> = {},
) {
  return {
    id: '00000000-0000-0000-0000-000000000001',
    status: 'to_be_scheduled' as JobStatus,
    target_start_date: '2026-04-20',
    target_end_date: '2026-04-26',
    ...overrides,
  };
}

describe('JobWeekEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the current week on a to_be_scheduled job as a button', () => {
    render(<JobWeekEditor job={makeJob()} />);
    const trigger = screen.getByTestId(
      'week-of-00000000-0000-0000-0000-000000000001',
    );
    expect(trigger).toHaveTextContent('Week of 4/20/2026');
    expect(trigger.tagName).toBe('BUTTON');
  });

  it('renders as plain text (not a button) when status is not to_be_scheduled', () => {
    render(
      <JobWeekEditor
        job={makeJob({ status: 'scheduled', target_start_date: '2026-04-20', target_end_date: '2026-04-26' })}
      />,
    );
    const cell = screen.getByTestId(
      'week-of-00000000-0000-0000-0000-000000000001',
    );
    expect(cell).toHaveTextContent('Week of 4/20/2026');
    // Plain span, not a button — no popover to open
    expect(cell.tagName).toBe('SPAN');
  });

  it('shows "No week set" placeholder when target_start_date is null', () => {
    render(
      <JobWeekEditor job={makeJob({ target_start_date: null, target_end_date: null })} />,
    );
    expect(
      screen.getByTestId('week-of-00000000-0000-0000-0000-000000000001'),
    ).toHaveTextContent('No week set');
  });

  it('opens popover and calls jobApi.update with the chosen Mon-Sun on day select', async () => {
    mockUpdate.mockResolvedValue(makeJob({ target_start_date: '2026-04-27', target_end_date: '2026-05-03' }) as Job);
    const user = userEvent.setup();
    const onSaved = vi.fn();

    render(<JobWeekEditor job={makeJob()} onSaved={onSaved} />);
    await user.click(
      screen.getByTestId('week-of-00000000-0000-0000-0000-000000000001'),
    );

    // Calendar renders, defaulted to April 2026 because the current
    // selection is 2026-04-20. Pick a different Monday in the same
    // month (Apr 27) so no month navigation is needed.
    const cal = await screen.findByTestId(
      'week-editor-calendar-00000000-0000-0000-0000-000000000001',
    );
    expect(cal).toBeInTheDocument();

    const aprTwentySeven = await screen.findByRole('button', {
      name: /April 27/i,
    });
    await user.click(aprTwentySeven);

    await waitFor(() => {
      expect(mockUpdate).toHaveBeenCalledWith(
        '00000000-0000-0000-0000-000000000001',
        { target_start_date: '2026-04-27', target_end_date: '2026-05-03' },
      );
    });
    expect(onSaved).toHaveBeenCalledWith('2026-04-27', '2026-05-03');
  });

  it('shows an inline error when the API call fails', async () => {
    mockUpdate.mockRejectedValue(new Error('server blew up'));
    const user = userEvent.setup();

    render(<JobWeekEditor job={makeJob()} />);
    await user.click(
      screen.getByTestId('week-of-00000000-0000-0000-0000-000000000001'),
    );
    await screen.findByTestId(
      'week-editor-calendar-00000000-0000-0000-0000-000000000001',
    );
    const aprTwentySeven = await screen.findByRole('button', {
      name: /April 27/i,
    });
    await user.click(aprTwentySeven);

    const err = await screen.findByTestId(
      'week-editor-error-00000000-0000-0000-0000-000000000001',
    );
    expect(err).toHaveTextContent(/server blew up/i);
  });
});
