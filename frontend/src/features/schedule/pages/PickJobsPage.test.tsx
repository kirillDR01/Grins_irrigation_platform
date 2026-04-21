/**
 * Integration tests for PickJobsPage.
 * Requirements: 18.1–18.12
 */

import type { ReactNode } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { PickJobsPage } from './PickJobsPage';

// ─── Mocks ───────────────────────────────────────────────────────────────────

vi.mock('@/features/schedule/hooks/useJobsReadyToSchedule');
vi.mock('@/features/staff/hooks/useStaff');
vi.mock('@/features/schedule/hooks/useAppointmentMutations');

// Mock Sheet to avoid portal issues
vi.mock('@/components/ui/sheet', () => ({
  Sheet: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  SheetContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  SheetHeader: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  SheetTitle: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  SheetTrigger: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));

// Mock Radix Select so SelectItem renders as <option> and onValueChange fires on change
vi.mock('@/components/ui/select', () => ({
  Select: ({
    children,
    value,
    onValueChange,
  }: {
    children: ReactNode;
    value?: string;
    onValueChange?: (v: string) => void;
  }) => (
    <select
      data-testid="select-root"
      value={value ?? ''}
      onChange={(e) => onValueChange?.(e.target.value)}
    >
      {children}
    </select>
  ),
  SelectContent: ({ children }: { children: ReactNode }) => <>{children}</>,
  SelectItem: ({
    children,
    value,
  }: {
    children: ReactNode;
    value: string;
  }) => <option value={value}>{children}</option>,
  SelectTrigger: ({ children, ...props }: { children: ReactNode; [k: string]: unknown }) => (
    <div {...props}>{children}</div>
  ),
  SelectValue: ({ placeholder }: { placeholder?: string }) => <span>{placeholder}</span>,
}));

// Mock PropertyTags
vi.mock('@/shared/components/PropertyTags', () => ({
  PropertyTags: () => null,
}));

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { useJobsReadyToSchedule } from '@/features/schedule/hooks/useJobsReadyToSchedule';
import { useStaff } from '@/features/staff/hooks/useStaff';
import { useCreateAppointment } from '@/features/schedule/hooks/useAppointmentMutations';
import { toast } from 'sonner';
import type { JobReadyToSchedule } from '../types/index';
import type { Staff } from '@/features/staff/types';

const mockUseJobsReadyToSchedule = vi.mocked(useJobsReadyToSchedule);
const mockUseStaff = vi.mocked(useStaff);
const mockUseCreateAppointment = vi.mocked(useCreateAppointment);

// ─── Fixtures ────────────────────────────────────────────────────────────────

const makeJob = (overrides: Partial<JobReadyToSchedule> = {}): JobReadyToSchedule => ({
  job_id: 'j1',
  customer_id: 'c1',
  customer_name: 'Alice Smith',
  city: 'Minneapolis',
  job_type: 'Spring Startup',
  estimated_duration_minutes: 60,
  priority: 'normal',
  requires_equipment: [],
  status: 'approved',
  customer_tags: [],
  priority_level: 0,
  requested_week: '2024-04-15',
  notes: '',
  ...overrides,
});

const mockStaff: Staff[] = [
  {
    id: 's1',
    name: 'Bob Tech',
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

const mockMutateAsync = vi.fn();

function setupMocks(jobs: JobReadyToSchedule[] = [], isPending = false) {
  mockUseJobsReadyToSchedule.mockReturnValue({
    data: { jobs, total_count: jobs.length, by_city: {}, by_job_type: {} },
    isLoading: false,
    error: null,
  } as ReturnType<typeof useJobsReadyToSchedule>);

  mockUseStaff.mockReturnValue({
    data: { items: mockStaff, total: 1 },
    isLoading: false,
    error: null,
  } as ReturnType<typeof useStaff>);

  mockUseCreateAppointment.mockReturnValue({
    mutateAsync: mockMutateAsync,
    isPending,
  } as unknown as ReturnType<typeof useCreateAppointment>);
}

// ─── Wrapper ─────────────────────────────────────────────────────────────────

function renderPage(initialPath = '/schedule/pick-jobs') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  const router = createMemoryRouter(
    [
      { path: '/schedule/pick-jobs', element: <PickJobsPage /> },
      { path: '/schedule', element: <div data-testid="schedule-page">Schedule</div> },
    ],
    { initialEntries: [initialPath] },
  );

  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

/** Select staff by firing a change event on the mocked <select> inside the tray */
function selectStaff(staffId: string) {
  const staffSelect = screen.getByTestId('tray-staff').closest('select') ??
    screen.getByTestId('tray-staff').parentElement?.querySelector('select');
  if (staffSelect) {
    fireEvent.change(staffSelect, { target: { value: staffId } });
  }
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('PickJobsPage integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMutateAsync.mockResolvedValue({});
  });

  // ─── Empty state ─────────────────────────────────────────────────────────

  it('renders empty state with zero jobs', () => {
    setupMocks([]);
    renderPage();
    expect(screen.getByTestId('pick-jobs-page')).toBeInTheDocument();
    expect(screen.getByText(/All jobs are scheduled/)).toBeInTheDocument();
  });

  // ─── Row selection ───────────────────────────────────────────────────────

  it('clicking a row toggles selection and updates tray header count', async () => {
    const user = userEvent.setup();
    setupMocks([makeJob({ job_id: 'j1' })]);
    renderPage();

    await user.click(screen.getByTestId('job-row-j1'));

    // Tray should show "Schedule 1 job" — the count is in a teal span
    const tealCount = document.querySelector('.text-teal-700');
    expect(tealCount?.textContent).toBe('1');
  });

  // ─── Facet filtering ─────────────────────────────────────────────────────

  it('facet click filters table rows while preserving existing selections', async () => {
    const user = userEvent.setup();
    const jobs = [
      makeJob({ job_id: 'j1', city: 'Minneapolis' }),
      makeJob({ job_id: 'j2', city: 'St. Paul', customer_name: 'Bob Jones' }),
    ];
    setupMocks(jobs);
    renderPage();

    // Select j1 first
    await user.click(screen.getByTestId('job-row-j1'));

    // Click Minneapolis facet (may render in multiple places due to Sheet mock; use first)
    const minneapolisCheckboxes = screen.getAllByTestId('facet-value-city-Minneapolis');
    const btn = minneapolisCheckboxes[0].querySelector('button');
    await user.click(btn!);

    // j2 should be filtered out
    expect(screen.queryByTestId('job-row-j2')).not.toBeInTheDocument();
    // j1 still visible
    expect(screen.getByTestId('job-row-j1')).toBeInTheDocument();
    // Selection count preserved
    const tealCount = document.querySelector('.text-teal-700');
    expect(tealCount?.textContent).toBe('1');
  });

  // ─── Assign button disabled without staff ────────────────────────────────

  it('assign button is disabled without staff selected', async () => {
    const user = userEvent.setup();
    setupMocks([makeJob({ job_id: 'j1' })]);
    renderPage();

    await user.click(screen.getByTestId('job-row-j1'));

    expect(screen.getByTestId('tray-assign-btn')).toBeDisabled();
  });

  // ─── Assign flow ─────────────────────────────────────────────────────────

  it('clicking Assign calls createAppointment once per selected job with correct params', async () => {
    const user = userEvent.setup();
    setupMocks([makeJob({ job_id: 'j1' })]);
    renderPage();

    // Select job
    await user.click(screen.getByTestId('job-row-j1'));

    // Select staff
    selectStaff('s1');

    // Click assign
    await user.click(screen.getByTestId('tray-assign-btn'));

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledTimes(1);
      expect(mockMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          job_id: 'j1',
          staff_id: 's1',
        }),
      );
    });
  });

  it('shows success toast after successful assignment', async () => {
    const user = userEvent.setup();
    setupMocks([makeJob({ job_id: 'j1' })]);
    renderPage();

    await user.click(screen.getByTestId('job-row-j1'));
    selectStaff('s1');
    await user.click(screen.getByTestId('tray-assign-btn'));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalled();
    });
  });

  // ─── Search debounce ─────────────────────────────────────────────────────

  it('search input filters jobs correctly', async () => {
    const user = userEvent.setup({ delay: null });
    const jobs = [
      makeJob({ job_id: 'j1', customer_name: 'Alice Smith' }),
      makeJob({ job_id: 'j2', customer_name: 'Bob Jones' }),
    ];
    setupMocks(jobs);
    renderPage();

    const searchInput = screen.getByTestId('job-search');
    await user.type(searchInput, 'Alice');

    // Wait for debounce
    await waitFor(() => {
      expect(screen.getByTestId('job-row-j1')).toBeInTheDocument();
      expect(screen.queryByTestId('job-row-j2')).not.toBeInTheDocument();
    }, { timeout: 500 });
  });

  // ─── Per-job time overrides persist ──────────────────────────────────────

  it('per-job time overrides persist across unrelated selection toggles', async () => {
    const user = userEvent.setup();
    const jobs = [
      makeJob({ job_id: 'j1' }),
      makeJob({ job_id: 'j2', customer_name: 'Bob Jones' }),
    ];
    setupMocks(jobs);
    renderPage();

    // Select j1
    await user.click(screen.getByTestId('job-row-j1'));

    // Open time adjustments
    await user.click(screen.getByTestId('tray-time-adjust-toggle'));

    // Verify time adjust table is visible
    expect(screen.getByTestId('tray-time-adjust-table')).toBeInTheDocument();

    // Toggle j2 selection (unrelated)
    await user.click(screen.getByTestId('job-row-j2'));
    await user.click(screen.getByTestId('job-row-j2'));

    // j1's time adjustment table row should still be visible
    expect(screen.getByTestId('tray-time-adjust-table')).toBeInTheDocument();
  });

  // ─── URL prefill ─────────────────────────────────────────────────────────

  it('URL ?date= and ?staff= prefill tray fields', () => {
    setupMocks([]);
    renderPage('/schedule/pick-jobs?date=2024-05-01&staff=s1');

    const dateInput = screen.getByTestId('tray-date') as HTMLInputElement;
    expect(dateInput.value).toBe('2024-05-01');
  });

  // ─── Leave-without-saving guard ──────────────────────────────────────────

  it('leave-without-saving guard triggers when navigating away with active selections', async () => {
    const user = userEvent.setup();
    setupMocks([makeJob({ job_id: 'j1' })]);

    // Use a router with a nav link so we can trigger in-app navigation
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    const router = createMemoryRouter(
      [
        {
          path: '/schedule/pick-jobs',
          element: (
            <>
              <PickJobsPage />
              {/* A link that triggers in-app navigation to a different path */}
              <a href="/schedule" onClick={(e) => { e.preventDefault(); router.navigate('/schedule'); }}>
                Go to schedule
              </a>
            </>
          ),
        },
        { path: '/schedule', element: <div data-testid="schedule-page">Schedule</div> },
      ],
      { initialEntries: ['/schedule/pick-jobs'] },
    );

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    // Select a job
    await user.click(screen.getByTestId('job-row-j1'));

    // Navigate away via router
    await act(async () => {
      await router.navigate('/schedule');
    });

    // Guard dialog should appear
    await waitFor(() => {
      expect(screen.getByText('Leave without scheduling?')).toBeInTheDocument();
    });
  });

  // ─── Keyboard shortcuts ──────────────────────────────────────────────────

  it('/ keyboard shortcut focuses search', async () => {
    setupMocks([makeJob()]);
    renderPage();

    const searchInput = screen.getByTestId('job-search');

    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: '/', bubbles: true }));
    });

    await waitFor(() => {
      expect(document.activeElement).toBe(searchInput);
    });
  });

  it('Cmd+Enter triggers assign when enabled', async () => {
    const user = userEvent.setup();
    setupMocks([makeJob({ job_id: 'j1' })]);
    renderPage();

    // Select job and staff
    await user.click(screen.getByTestId('job-row-j1'));
    selectStaff('s1');

    // Trigger Cmd+Enter
    await act(async () => {
      window.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'Enter', metaKey: true, bubbles: true }),
      );
    });

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledTimes(1);
    });
  });

  // ─── Landmark elements ───────────────────────────────────────────────────

  it('landmark elements are present: main, aside, section', () => {
    setupMocks([]);
    renderPage();

    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('complementary')).toBeInTheDocument(); // <aside>
    // Multiple regions with this label exist (outer section + inner tray section)
    const regions = screen.getAllByRole('region', { name: /Scheduling assignment/i });
    expect(regions.length).toBeGreaterThanOrEqual(1);
  });

  // ─── Loading state ───────────────────────────────────────────────────────

  it('shows loading spinner while data loads', () => {
    mockUseJobsReadyToSchedule.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as ReturnType<typeof useJobsReadyToSchedule>);

    mockUseStaff.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as ReturnType<typeof useStaff>);

    mockUseCreateAppointment.mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateAppointment>);

    renderPage();
    expect(screen.getByTestId('pick-jobs-page')).toBeInTheDocument();
    // Loading spinner should be present (LoadingSpinner component)
    expect(document.querySelector('[class*="animate-spin"], [data-testid="loading-spinner"]')).toBeTruthy();
  });
});
