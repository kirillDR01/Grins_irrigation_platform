import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SchedulingTray } from './SchedulingTray';
import type { JobReadyToSchedule, PerJobTimeMap } from '../types/pick-jobs';
import type { Staff } from '@/features/staff/types';

const mockStaff: Staff[] = [
  {
    id: 's1',
    name: 'Alice',
    phone: '6125550001',
    email: null,
    role: 'tech',
    skill_level: 'senior',
    certifications: null,
    is_available: true,
    availability_notes: null,
    hourly_rate: null,
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
];

const mockJob: JobReadyToSchedule = {
  job_id: 'j1',
  customer_id: 'c1',
  customer_name: 'John Doe',
  city: 'Minneapolis',
  job_type: 'Spring Startup',
  estimated_duration_minutes: 60,
  customer_tags: [],
  priority_level: 0,
  requested_week: '2024-04-15',
  notes: '',
};

const defaultProps = {
  selectedJobIds: new Set<string>(),
  selectedJobs: [] as JobReadyToSchedule[],
  totalSelectedCount: 0,
  staff: mockStaff,
  assignDate: '2024-04-15',
  onAssignDateChange: vi.fn(),
  assignStaffId: '',
  onAssignStaffIdChange: vi.fn(),
  startTime: '08:00',
  onStartTimeChange: vi.fn(),
  duration: 60,
  onDurationChange: vi.fn(),
  perJobTimes: {} as PerJobTimeMap,
  onPerJobTimesChange: vi.fn(),
  showTimeAdjust: false,
  onShowTimeAdjustChange: vi.fn(),
  isAssigning: false,
  onAssign: vi.fn(),
  onClearSelection: vi.fn(),
};

describe('SchedulingTray', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('always renders (idle state)', () => {
    render(<SchedulingTray {...defaultProps} />);
    expect(screen.getByTestId('scheduling-tray')).toBeInTheDocument();
  });

  it('shows idle header text when no jobs selected', () => {
    render(<SchedulingTray {...defaultProps} />);
    expect(screen.getByText(/No jobs selected yet/)).toBeInTheDocument();
  });

  it('shows active header text with count when jobs selected', () => {
    render(
      <SchedulingTray
        {...defaultProps}
        selectedJobIds={new Set(['j1'])}
        selectedJobs={[mockJob]}
        totalSelectedCount={1}
      />
    );
    expect(screen.getByText(/Schedule/)).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('shows plural "jobs" for multiple selections', () => {
    render(
      <SchedulingTray
        {...defaultProps}
        selectedJobIds={new Set(['j1', 'j2'])}
        selectedJobs={[mockJob, { ...mockJob, job_id: 'j2' }]}
        totalSelectedCount={2}
      />
    );
    expect(screen.getByText(/jobs/)).toBeInTheDocument();
  });

  it('shows hidden selections note when some selected jobs are filtered out', () => {
    render(
      <SchedulingTray
        {...defaultProps}
        selectedJobIds={new Set(['j1', 'j2'])}
        selectedJobs={[mockJob]} // only 1 visible, 1 hidden
        totalSelectedCount={2}
      />
    );
    expect(screen.getByText(/hidden by current filters/)).toBeInTheDocument();
  });

  it('does not show hidden selections note when all selected jobs are visible', () => {
    render(
      <SchedulingTray
        {...defaultProps}
        selectedJobIds={new Set(['j1'])}
        selectedJobs={[mockJob]}
        totalSelectedCount={1}
      />
    );
    expect(screen.queryByText(/hidden by current filters/)).not.toBeInTheDocument();
  });

  it('assign button is disabled when no jobs selected', () => {
    render(<SchedulingTray {...defaultProps} />);
    expect(screen.getByTestId('tray-assign-btn')).toBeDisabled();
  });

  it('assign button is disabled when no staff selected', () => {
    render(
      <SchedulingTray
        {...defaultProps}
        selectedJobIds={new Set(['j1'])}
        selectedJobs={[mockJob]}
        totalSelectedCount={1}
        assignStaffId=""
      />
    );
    expect(screen.getByTestId('tray-assign-btn')).toBeDisabled();
  });

  it('assign button is disabled when isAssigning is true', () => {
    render(
      <SchedulingTray
        {...defaultProps}
        selectedJobIds={new Set(['j1'])}
        selectedJobs={[mockJob]}
        totalSelectedCount={1}
        assignStaffId="s1"
        isAssigning={true}
      />
    );
    expect(screen.getByTestId('tray-assign-btn')).toBeDisabled();
  });

  it('assign button is disabled when time overlap exists', () => {
    const perJobTimes: PerJobTimeMap = {
      j1: { start: '10:00', end: '09:00' }, // end <= start
    };
    render(
      <SchedulingTray
        {...defaultProps}
        selectedJobIds={new Set(['j1'])}
        selectedJobs={[mockJob]}
        totalSelectedCount={1}
        assignStaffId="s1"
        perJobTimes={perJobTimes}
      />
    );
    expect(screen.getByTestId('tray-assign-btn')).toBeDisabled();
  });

  it('assign button is enabled when jobs selected and staff chosen', () => {
    render(
      <SchedulingTray
        {...defaultProps}
        selectedJobIds={new Set(['j1'])}
        selectedJobs={[mockJob]}
        totalSelectedCount={1}
        assignStaffId="s1"
      />
    );
    expect(screen.getByTestId('tray-assign-btn')).not.toBeDisabled();
  });

  it('shows "Pick jobs above to continue" helper when no selection', () => {
    render(<SchedulingTray {...defaultProps} />);
    expect(screen.getByText('Pick jobs above to continue')).toBeInTheDocument();
  });

  it('shows "Pick a staff member to continue" helper when jobs selected but no staff', () => {
    render(
      <SchedulingTray
        {...defaultProps}
        selectedJobIds={new Set(['j1'])}
        selectedJobs={[mockJob]}
        totalSelectedCount={1}
        assignStaffId=""
      />
    );
    expect(screen.getByText('Pick a staff member to continue')).toBeInTheDocument();
  });

  it('shows overlap warning helper when time overlap exists', () => {
    const perJobTimes: PerJobTimeMap = {
      j1: { start: '10:00', end: '09:00' },
    };
    render(
      <SchedulingTray
        {...defaultProps}
        selectedJobIds={new Set(['j1'])}
        selectedJobs={[mockJob]}
        totalSelectedCount={1}
        assignStaffId="s1"
        perJobTimes={perJobTimes}
      />
    );
    expect(screen.getByText(/overlap/)).toBeInTheDocument();
  });

  it('per-job time adjustments toggle is hidden when no selection', () => {
    render(<SchedulingTray {...defaultProps} />);
    expect(screen.queryByTestId('tray-time-adjust-toggle')).not.toBeInTheDocument();
  });

  it('per-job time adjustments toggle is visible when jobs selected', () => {
    render(
      <SchedulingTray
        {...defaultProps}
        selectedJobIds={new Set(['j1'])}
        selectedJobs={[mockJob]}
        totalSelectedCount={1}
      />
    );
    expect(screen.getByTestId('tray-time-adjust-toggle')).toBeInTheDocument();
  });

  it('clicking toggle calls onShowTimeAdjustChange', () => {
    render(
      <SchedulingTray
        {...defaultProps}
        selectedJobIds={new Set(['j1'])}
        selectedJobs={[mockJob]}
        totalSelectedCount={1}
      />
    );
    fireEvent.click(screen.getByTestId('tray-time-adjust-toggle'));
    expect(defaultProps.onShowTimeAdjustChange).toHaveBeenCalledWith(true);
  });

  it('time adjust table is hidden when showTimeAdjust is false', () => {
    render(
      <SchedulingTray
        {...defaultProps}
        selectedJobIds={new Set(['j1'])}
        selectedJobs={[mockJob]}
        totalSelectedCount={1}
        showTimeAdjust={false}
      />
    );
    expect(screen.queryByTestId('tray-time-adjust-table')).not.toBeInTheDocument();
  });

  it('time adjust table is visible when showTimeAdjust is true', () => {
    render(
      <SchedulingTray
        {...defaultProps}
        selectedJobIds={new Set(['j1'])}
        selectedJobs={[mockJob]}
        totalSelectedCount={1}
        showTimeAdjust={true}
      />
    );
    expect(screen.getByTestId('tray-time-adjust-table')).toBeInTheDocument();
  });

  it('time adjust table shows selected job rows', () => {
    render(
      <SchedulingTray
        {...defaultProps}
        selectedJobIds={new Set(['j1'])}
        selectedJobs={[mockJob]}
        totalSelectedCount={1}
        showTimeAdjust={true}
      />
    );
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('Spring Startup')).toBeInTheDocument();
  });

  it('aria-live="polite" is on the header element', () => {
    render(<SchedulingTray {...defaultProps} />);
    const liveRegion = screen.getByRole('region', { name: /Scheduling assignment/i });
    const ariaLive = liveRegion.querySelector('[aria-live="polite"]');
    expect(ariaLive).toBeInTheDocument();
  });

  it('shows "Assigning…" label when isAssigning', () => {
    render(
      <SchedulingTray
        {...defaultProps}
        selectedJobIds={new Set(['j1'])}
        selectedJobs={[mockJob]}
        totalSelectedCount={1}
        assignStaffId="s1"
        isAssigning={true}
      />
    );
    expect(screen.getByTestId('tray-assign-btn')).toHaveTextContent('Assigning…');
  });

  it('shows "Assign N Jobs" label when active and not assigning', () => {
    render(
      <SchedulingTray
        {...defaultProps}
        selectedJobIds={new Set(['j1'])}
        selectedJobs={[mockJob]}
        totalSelectedCount={1}
        assignStaffId="s1"
      />
    );
    expect(screen.getByTestId('tray-assign-btn')).toHaveTextContent('Assign 1 Job');
  });

  it('shows "Assign" label when idle', () => {
    render(<SchedulingTray {...defaultProps} />);
    expect(screen.getByTestId('tray-assign-btn')).toHaveTextContent('Assign');
  });

  it('calls onClearSelection when Clear selection is clicked', () => {
    render(
      <SchedulingTray
        {...defaultProps}
        selectedJobIds={new Set(['j1'])}
        selectedJobs={[mockJob]}
        totalSelectedCount={1}
      />
    );
    fireEvent.click(screen.getByTestId('tray-clear-selection'));
    expect(defaultProps.onClearSelection).toHaveBeenCalledTimes(1);
  });

  it('Clear selection link is not shown in idle state', () => {
    render(<SchedulingTray {...defaultProps} />);
    expect(screen.queryByTestId('tray-clear-selection')).not.toBeInTheDocument();
  });

  it('renders all tray field inputs', () => {
    render(<SchedulingTray {...defaultProps} />);
    expect(screen.getByTestId('tray-date')).toBeInTheDocument();
    expect(screen.getByTestId('tray-staff')).toBeInTheDocument();
    expect(screen.getByTestId('tray-start-time')).toBeInTheDocument();
    expect(screen.getByTestId('tray-duration')).toBeInTheDocument();
  });
});
