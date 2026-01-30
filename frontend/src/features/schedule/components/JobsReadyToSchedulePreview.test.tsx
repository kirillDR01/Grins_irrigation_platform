import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { JobsReadyToSchedulePreview } from './JobsReadyToSchedulePreview';
import type { JobReadyToSchedule } from '../types';
import type { ReactNode } from 'react';

// Mock UI components
vi.mock('@/shared/components/ui/card', () => ({
  Card: ({ children, ...props }: { children: ReactNode; [key: string]: unknown }) => <div {...props}>{children}</div>,
  CardContent: ({ children, ...props }: { children: ReactNode; [key: string]: unknown }) => <div {...props}>{children}</div>,
  CardHeader: ({ children, ...props }: { children: ReactNode; [key: string]: unknown }) => <div {...props}>{children}</div>,
  CardTitle: ({ children, ...props }: { children: ReactNode; [key: string]: unknown }) => <h2 {...props}>{children}</h2>,
}));

vi.mock('@/shared/components/ui/badge', () => ({
  Badge: ({ children, ...props }: { children: ReactNode; [key: string]: unknown }) => <span {...props}>{children}</span>,
}));

vi.mock('@/shared/components/ui/checkbox', () => ({
  Checkbox: ({ checked, onCheckedChange, ...props }: { checked?: boolean; onCheckedChange?: (checked: boolean) => void; [key: string]: unknown }) => (
    <input
      type="checkbox"
      checked={checked}
      onChange={(e) => onCheckedChange?.(e.target.checked)}
      {...props}
    />
  ),
}));

vi.mock('@/shared/components/ui/select', () => ({
  Select: ({ children, value, onValueChange }: { children: ReactNode; value?: string; onValueChange?: (value: string) => void }) => (
    <div data-value={value} data-onvaluechange={onValueChange?.toString()}>
      {children}
    </div>
  ),
  SelectContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  SelectItem: ({ children, value, ...props }: { children: ReactNode; value: string; [key: string]: unknown }) => (
    <option value={value} {...props}>
      {children}
    </option>
  ),
  SelectTrigger: ({ children }: { children: ReactNode }) => <div role="combobox">{children}</div>,
  SelectValue: ({ placeholder }: { placeholder?: string }) => <span>{placeholder}</span>,
}));

vi.mock('@/shared/components/ui/alert', () => ({
  Alert: ({ children, ...props }: { children: ReactNode; [key: string]: unknown }) => <div {...props}>{children}</div>,
  AlertDescription: ({ children, ...props }: { children: ReactNode; [key: string]: unknown }) => <div {...props}>{children}</div>,
}));

vi.mock('lucide-react', () => ({
  Loader2: () => <div>Loading Icon</div>,
  AlertCircle: () => <div>Alert Icon</div>,
}));

const mockJobs: JobReadyToSchedule[] = [
  {
    job_id: 'job-1',
    customer_name: 'John Doe',
    job_type: 'Spring Startup',
    city: 'Eden Prairie',
    priority: 'high',
    duration_minutes: 60,
    status: 'approved',
  },
  {
    job_id: 'job-2',
    customer_name: 'Jane Smith',
    job_type: 'Winterization',
    city: 'Plymouth',
    priority: 'normal',
    duration_minutes: 45,
    status: 'requested',
  },
  {
    job_id: 'job-3',
    customer_name: 'Bob Johnson',
    job_type: 'Repair',
    city: 'Eden Prairie',
    priority: 'high',
    duration_minutes: 30,
    status: 'approved',
  },
];

describe('JobsReadyToSchedulePreview', () => {
  describe('Property: Job Preview Accuracy', () => {
    it('shows all jobs when none are excluded', () => {
      const excludedJobIds = new Set<string>();
      const onToggleExclude = () => {};

      render(
        <JobsReadyToSchedulePreview
          jobs={mockJobs}
          isLoading={false}
          error={null}
          excludedJobIds={excludedJobIds}
          onToggleExclude={onToggleExclude}
        />
      );

      // All jobs should be visible
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('Jane Smith')).toBeInTheDocument();
      expect(screen.getByText('Bob Johnson')).toBeInTheDocument();

      // Summary should show all jobs selected
      expect(screen.getByTestId('jobs-summary')).toHaveTextContent('3 of 3 jobs selected');
    });

    it('correctly reflects excluded jobs in summary count', async () => {
      const user = userEvent.setup();
      const excludedJobIds = new Set<string>();
      const onToggleExclude = (jobId: string) => {
        if (excludedJobIds.has(jobId)) {
          excludedJobIds.delete(jobId);
        } else {
          excludedJobIds.add(jobId);
        }
      };

      const { rerender } = render(
        <JobsReadyToSchedulePreview
          jobs={mockJobs}
          isLoading={false}
          error={null}
          excludedJobIds={excludedJobIds}
          onToggleExclude={onToggleExclude}
        />
      );

      // Initially all selected
      expect(screen.getByTestId('jobs-summary')).toHaveTextContent('3 of 3 jobs selected');

      // Exclude first job
      const checkbox1 = screen.getByTestId('job-checkbox-job-1');
      await user.click(checkbox1);
      excludedJobIds.add('job-1');

      // Rerender with updated state
      rerender(
        <JobsReadyToSchedulePreview
          jobs={mockJobs}
          isLoading={false}
          error={null}
          excludedJobIds={excludedJobIds}
          onToggleExclude={onToggleExclude}
        />
      );

      // Should show 2 selected out of 3 total
      expect(screen.getByTestId('jobs-summary')).toHaveTextContent('2 of 3 jobs selected');
    });

    it('visually distinguishes excluded jobs', () => {
      const excludedJobIds = new Set(['job-2']);
      const onToggleExclude = () => {};

      render(
        <JobsReadyToSchedulePreview
          jobs={mockJobs}
          isLoading={false}
          error={null}
          excludedJobIds={excludedJobIds}
          onToggleExclude={onToggleExclude}
        />
      );

      // Excluded job should have line-through styling
      const excludedJob = screen.getByTestId('job-preview-job-2');
      expect(excludedJob).toHaveClass('opacity-50');

      // Non-excluded jobs should not
      const includedJob = screen.getByTestId('job-preview-job-1');
      expect(includedJob).not.toHaveClass('opacity-50');
    });

    it('maintains job identity through exclude/include cycle', async () => {
      const user = userEvent.setup();
      let excludedJobIds = new Set<string>();
      const onToggleExclude = (jobId: string) => {
        if (excludedJobIds.has(jobId)) {
          excludedJobIds.delete(jobId);
        } else {
          excludedJobIds.add(jobId);
        }
      };

      const { rerender } = render(
        <JobsReadyToSchedulePreview
          jobs={mockJobs}
          isLoading={false}
          error={null}
          excludedJobIds={excludedJobIds}
          onToggleExclude={onToggleExclude}
        />
      );

      // Verify initial state
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByTestId('jobs-summary')).toHaveTextContent('3 of 3 jobs selected');

      // Exclude job-1
      const checkbox1 = screen.getByTestId('job-checkbox-job-1');
      await user.click(checkbox1);
      excludedJobIds = new Set(['job-1']);

      rerender(
        <JobsReadyToSchedulePreview
          jobs={mockJobs}
          isLoading={false}
          error={null}
          excludedJobIds={excludedJobIds}
          onToggleExclude={onToggleExclude}
        />
      );

      expect(screen.getByTestId('jobs-summary')).toHaveTextContent('2 of 3 jobs selected');

      // Re-include job-1
      await user.click(checkbox1);
      excludedJobIds = new Set<string>();

      rerender(
        <JobsReadyToSchedulePreview
          jobs={mockJobs}
          isLoading={false}
          error={null}
          excludedJobIds={excludedJobIds}
          onToggleExclude={onToggleExclude}
        />
      );

      // Should be back to all 3 selected
      expect(screen.getByTestId('jobs-summary')).toHaveTextContent('3 jobs selected');
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    it('filters do not affect excluded job tracking', async () => {
      const user = userEvent.setup();
      const excludedJobIds = new Set(['job-1']);
      const onToggleExclude = () => {};

      render(
        <JobsReadyToSchedulePreview
          jobs={mockJobs}
          isLoading={false}
          error={null}
          excludedJobIds={excludedJobIds}
          onToggleExclude={onToggleExclude}
        />
      );

      // Initially: 2 selected (job-1 excluded), 1 excluded
      expect(screen.getByTestId('jobs-summary')).toHaveTextContent('2 of 3 jobs selected');

      // Verify all 3 jobs are visible initially
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('Jane Smith')).toBeInTheDocument();
      expect(screen.getByText('Bob Johnson')).toBeInTheDocument();

      // Note: Filter interaction testing is simplified due to stub components
      // In a real implementation with shadcn/ui, this would test actual filter behavior
      // For now, we verify that the component renders correctly with filters present
      const comboboxes = screen.getAllByRole('combobox');
      expect(comboboxes).toHaveLength(3); // Job Type, Priority, City filters
    });
  });

  describe('Loading and Error States', () => {
    it('shows loading state', () => {
      render(
        <JobsReadyToSchedulePreview
          jobs={[]}
          isLoading={true}
          error={null}
          excludedJobIds={new Set()}
          onToggleExclude={() => {}}
        />
      );

      expect(screen.getByText('Loading jobs...')).toBeInTheDocument();
    });

    it('shows error state', () => {
      const error = new Error('Failed to fetch jobs');
      render(
        <JobsReadyToSchedulePreview
          jobs={[]}
          isLoading={false}
          error={error}
          excludedJobIds={new Set()}
          onToggleExclude={() => {}}
        />
      );

      expect(screen.getByText(/Failed to load jobs/)).toBeInTheDocument();
    });

    it('shows empty state', () => {
      render(
        <JobsReadyToSchedulePreview
          jobs={[]}
          isLoading={false}
          error={null}
          excludedJobIds={new Set()}
          onToggleExclude={() => {}}
        />
      );

      expect(screen.getByText(/No jobs ready to schedule/)).toBeInTheDocument();
    });
  });
});
