# Design Document: Admin Dashboard (Phase 3)

## Introduction

This document provides the technical design for the Admin Dashboard feature of Grin's Irrigation Platform. It defines the frontend architecture, backend additions (Appointment model), API endpoints, component specifications, and implementation patterns that will fulfill the requirements specified in requirements.md.

## Design Overview

Phase 3 introduces a React-based Admin Dashboard following Vertical Slice Architecture (VSA) patterns. The frontend integrates with the existing FastAPI backend and adds new Appointment management capabilities.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ADMIN DASHBOARD (React SPA)                          │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Dashboard   │  │  Customers   │  │    Jobs      │  │   Schedule   │    │
│  │   Feature    │  │   Feature    │  │   Feature    │  │   Feature    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│         │                  │                  │                  │          │
│         └──────────────────┴──────────────────┴──────────────────┘          │
│                                    │                                         │
│                          ┌─────────┴─────────┐                              │
│                          │   TanStack Query  │                              │
│                          │   (Server State)  │                              │
│                          └─────────┬─────────┘                              │
│                                    │                                         │
│                          ┌─────────┴─────────┐                              │
│                          │   Axios Client    │                              │
│                          │  (API Integration)│                              │
│                          └─────────┬─────────┘                              │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND                                      │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Customers   │  │    Jobs      │  │    Staff     │  │ Appointments │    │
│  │     API      │  │     API      │  │     API      │  │     API      │    │
│  │  (Phase 1)   │  │  (Phase 2)   │  │  (Phase 2)   │  │  (Phase 3)   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```



## Technology Stack

### Frontend Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Framework** | React 18 + TypeScript | Type safety, component ecosystem |
| **Build Tool** | Vite | Fast builds, HMR, PWA plugin ready |
| **State Management** | TanStack Query v5 | Server state, caching, offline support |
| **Styling** | Tailwind CSS + shadcn/ui | Rapid development, consistent design |
| **Forms** | React Hook Form + Zod | Type-safe validation, performance |
| **Calendar** | FullCalendar | Industry standard, React integration |
| **Tables** | TanStack Table | Sorting, filtering, pagination |
| **Routing** | React Router v6 | Standard routing solution |
| **HTTP Client** | Axios | Interceptors, error handling |
| **Icons** | Lucide React | Consistent icon set |
| **Date Handling** | date-fns | Lightweight date utilities |

### Backend Additions

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Appointment Model** | SQLAlchemy 2.0 | Async support, type hints |
| **Appointment API** | FastAPI | Consistent with existing APIs |
| **Validation** | Pydantic v2 | Schema validation |

---

## Frontend Architecture (Vertical Slice)

### Directory Structure

```
frontend/
├── public/
│   ├── manifest.json           # PWA manifest (future)
│   └── icons/                  # App icons
├── src/
│   ├── main.tsx                # Entry point
│   ├── App.tsx                 # Root component with providers
│   ├── vite-env.d.ts           # Vite types
│   │
│   ├── core/                   # Foundation (exists before features)
│   │   ├── api/
│   │   │   ├── client.ts       # Axios instance with interceptors
│   │   │   └── types.ts        # API response types
│   │   ├── config/
│   │   │   └── index.ts        # Environment configuration
│   │   ├── providers/
│   │   │   ├── QueryProvider.tsx    # TanStack Query setup
│   │   │   └── ThemeProvider.tsx    # Theme context
│   │   └── router/
│   │       └── index.tsx       # Route definitions
│   │
│   ├── shared/                 # Cross-feature utilities (3+ features)
│   │   ├── components/
│   │   │   ├── ui/             # shadcn/ui components
│   │   │   │   ├── button.tsx
│   │   │   │   ├── card.tsx
│   │   │   │   ├── dialog.tsx
│   │   │   │   ├── input.tsx
│   │   │   │   ├── table.tsx
│   │   │   │   ├── select.tsx
│   │   │   │   ├── badge.tsx
│   │   │   │   ├── toast.tsx
│   │   │   │   ├── form.tsx
│   │   │   │   ├── calendar.tsx
│   │   │   │   ├── popover.tsx
│   │   │   │   ├── skeleton.tsx
│   │   │   │   └── tabs.tsx
│   │   │   ├── Layout.tsx      # Main layout with sidebar
│   │   │   ├── PageHeader.tsx  # Consistent page headers
│   │   │   ├── StatusBadge.tsx # Status indicators
│   │   │   ├── LoadingSpinner.tsx
│   │   │   ├── ErrorBoundary.tsx
│   │   │   └── ConfirmDialog.tsx
│   │   ├── hooks/
│   │   │   ├── useDebounce.ts
│   │   │   ├── usePagination.ts
│   │   │   └── useToast.ts
│   │   └── utils/
│   │       ├── formatters.ts   # Date, currency, phone formatting
│   │       └── validators.ts   # Zod schemas
│   │
│   └── features/               # Feature slices (self-contained)
│       ├── dashboard/
│       │   ├── components/
│       │   │   ├── DashboardPage.tsx
│       │   │   ├── MetricsCard.tsx
│       │   │   └── RecentActivity.tsx
│       │   ├── hooks/
│       │   │   └── useDashboardMetrics.ts
│       │   ├── api/
│       │   │   └── dashboardApi.ts
│       │   ├── types/
│       │   │   └── index.ts
│       │   └── index.ts        # Public exports
│       │
│       ├── customers/
│       │   ├── components/
│       │   │   ├── CustomerList.tsx
│       │   │   ├── CustomerDetail.tsx
│       │   │   ├── CustomerForm.tsx
│       │   │   └── CustomerSearch.tsx
│       │   ├── hooks/
│       │   │   ├── useCustomers.ts
│       │   │   ├── useCustomer.ts
│       │   │   ├── useCreateCustomer.ts
│       │   │   └── useUpdateCustomer.ts
│       │   ├── api/
│       │   │   └── customerApi.ts
│       │   ├── types/
│       │   │   └── index.ts
│       │   └── index.ts
│       │
│       ├── jobs/
│       │   ├── components/
│       │   │   ├── JobList.tsx
│       │   │   ├── JobDetail.tsx
│       │   │   ├── JobForm.tsx
│       │   │   ├── JobStatusBadge.tsx
│       │   │   └── JobStatusDropdown.tsx
│       │   ├── hooks/
│       │   │   ├── useJobs.ts
│       │   │   ├── useJob.ts
│       │   │   ├── useCreateJob.ts
│       │   │   └── useUpdateJobStatus.ts
│       │   ├── api/
│       │   │   └── jobApi.ts
│       │   ├── types/
│       │   │   └── index.ts
│       │   └── index.ts
│       │
│       ├── staff/
│       │   ├── components/
│       │   │   ├── StaffList.tsx
│       │   │   ├── StaffDetail.tsx
│       │   │   └── StaffAvailabilityToggle.tsx
│       │   ├── hooks/
│       │   │   ├── useStaff.ts
│       │   │   └── useUpdateStaffAvailability.ts
│       │   ├── api/
│       │   │   └── staffApi.ts
│       │   ├── types/
│       │   │   └── index.ts
│       │   └── index.ts
│       │
│       └── schedule/
│           ├── components/
│           │   ├── SchedulePage.tsx
│           │   ├── CalendarView.tsx
│           │   ├── AppointmentForm.tsx
│           │   ├── AppointmentDetail.tsx
│           │   ├── DailyScheduleView.tsx
│           │   └── StaffDailyView.tsx
│           ├── hooks/
│           │   ├── useAppointments.ts
│           │   ├── useAppointment.ts
│           │   ├── useCreateAppointment.ts
│           │   ├── useUpdateAppointment.ts
│           │   └── useDailySchedule.ts
│           ├── api/
│           │   └── appointmentApi.ts
│           ├── types/
│           │   └── index.ts
│           └── index.ts
│
├── index.html
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
├── package.json
└── README.md
```


---

## Backend: Appointment Database Schema

### appointments Table

```sql
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- References
    job_id UUID NOT NULL REFERENCES jobs(id),
    staff_id UUID NOT NULL REFERENCES staff(id),
    
    -- Scheduling
    scheduled_date DATE NOT NULL,
    time_window_start TIME NOT NULL,
    time_window_end TIME NOT NULL,
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'scheduled',
    -- scheduled, confirmed, in_progress, completed, cancelled
    
    -- Execution Tracking
    arrived_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Notes
    notes TEXT,
    
    -- Route Information (for future optimization)
    route_order INTEGER,
    estimated_arrival TIME,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_appointment_status CHECK (
        status IN ('scheduled', 'confirmed', 'in_progress', 'completed', 'cancelled')
    ),
    CONSTRAINT valid_time_window CHECK (time_window_start < time_window_end)
);

-- Indexes
CREATE INDEX idx_appointments_job ON appointments(job_id);
CREATE INDEX idx_appointments_staff ON appointments(staff_id);
CREATE INDEX idx_appointments_date ON appointments(scheduled_date);
CREATE INDEX idx_appointments_status ON appointments(status);
CREATE INDEX idx_appointments_staff_date ON appointments(staff_id, scheduled_date);
```

### Entity Relationships

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│    Customer     │       │      Job        │       │   Appointment   │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │──┐    │ id (PK)         │──┐    │ id (PK)         │
│ first_name      │  │    │ customer_id(FK) │◄─┘    │ job_id (FK)     │◄─┘
│ last_name       │  │    │ property_id(FK) │       │ staff_id (FK)   │◄─┐
│ phone           │  │    │ status          │       │ scheduled_date  │  │
│ ...             │  │    │ ...             │       │ time_window_*   │  │
└─────────────────┘  │    └─────────────────┘       │ status          │  │
                     │                              │ ...             │  │
                     │    ┌─────────────────┐       └─────────────────┘  │
                     │    │    Property     │                            │
                     │    ├─────────────────┤       ┌─────────────────┐  │
                     └───►│ id (PK)         │       │     Staff       │  │
                          │ customer_id(FK) │       ├─────────────────┤  │
                          │ address         │       │ id (PK)         │──┘
                          │ ...             │       │ name            │
                          └─────────────────┘       │ role            │
                                                    │ ...             │
                                                    └─────────────────┘
```

---

## Backend: API Endpoints

### Appointment Endpoints (8 endpoints)

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/api/v1/appointments` | Create appointment | AppointmentCreate | AppointmentResponse |
| GET | `/api/v1/appointments/{id}` | Get appointment by ID | - | AppointmentDetailResponse |
| PUT | `/api/v1/appointments/{id}` | Update appointment | AppointmentUpdate | AppointmentResponse |
| DELETE | `/api/v1/appointments/{id}` | Cancel appointment | - | 204 No Content |
| GET | `/api/v1/appointments` | List appointments | Query params | PaginatedAppointmentResponse |
| GET | `/api/v1/appointments/daily/{date}` | Get daily schedule | - | DailyScheduleResponse |
| GET | `/api/v1/appointments/staff/{staff_id}/daily/{date}` | Staff daily schedule | - | StaffDailyResponse |
| GET | `/api/v1/appointments/weekly` | Weekly overview | Query params | WeeklyScheduleResponse |

### Dashboard Endpoints (4 endpoints)

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| GET | `/api/v1/dashboard/metrics` | Get dashboard metrics | DashboardMetricsResponse |
| GET | `/api/v1/dashboard/recent-activity` | Get recent activity | RecentActivityResponse |
| GET | `/api/v1/dashboard/jobs-by-status` | Jobs count by status | JobsByStatusResponse |
| GET | `/api/v1/dashboard/today-schedule` | Today's appointments | TodayScheduleResponse |


---

## Backend: Pydantic Schemas

### Appointment Enums

```python
from enum import Enum

class AppointmentStatus(str, Enum):
    """Appointment status enumeration."""
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
```

### Appointment Schemas

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date, time
from uuid import UUID
from decimal import Decimal

class AppointmentCreate(BaseModel):
    job_id: UUID
    staff_id: UUID
    scheduled_date: date
    time_window_start: time
    time_window_end: time
    notes: Optional[str] = None
    
    @field_validator('time_window_end')
    @classmethod
    def validate_time_window(cls, v: time, info) -> time:
        start = info.data.get('time_window_start')
        if start and v <= start:
            raise ValueError('End time must be after start time')
        return v

class AppointmentUpdate(BaseModel):
    staff_id: Optional[UUID] = None
    scheduled_date: Optional[date] = None
    time_window_start: Optional[time] = None
    time_window_end: Optional[time] = None
    notes: Optional[str] = None
    status: Optional[AppointmentStatus] = None

class AppointmentResponse(BaseModel):
    id: UUID
    job_id: UUID
    staff_id: UUID
    scheduled_date: date
    time_window_start: time
    time_window_end: time
    status: AppointmentStatus
    arrived_at: Optional[datetime]
    completed_at: Optional[datetime]
    notes: Optional[str]
    route_order: Optional[int]
    estimated_arrival: Optional[time]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AppointmentDetailResponse(AppointmentResponse):
    job: 'JobResponse'
    staff: 'StaffResponse'
    customer: 'CustomerResponse'
    property: Optional['PropertyResponse']

class DailyScheduleResponse(BaseModel):
    date: date
    appointments: List[AppointmentDetailResponse]
    total_count: int

class StaffDailyResponse(BaseModel):
    staff: 'StaffResponse'
    date: date
    appointments: List[AppointmentDetailResponse]
    total_scheduled_minutes: int

class WeeklyScheduleResponse(BaseModel):
    start_date: date
    end_date: date
    days: List[DailyScheduleResponse]
    total_appointments: int
```

### Dashboard Schemas

```python
class DashboardMetricsResponse(BaseModel):
    total_customers: int
    active_customers: int
    jobs_by_status: dict[str, int]
    today_appointments: int
    available_staff: int
    total_staff: int

class RecentActivityItem(BaseModel):
    id: UUID
    type: str  # job_created, status_changed, appointment_created
    description: str
    job_id: Optional[UUID]
    customer_name: str
    timestamp: datetime

class RecentActivityResponse(BaseModel):
    items: List[RecentActivityItem]
    total: int

class JobsByStatusResponse(BaseModel):
    requested: int
    approved: int
    scheduled: int
    in_progress: int
    completed: int
    closed: int
    cancelled: int

class TodayScheduleResponse(BaseModel):
    date: date
    appointments: List[AppointmentDetailResponse]
    by_staff: dict[str, List[AppointmentDetailResponse]]
```


---

## Backend: Service Layer Design

### AppointmentService

```python
from grins_platform.log_config import LoggerMixin

class AppointmentService(LoggerMixin):
    """Service for appointment management operations."""
    
    DOMAIN = "appointment"
    
    def __init__(
        self,
        appointment_repository: AppointmentRepository,
        job_repository: JobRepository,
        staff_repository: StaffRepository,
    ):
        self.appointment_repository = appointment_repository
        self.job_repository = job_repository
        self.staff_repository = staff_repository
    
    async def create_appointment(self, data: AppointmentCreate) -> Appointment:
        """Create a new appointment and update job status."""
        self.log_started("create_appointment", job_id=str(data.job_id))
        
        # Validate job exists and is in approved status
        job = await self.job_repository.get_by_id(data.job_id)
        if not job or job.is_deleted:
            self.log_rejected("create_appointment", reason="job_not_found")
            raise JobNotFoundError(data.job_id)
        
        if job.status != JobStatus.APPROVED.value:
            self.log_rejected("create_appointment", reason="job_not_approved")
            raise InvalidJobStatusError(f"Job must be approved to schedule, current: {job.status}")
        
        # Validate staff exists and is active
        staff = await self.staff_repository.get_by_id(data.staff_id)
        if not staff or not staff.is_active:
            self.log_rejected("create_appointment", reason="staff_not_found_or_inactive")
            raise StaffNotFoundError(data.staff_id)
        
        # Create appointment
        appointment = await self.appointment_repository.create(
            **data.model_dump(),
            status=AppointmentStatus.SCHEDULED.value,
        )
        
        # Update job status to scheduled
        await self.job_repository.update(
            data.job_id,
            {"status": JobStatus.SCHEDULED.value, "scheduled_at": datetime.utcnow()}
        )
        
        self.log_completed("create_appointment", appointment_id=str(appointment.id))
        return appointment
    
    async def cancel_appointment(self, appointment_id: UUID) -> None:
        """Cancel an appointment and revert job status."""
        self.log_started("cancel_appointment", appointment_id=str(appointment_id))
        
        appointment = await self.appointment_repository.get_by_id(appointment_id)
        if not appointment:
            self.log_rejected("cancel_appointment", reason="not_found")
            raise AppointmentNotFoundError(appointment_id)
        
        if appointment.status == AppointmentStatus.CANCELLED.value:
            self.log_rejected("cancel_appointment", reason="already_cancelled")
            raise InvalidAppointmentStatusError("Appointment already cancelled")
        
        # Update appointment status
        await self.appointment_repository.update(
            appointment_id,
            {"status": AppointmentStatus.CANCELLED.value}
        )
        
        # Revert job status to approved
        await self.job_repository.update(
            appointment.job_id,
            {"status": JobStatus.APPROVED.value, "scheduled_at": None}
        )
        
        self.log_completed("cancel_appointment", appointment_id=str(appointment_id))
    
    async def get_daily_schedule(self, date: date) -> DailySchedule:
        """Get all appointments for a specific date."""
        self.log_started("get_daily_schedule", date=str(date))
        
        appointments = await self.appointment_repository.find_by_date(date)
        
        self.log_completed("get_daily_schedule", count=len(appointments))
        return DailySchedule(date=date, appointments=appointments)
    
    async def get_staff_daily_schedule(self, staff_id: UUID, date: date) -> StaffDailySchedule:
        """Get appointments for a specific staff member on a date."""
        self.log_started("get_staff_daily_schedule", staff_id=str(staff_id), date=str(date))
        
        staff = await self.staff_repository.get_by_id(staff_id)
        if not staff:
            self.log_rejected("get_staff_daily_schedule", reason="staff_not_found")
            raise StaffNotFoundError(staff_id)
        
        appointments = await self.appointment_repository.find_by_staff_and_date(staff_id, date)
        
        # Calculate total scheduled time
        total_minutes = sum(
            self._calculate_duration(a.time_window_start, a.time_window_end)
            for a in appointments
        )
        
        self.log_completed("get_staff_daily_schedule", count=len(appointments))
        return StaffDailySchedule(
            staff=staff,
            date=date,
            appointments=appointments,
            total_scheduled_minutes=total_minutes
        )
    
    def _calculate_duration(self, start: time, end: time) -> int:
        """Calculate duration in minutes between two times."""
        start_minutes = start.hour * 60 + start.minute
        end_minutes = end.hour * 60 + end.minute
        return end_minutes - start_minutes
```

### DashboardService

```python
class DashboardService(LoggerMixin):
    """Service for dashboard metrics and activity."""
    
    DOMAIN = "dashboard"
    
    def __init__(
        self,
        customer_repository: CustomerRepository,
        job_repository: JobRepository,
        staff_repository: StaffRepository,
        appointment_repository: AppointmentRepository,
    ):
        self.customer_repository = customer_repository
        self.job_repository = job_repository
        self.staff_repository = staff_repository
        self.appointment_repository = appointment_repository
    
    async def get_metrics(self) -> DashboardMetrics:
        """Get dashboard metrics."""
        self.log_started("get_metrics")
        
        # Customer counts
        total_customers = await self.customer_repository.count_all()
        active_customers = await self.customer_repository.count_active()
        
        # Jobs by status
        jobs_by_status = await self.job_repository.count_by_status()
        
        # Today's appointments
        today = date.today()
        today_appointments = await self.appointment_repository.count_by_date(today)
        
        # Staff availability
        total_staff = await self.staff_repository.count_active()
        available_staff = await self.staff_repository.count_available()
        
        self.log_completed("get_metrics")
        return DashboardMetrics(
            total_customers=total_customers,
            active_customers=active_customers,
            jobs_by_status=jobs_by_status,
            today_appointments=today_appointments,
            available_staff=available_staff,
            total_staff=total_staff,
        )
    
    async def get_recent_activity(self, limit: int = 10) -> List[ActivityItem]:
        """Get recent activity items."""
        self.log_started("get_recent_activity", limit=limit)
        
        # Get recent job status changes from history
        activities = await self.job_repository.get_recent_status_changes(limit)
        
        self.log_completed("get_recent_activity", count=len(activities))
        return activities
```


---

## Frontend: Core Infrastructure

### API Client Configuration

```typescript
// src/core/api/client.ts
import axios, { AxiosInstance, AxiosError } from 'axios';
import { ApiResponse, ApiError } from './types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Request interceptor for auth (future)
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token when implemented
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    const message = error.response?.data?.error?.message || 'An error occurred';
    return Promise.reject(new Error(message));
  }
);
```

### TanStack Query Provider

```typescript
// src/core/providers/QueryProvider.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { ReactNode } from 'react';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
});

export function QueryProvider({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

### Router Configuration

```typescript
// src/core/router/index.tsx
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { Layout } from '@/shared/components/Layout';
import { DashboardPage } from '@/features/dashboard';
import { CustomerList, CustomerDetail } from '@/features/customers';
import { JobList, JobDetail } from '@/features/jobs';
import { StaffList, StaffDetail } from '@/features/staff';
import { SchedulePage } from '@/features/schedule';

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'customers', element: <CustomerList /> },
      { path: 'customers/:id', element: <CustomerDetail /> },
      { path: 'jobs', element: <JobList /> },
      { path: 'jobs/:id', element: <JobDetail /> },
      { path: 'staff', element: <StaffList /> },
      { path: 'staff/:id', element: <StaffDetail /> },
      { path: 'schedule', element: <SchedulePage /> },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
```

---

## Frontend: Shared Components

### Layout Component

```typescript
// src/shared/components/Layout.tsx
import { Outlet, NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, Users, Briefcase, Calendar, UserCog 
} from 'lucide-react';
import { cn } from '@/shared/utils/cn';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/customers', icon: Users, label: 'Customers' },
  { to: '/jobs', icon: Briefcase, label: 'Jobs' },
  { to: '/schedule', icon: Calendar, label: 'Schedule' },
  { to: '/staff', icon: UserCog, label: 'Staff' },
];

export function Layout() {
  return (
    <div className="flex h-screen bg-gray-100" data-testid="main-layout">
      {/* Sidebar */}
      <aside className="w-64 bg-white shadow-md" data-testid="sidebar">
        <div className="p-4 border-b">
          <h1 className="text-xl font-bold text-green-600">Grin's Irrigation</h1>
        </div>
        <nav className="p-4">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              data-testid={`nav-${label.toLowerCase()}`}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-4 py-2 rounded-lg mb-1',
                  isActive
                    ? 'bg-green-100 text-green-700'
                    : 'text-gray-600 hover:bg-gray-100'
                )
              }
            >
              <Icon className="w-5 h-5" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <header className="bg-white shadow-sm p-4" data-testid="header">
          {/* Page title set by child routes */}
        </header>
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
```

### Status Badge Component

```typescript
// src/shared/components/StatusBadge.tsx
import { Badge } from '@/shared/components/ui/badge';
import { cn } from '@/shared/utils/cn';

type StatusType = 'requested' | 'approved' | 'scheduled' | 'in_progress' | 
                  'completed' | 'closed' | 'cancelled';

const statusConfig: Record<StatusType, { label: string; className: string }> = {
  requested: { label: 'Requested', className: 'bg-yellow-100 text-yellow-800' },
  approved: { label: 'Approved', className: 'bg-blue-100 text-blue-800' },
  scheduled: { label: 'Scheduled', className: 'bg-purple-100 text-purple-800' },
  in_progress: { label: 'In Progress', className: 'bg-orange-100 text-orange-800' },
  completed: { label: 'Completed', className: 'bg-green-100 text-green-800' },
  closed: { label: 'Closed', className: 'bg-gray-100 text-gray-800' },
  cancelled: { label: 'Cancelled', className: 'bg-red-100 text-red-800' },
};

interface StatusBadgeProps {
  status: StatusType;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status];
  return (
    <Badge 
      className={cn(config.className, className)}
      data-testid={`status-${status}`}
    >
      {config.label}
    </Badge>
  );
}
```


---

## Frontend: Feature Slice Patterns

### Customer Feature Example

#### Types

```typescript
// src/features/customers/types/index.ts
export interface Customer {
  id: string;
  first_name: string;
  last_name: string;
  phone: string;
  email: string | null;
  status: 'active' | 'inactive';
  is_priority: boolean;
  is_red_flag: boolean;
  is_slow_payer: boolean;
  is_new_customer: boolean;
  sms_opt_in: boolean;
  email_opt_in: boolean;
  lead_source: string | null;
  created_at: string;
  updated_at: string;
}

export interface CustomerCreate {
  first_name: string;
  last_name: string;
  phone: string;
  email?: string;
  lead_source?: string;
  sms_opt_in?: boolean;
  email_opt_in?: boolean;
}

export interface CustomerUpdate extends Partial<CustomerCreate> {
  status?: 'active' | 'inactive';
}

export interface CustomerListParams {
  page?: number;
  page_size?: number;
  search?: string;
  status?: string;
  is_priority?: boolean;
  is_red_flag?: boolean;
  is_slow_payer?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}
```

#### API Client

```typescript
// src/features/customers/api/customerApi.ts
import { apiClient } from '@/core/api/client';
import { Customer, CustomerCreate, CustomerUpdate, CustomerListParams } from '../types';
import { PaginatedResponse } from '@/core/api/types';

export const customerApi = {
  list: async (params: CustomerListParams = {}): Promise<PaginatedResponse<Customer>> => {
    const { data } = await apiClient.get('/customers', { params });
    return data;
  },

  get: async (id: string): Promise<Customer> => {
    const { data } = await apiClient.get(`/customers/${id}`);
    return data;
  },

  create: async (customer: CustomerCreate): Promise<Customer> => {
    const { data } = await apiClient.post('/customers', customer);
    return data;
  },

  update: async (id: string, customer: CustomerUpdate): Promise<Customer> => {
    const { data } = await apiClient.put(`/customers/${id}`, customer);
    return data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/customers/${id}`);
  },

  updateFlags: async (id: string, flags: Partial<Customer>): Promise<Customer> => {
    const { data } = await apiClient.put(`/customers/${id}/flags`, flags);
    return data;
  },
};
```

#### TanStack Query Hooks

```typescript
// src/features/customers/hooks/useCustomers.ts
import { useQuery } from '@tanstack/react-query';
import { customerApi } from '../api/customerApi';
import { CustomerListParams } from '../types';

export const customerKeys = {
  all: ['customers'] as const,
  lists: () => [...customerKeys.all, 'list'] as const,
  list: (params: CustomerListParams) => [...customerKeys.lists(), params] as const,
  details: () => [...customerKeys.all, 'detail'] as const,
  detail: (id: string) => [...customerKeys.details(), id] as const,
};

export function useCustomers(params: CustomerListParams = {}) {
  return useQuery({
    queryKey: customerKeys.list(params),
    queryFn: () => customerApi.list(params),
  });
}

// src/features/customers/hooks/useCustomer.ts
import { useQuery } from '@tanstack/react-query';
import { customerApi } from '../api/customerApi';
import { customerKeys } from './useCustomers';

export function useCustomer(id: string) {
  return useQuery({
    queryKey: customerKeys.detail(id),
    queryFn: () => customerApi.get(id),
    enabled: !!id,
  });
}

// src/features/customers/hooks/useCreateCustomer.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { customerApi } from '../api/customerApi';
import { customerKeys } from './useCustomers';
import { CustomerCreate } from '../types';

export function useCreateCustomer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CustomerCreate) => customerApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() });
    },
  });
}
```

#### Component Example

```typescript
// src/features/customers/components/CustomerList.tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useCustomers } from '../hooks/useCustomers';
import { useCreateCustomer } from '../hooks/useCreateCustomer';
import { CustomerForm } from './CustomerForm';
import { CustomerSearch } from './CustomerSearch';
import { Button } from '@/shared/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/components/ui/table';
import { Dialog, DialogContent, DialogTrigger } from '@/shared/components/ui/dialog';
import { Badge } from '@/shared/components/ui/badge';
import { Plus } from 'lucide-react';

export function CustomerList() {
  const [params, setParams] = useState({ page: 1, page_size: 20 });
  const [isFormOpen, setIsFormOpen] = useState(false);
  const { data, isLoading } = useCustomers(params);
  const createCustomer = useCreateCustomer();

  const handleSearch = (search: string) => {
    setParams(prev => ({ ...prev, search, page: 1 }));
  };

  const handleCreate = async (data: CustomerCreate) => {
    await createCustomer.mutateAsync(data);
    setIsFormOpen(false);
  };

  if (isLoading) return <div>Loading...</div>;

  return (
    <div data-testid="customers-page">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Customers</h1>
        <Dialog open={isFormOpen} onOpenChange={setIsFormOpen}>
          <DialogTrigger asChild>
            <Button data-testid="add-customer-btn">
              <Plus className="w-4 h-4 mr-2" />
              Add Customer
            </Button>
          </DialogTrigger>
          <DialogContent>
            <CustomerForm onSubmit={handleCreate} />
          </DialogContent>
        </Dialog>
      </div>

      <CustomerSearch onSearch={handleSearch} data-testid="customer-search" />

      <Table data-testid="customer-table">
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Phone</TableHead>
            <TableHead>Email</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Flags</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data?.items.map((customer) => (
            <TableRow 
              key={customer.id} 
              data-testid="customer-row"
              className="cursor-pointer hover:bg-gray-50"
            >
              <TableCell>
                <Link to={`/customers/${customer.id}`}>
                  {customer.first_name} {customer.last_name}
                </Link>
              </TableCell>
              <TableCell>{customer.phone}</TableCell>
              <TableCell>{customer.email || '-'}</TableCell>
              <TableCell>
                <Badge variant={customer.status === 'active' ? 'default' : 'secondary'}>
                  {customer.status}
                </Badge>
              </TableCell>
              <TableCell>
                {customer.is_priority && <Badge className="mr-1 bg-yellow-100">Priority</Badge>}
                {customer.is_red_flag && <Badge className="mr-1 bg-red-100">Red Flag</Badge>}
                {customer.is_slow_payer && <Badge className="bg-orange-100">Slow Payer</Badge>}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
```


---

## Frontend: Schedule Feature Design

### Calendar Integration with FullCalendar

```typescript
// src/features/schedule/components/CalendarView.tsx
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import { useAppointments } from '../hooks/useAppointments';
import { Appointment } from '../types';

interface CalendarViewProps {
  onEventClick: (appointment: Appointment) => void;
  onDateClick: (date: Date) => void;
}

export function CalendarView({ onEventClick, onDateClick }: CalendarViewProps) {
  const { data: appointments } = useAppointments();

  const events = appointments?.map((apt) => ({
    id: apt.id,
    title: `${apt.customer.first_name} ${apt.customer.last_name} - ${apt.job.job_type}`,
    start: `${apt.scheduled_date}T${apt.time_window_start}`,
    end: `${apt.scheduled_date}T${apt.time_window_end}`,
    backgroundColor: getStatusColor(apt.status),
    extendedProps: { appointment: apt },
  }));

  return (
    <FullCalendar
      plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
      initialView="dayGridMonth"
      headerToolbar={{
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,timeGridDay',
      }}
      events={events}
      eventClick={(info) => onEventClick(info.event.extendedProps.appointment)}
      dateClick={(info) => onDateClick(info.date)}
      height="auto"
    />
  );
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    scheduled: '#8b5cf6',
    confirmed: '#3b82f6',
    in_progress: '#f97316',
    completed: '#22c55e',
    cancelled: '#ef4444',
  };
  return colors[status] || '#6b7280';
}
```

### Appointment Form

```typescript
// src/features/schedule/components/AppointmentForm.tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useJobs } from '@/features/jobs/hooks/useJobs';
import { useStaff } from '@/features/staff/hooks/useStaff';
import { Button } from '@/shared/components/ui/button';
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from '@/shared/components/ui/form';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/components/ui/select';
import { Input } from '@/shared/components/ui/input';
import { Textarea } from '@/shared/components/ui/textarea';

const appointmentSchema = z.object({
  job_id: z.string().uuid('Please select a job'),
  staff_id: z.string().uuid('Please select a staff member'),
  scheduled_date: z.string().min(1, 'Date is required'),
  time_window_start: z.string().min(1, 'Start time is required'),
  time_window_end: z.string().min(1, 'End time is required'),
  notes: z.string().optional(),
}).refine((data) => data.time_window_end > data.time_window_start, {
  message: 'End time must be after start time',
  path: ['time_window_end'],
});

type AppointmentFormData = z.infer<typeof appointmentSchema>;

interface AppointmentFormProps {
  onSubmit: (data: AppointmentFormData) => Promise<void>;
  defaultDate?: string;
}

export function AppointmentForm({ onSubmit, defaultDate }: AppointmentFormProps) {
  const { data: jobs } = useJobs({ status: 'approved' });
  const { data: staff } = useStaff({ is_available: true });

  const form = useForm<AppointmentFormData>({
    resolver: zodResolver(appointmentSchema),
    defaultValues: {
      scheduled_date: defaultDate || '',
      time_window_start: '09:00',
      time_window_end: '11:00',
    },
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" data-testid="appointment-form">
        <FormField
          control={form.control}
          name="job_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Job</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger data-testid="job-select">
                    <SelectValue placeholder="Select a job" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {jobs?.items.map((job) => (
                    <SelectItem key={job.id} value={job.id} data-testid="job-option">
                      {job.job_type} - {job.customer?.first_name} {job.customer?.last_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="staff_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Assign Staff</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger data-testid="staff-select">
                    <SelectValue placeholder="Select staff member" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {staff?.items.map((s) => (
                    <SelectItem key={s.id} value={s.id} data-testid="staff-option">
                      {s.name} ({s.role})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="scheduled_date"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Date</FormLabel>
              <FormControl>
                <Input type="date" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="time_window_start"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Start Time</FormLabel>
                <FormControl>
                  <Input type="time" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="time_window_end"
            render={({ field }) => (
              <FormItem>
                <FormLabel>End Time</FormLabel>
                <FormControl>
                  <Input type="time" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="notes"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Notes</FormLabel>
              <FormControl>
                <Textarea {...field} placeholder="Optional notes..." />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" className="w-full" data-testid="submit-btn">
          Create Appointment
        </Button>
      </form>
    </Form>
  );
}
```


---

## Error Handling

### Backend Exceptions

```python
class AppointmentError(Exception):
    """Base exception for appointment operations."""
    pass

class AppointmentNotFoundError(AppointmentError):
    """Raised when appointment is not found."""
    def __init__(self, appointment_id: UUID):
        self.appointment_id = appointment_id
        super().__init__(f"Appointment not found: {appointment_id}")

class InvalidAppointmentStatusError(AppointmentError):
    """Raised when appointment status transition is invalid."""
    def __init__(self, message: str):
        super().__init__(message)

class InvalidJobStatusError(AppointmentError):
    """Raised when job is not in valid status for scheduling."""
    def __init__(self, message: str):
        super().__init__(message)

class StaffNotAvailableError(AppointmentError):
    """Raised when staff is not available for scheduling."""
    def __init__(self, staff_id: UUID, date: date):
        self.staff_id = staff_id
        self.date = date
        super().__init__(f"Staff {staff_id} not available on {date}")
```

### Frontend Error Handling

```typescript
// src/shared/hooks/useToast.ts
import { toast } from '@/shared/components/ui/toast';

export function useApiError() {
  const handleError = (error: Error) => {
    toast({
      title: 'Error',
      description: error.message || 'An unexpected error occurred',
      variant: 'destructive',
    });
  };

  return { handleError };
}

// Usage in mutations
const createAppointment = useCreateAppointment();
const { handleError } = useApiError();

const handleSubmit = async (data: AppointmentCreate) => {
  try {
    await createAppointment.mutateAsync(data);
    toast({ title: 'Success', description: 'Appointment created' });
  } catch (error) {
    handleError(error as Error);
  }
};
```

---

## Testing Strategy

### Backend Tests

#### Unit Tests
- Test AppointmentService methods with mocked repositories
- Test DashboardService metrics calculation
- Test Pydantic schema validation
- Test time window validation

#### Integration Tests
- Test full appointment CRUD workflow
- Test appointment creation updates job status
- Test appointment cancellation reverts job status
- Test daily schedule queries

#### Property-Based Tests
- Test time window validation with various inputs
- Test appointment status transitions

### Frontend Tests

#### Component Tests (Vitest + React Testing Library)
- Test CustomerList renders data correctly
- Test CustomerForm validation
- Test JobStatusBadge displays correct colors
- Test CalendarView renders events

#### Integration Tests
- Test customer CRUD flow
- Test job status update flow
- Test appointment creation flow

### Agent-Browser Validation Tests

User journey validation scripts for each feature (see Agent-Browser Integration section).

---

## Correctness Properties

### Property 1: Appointment-Job Status Sync
**Validates: Requirement 7.1.3**
- When an appointment is created for job J, J.status must become "scheduled"
- When an appointment is cancelled for job J, J.status must revert to "approved"

### Property 2: Time Window Validity
**Validates: Requirement 5.2.5**
- For any appointment A, A.time_window_start < A.time_window_end

### Property 3: Job Scheduling Prerequisite
**Validates: Requirement 7.1.5**
- An appointment can only be created for a job with status "approved"

### Property 4: Staff Active Requirement
**Validates: Requirement 7.1.6**
- An appointment can only be created with a staff member where is_active = true

### Property 5: Single Active Appointment Per Job
**Validates: Requirement 5.2.2**
- For any job J, at most one appointment A where A.job_id = J.id and A.status != "cancelled"

### Property 6: Dashboard Metrics Consistency
**Validates: Requirement 1.1**
- Dashboard total_customers equals count of customers where is_deleted = false
- Dashboard jobs_by_status sums equal total non-deleted jobs


---

## Agent-Browser Integration for UI Validation

### Overview

Agent-browser provides automated UI validation during development. Each feature must pass user journey validation before being considered complete.

### Installation

```bash
npm install -g agent-browser
agent-browser install
```

### Validation Scripts

#### Layout Validation Script

```bash
#!/bin/bash
# scripts/validate-layout.sh

echo "🧪 Core Layout User Journey Test"
echo "Scenario: Viktor opens the dashboard for the first time"

agent-browser open http://localhost:5173
agent-browser wait --load networkidle

# Step 1: Dashboard loads
echo "Step 1: Dashboard loads correctly"
agent-browser is visible "[data-testid='main-layout']" && echo "  ✓ Main layout visible"
agent-browser is visible "[data-testid='sidebar']" && echo "  ✓ Sidebar visible"
agent-browser is visible "[data-testid='header']" && echo "  ✓ Header visible"

# Step 2: Navigation works
echo "Step 2: Navigation links work"
agent-browser click "[data-testid='nav-customers']"
agent-browser wait --url "**/customers"
echo "  ✓ Customers navigation works"

agent-browser click "[data-testid='nav-jobs']"
agent-browser wait --url "**/jobs"
echo "  ✓ Jobs navigation works"

agent-browser click "[data-testid='nav-schedule']"
agent-browser wait --url "**/schedule"
echo "  ✓ Schedule navigation works"

agent-browser close
echo "✅ Layout Validation PASSED!"
```

#### Customer CRUD Validation Script

```bash
#!/bin/bash
# scripts/validate-customers.sh

echo "🧪 Customer Feature User Journey Test"
echo "Scenario: Viktor adds a new customer and views their details"

agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle

# Step 1: View customer list
echo "Step 1: Viktor sees the customer list"
agent-browser is visible "[data-testid='customer-table']" && echo "  ✓ Customer table visible"
agent-browser is visible "[data-testid='add-customer-btn']" && echo "  ✓ Add button visible"

# Step 2: Add new customer
echo "Step 2: Viktor clicks 'Add Customer' and fills the form"
agent-browser click "[data-testid='add-customer-btn']"
agent-browser wait "[data-testid='customer-form']"
agent-browser fill "[name='firstName']" "John"
agent-browser fill "[name='lastName']" "Smith"
agent-browser fill "[name='phone']" "6125551234"
agent-browser fill "[name='email']" "john.smith@example.com"
echo "  ✓ Form filled out"

# Step 3: Submit and verify
echo "Step 3: Viktor submits the form"
agent-browser click "[data-testid='submit-btn']"
agent-browser wait --text "Customer created" --timeout 5000
echo "  ✓ Success message shown"

# Step 4: View customer in list
echo "Step 4: Viktor sees the new customer in the list"
agent-browser wait "[data-testid='customer-row']"
echo "  ✓ Customer appears in list"

agent-browser close
echo "✅ Customer Validation PASSED!"
```

#### Jobs Validation Script

```bash
#!/bin/bash
# scripts/validate-jobs.sh

echo "🧪 Jobs Feature User Journey Test"
echo "Scenario: Viktor creates a job and updates its status"

agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle

# Step 1: View jobs list
echo "Step 1: Viktor sees the jobs list"
agent-browser is visible "[data-testid='job-table']" && echo "  ✓ Job table visible"
agent-browser is visible "[data-testid='add-job-btn']" && echo "  ✓ Add job button visible"
agent-browser is visible "[data-testid='status-filter']" && echo "  ✓ Status filter visible"

# Step 2: Create new job
echo "Step 2: Viktor creates a new job"
agent-browser click "[data-testid='add-job-btn']"
agent-browser wait "[data-testid='job-form']"
agent-browser click "[data-testid='customer-select']"
agent-browser click "[data-testid='customer-option']:first-child"
agent-browser click "[data-testid='service-select']"
agent-browser click "[data-testid='service-option']:first-child"
agent-browser click "[data-testid='submit-btn']"
agent-browser wait --text "Job created"
echo "  ✓ Job created successfully"

# Step 3: Update job status
echo "Step 3: Viktor updates the job status"
agent-browser click "[data-testid='job-row']:first-child"
agent-browser wait "[data-testid='job-detail']"
agent-browser click "[data-testid='status-dropdown']"
agent-browser click "[data-testid='status-approved']"
agent-browser wait --text "Status updated"
echo "  ✓ Status updated to 'approved'"

agent-browser close
echo "✅ Jobs Validation PASSED!"
```

#### Schedule Validation Script

```bash
#!/bin/bash
# scripts/validate-schedule.sh

echo "🧪 Schedule Feature User Journey Test"
echo "Scenario: Viktor schedules an appointment for a job"

agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle

# Step 1: View calendar
echo "Step 1: Viktor sees the calendar"
agent-browser is visible ".fc-daygrid" && echo "  ✓ Calendar grid visible"
agent-browser is visible "[data-testid='create-appointment-btn']" && echo "  ✓ Create button visible"

# Step 2: Create appointment
echo "Step 2: Viktor creates a new appointment"
agent-browser click "[data-testid='create-appointment-btn']"
agent-browser wait "[data-testid='appointment-form']"
agent-browser click "[data-testid='job-select']"
agent-browser click "[data-testid='job-option']:first-child"
agent-browser click "[data-testid='staff-select']"
agent-browser click "[data-testid='staff-option']:first-child"
agent-browser fill "[name='scheduled_date']" "2025-01-25"
agent-browser fill "[name='time_window_start']" "09:00"
agent-browser fill "[name='time_window_end']" "11:00"
agent-browser click "[data-testid='submit-btn']"
agent-browser wait --text "Appointment created"
echo "  ✓ Appointment created successfully"

# Step 3: View appointment on calendar
echo "Step 3: Viktor sees the appointment on the calendar"
agent-browser is visible ".fc-event" && echo "  ✓ Appointment event visible"

agent-browser close
echo "✅ Schedule Validation PASSED!"
```

### Master Validation Script

```bash
#!/bin/bash
# scripts/validate-all.sh

set -e

echo "🚀 Running ALL User Journey Validations"
echo "========================================"

# Check frontend is running
if ! curl -s http://localhost:5173 > /dev/null; then
    echo "❌ Frontend not running!"
    echo "Start with: cd frontend && npm run dev"
    exit 1
fi

echo "✅ Frontend is running"

bash scripts/validate-layout.sh
bash scripts/validate-customers.sh
bash scripts/validate-jobs.sh
bash scripts/validate-schedule.sh

echo "========================================"
echo "🎉 ALL VALIDATIONS PASSED!"
```

### Test Data IDs Convention

| Component | Test ID Pattern | Example |
|-----------|-----------------|---------|
| Page containers | `{feature}-page` | `customers-page` |
| Tables | `{feature}-table` | `customer-table` |
| Table rows | `{feature}-row` | `customer-row` |
| Forms | `{feature}-form` | `customer-form` |
| Buttons | `{action}-{feature}-btn` | `add-customer-btn` |
| Inputs | Form field `name` attribute | `name="firstName"` |
| Status badges | `status-{status}` | `status-scheduled` |
| Select triggers | `{feature}-select` | `customer-select` |
| Select options | `{feature}-option` | `customer-option` |


---

## Kiro Integration Strategy

### Current Kiro Usage Summary

| Category | Count | Details |
|----------|-------|---------|
| **Steering Documents** | 14 | product.md, tech.md, structure.md, code-standards.md, etc. |
| **Custom Prompts** | 37+ | @implement-service, @implement-api, @quality-check, etc. |
| **Custom Agents** | 7 | service-layer, api-layer, repository-layer, test-specialist, etc. |
| **Hooks** | 6 | auto-lint, auto-typecheck, test-on-complete, etc. |
| **Specs** | 2 | customer-management, field-operations |

### New Kiro Items for Phase 3

#### 1. New Custom Agents (2 agents)

**Frontend Agent** (`.kiro/agents/frontend-agent.json`):
```json
{
  "name": "frontend-agent",
  "description": "Specialized agent for React + TypeScript frontend development",
  "prompt": "You are a frontend development specialist for the Grin's Irrigation Platform. You focus on:\n\n1. React 18 with TypeScript and functional components\n2. TanStack Query for server state management\n3. Tailwind CSS + shadcn/ui for styling\n4. Vertical Slice Architecture patterns\n5. Type-safe API integration\n\nAlways follow the patterns in frontend-patterns.md and ensure accessibility compliance.",
  "tools": ["read", "write", "shell"],
  "allowedTools": ["read", "write", "shell:npm", "shell:pnpm"],
  "resources": [
    "file://.kiro/steering/frontend-patterns.md",
    "file://.kiro/steering/vertical-slice-setup-guide-full.md",
    "file://frontend/README.md"
  ],
  "model": "claude-sonnet-4"
}
```

**Component Agent** (`.kiro/agents/component-agent.json`):
```json
{
  "name": "component-agent",
  "description": "Specialized agent for React component creation with shadcn/ui",
  "prompt": "You are a React component specialist. You focus on:\n\n1. Creating accessible, reusable components\n2. Using shadcn/ui as the foundation\n3. Proper TypeScript typing for props\n4. Component composition patterns\n5. Storybook documentation (if applicable)\n\nAlways ensure components are accessible and follow WCAG guidelines.",
  "tools": ["read", "write"],
  "allowedTools": ["read", "write"],
  "resources": [
    "file://frontend/src/shared/components/ui/"
  ],
  "model": "claude-sonnet-4"
}
```

#### 2. New Custom Prompts (3 prompts)

**@implement-feature-slice** (`.kiro/prompts/implement-feature-slice.md`):
```markdown
# Implement Feature Slice

Create a complete feature slice following VSA patterns.

## Required Information
- Feature name (e.g., "customers", "jobs", "schedule")
- API endpoints to integrate
- Key components needed

## Structure to Create
1. `features/{name}/components/` - React components
2. `features/{name}/hooks/` - TanStack Query hooks
3. `features/{name}/api/` - API integration
4. `features/{name}/types/` - TypeScript types
5. `features/{name}/index.ts` - Public exports

## Patterns to Follow
- Use TanStack Query for all API calls
- Use Zod for runtime validation
- Use shadcn/ui components as base
- Export only public API from index.ts
```

**@implement-api-client** (`.kiro/prompts/implement-api-client.md`):
```markdown
# Implement API Client

Create type-safe API client for a feature.

## Required Information
- Feature name
- Backend API endpoints
- Request/response types

## Implementation Pattern
1. Define TypeScript types matching backend schemas
2. Create API functions using Axios client
3. Add proper error handling
4. Export from feature's api/ directory
```

**@implement-tanstack-hook** (`.kiro/prompts/implement-tanstack-hook.md`):
```markdown
# Implement TanStack Query Hook

Create a TanStack Query hook for data fetching.

## Required Information
- Hook name (e.g., useCustomers, useCreateJob)
- API endpoint to call
- Query key structure
- Mutation or query?

## Implementation Pattern
- Use queryKey factory pattern
- Include proper TypeScript generics
- Handle loading, error, success states
- Add optimistic updates for mutations
```

#### 3. New Hooks (3 hooks)

**Frontend Lint Hook** (`.kiro/hooks/frontend-lint.json`):
```json
{
  "name": "Frontend Lint on Save",
  "version": "1.0.0",
  "description": "Run ESLint on frontend TypeScript files when edited",
  "when": {
    "type": "fileEdited",
    "patterns": ["frontend/src/**/*.tsx", "frontend/src/**/*.ts"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "Run `cd frontend && npm run lint` and fix any errors in the edited file"
  }
}
```

**Frontend Typecheck Hook** (`.kiro/hooks/frontend-typecheck.json`):
```json
{
  "name": "Frontend Typecheck on Save",
  "version": "1.0.0",
  "description": "Run TypeScript type checking on frontend files",
  "when": {
    "type": "fileEdited",
    "patterns": ["frontend/src/**/*.tsx", "frontend/src/**/*.ts"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "Run `cd frontend && npm run typecheck` and fix any type errors"
  }
}
```

**UI Validation Hook** (`.kiro/hooks/validate-ui-on-complete.json`):
```json
{
  "name": "Validate UI on Agent Stop",
  "version": "1.0.0",
  "description": "Run UI validation after frontend changes",
  "when": {
    "type": "agentStop"
  },
  "then": {
    "type": "runCommand",
    "command": "bash scripts/validate-ui.sh"
  }
}
```

#### 4. New Steering Documents (2 documents)

**Frontend Patterns** (`.kiro/steering/frontend-patterns.md`):
- React component patterns
- TanStack Query usage patterns
- Form handling with React Hook Form + Zod
- Error boundary patterns
- Accessibility guidelines

**Frontend Testing** (`.kiro/steering/frontend-testing.md`):
- Vitest setup and patterns
- React Testing Library usage
- Component testing strategies
- Integration testing with MSW

#### 5. Subagent Strategy

**Parallel Execution Opportunities:**
```
Backend (Appointment API)     Frontend (Dashboard Shell)
        ↓                              ↓
        └──────────┬───────────────────┘
                   ↓
         Feature Integration
                   ↓
    ┌──────────────┼──────────────┐
    ↓              ↓              ↓
Customers UI   Jobs UI      Schedule UI
    ↓              ↓              ↓
    └──────────────┴──────────────┘
                   ↓
         Integration Testing
```

**Subagent Delegation Plan:**
- **Subagent A**: Backend appointment API (spec-task-execution)
- **Subagent B**: Frontend core setup (frontend-agent)
- **Main Agent**: Orchestration and integration

**Estimated Time Savings**: 30-40% with parallel execution

### Kiro Integration Summary

| Feature | New Items | Impact | Time |
|---------|-----------|--------|------|
| **Spec** | 1 new spec (admin-dashboard) | ⭐⭐⭐⭐⭐ | 2h |
| **Agents** | 2 new agents (frontend, component) | ⭐⭐⭐⭐ | 1h |
| **Prompts** | 3 new prompts | ⭐⭐⭐⭐ | 30m |
| **Hooks** | 3 new hooks | ⭐⭐⭐⭐ | 45m |
| **Steering** | 2 new docs | ⭐⭐⭐ | 1h |
| **Agent-Browser** | UI validation scripts | ⭐⭐⭐⭐⭐ | 1h |

**Total Kiro Setup Time**: ~6.5 hours


---

## Backend File Structure

### New Files for Phase 3

```
src/grins_platform/
├── models/
│   └── appointment.py              # NEW: Appointment SQLAlchemy model
├── schemas/
│   └── appointment.py              # NEW: Appointment Pydantic schemas
├── repositories/
│   └── appointment_repository.py   # NEW: Appointment data access
├── services/
│   ├── appointment_service.py      # NEW: Appointment business logic
│   └── dashboard_service.py        # NEW: Dashboard metrics service
├── api/v1/
│   ├── appointments.py             # NEW: Appointment API endpoints
│   └── dashboard.py                # NEW: Dashboard API endpoints
├── migrations/versions/
│   └── 20250121_create_appointments_table.py  # NEW: Migration
└── exceptions/
    └── appointment_exceptions.py   # NEW: Appointment-specific exceptions
```

### Updated Files

```
src/grins_platform/
├── api/v1/
│   └── router.py                   # UPDATE: Add appointment and dashboard routes
├── models/
│   └── __init__.py                 # UPDATE: Export Appointment model
├── schemas/
│   └── __init__.py                 # UPDATE: Export appointment schemas
└── services/
    └── __init__.py                 # UPDATE: Export new services
```


---

## Dependencies

### Frontend Dependencies (npm)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.21.0",
    "@tanstack/react-query": "^5.17.0",
    "@tanstack/react-table": "^8.11.0",
    "react-hook-form": "^7.49.0",
    "@hookform/resolvers": "^3.3.0",
    "zod": "^3.22.0",
    "@fullcalendar/react": "^6.1.0",
    "@fullcalendar/daygrid": "^6.1.0",
    "@fullcalendar/timegrid": "^6.1.0",
    "@fullcalendar/interaction": "^6.1.0",
    "axios": "^1.6.0",
    "date-fns": "^3.0.0",
    "lucide-react": "^0.303.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "eslint": "^8.56.0",
    "@typescript-eslint/eslint-plugin": "^6.18.0",
    "@typescript-eslint/parser": "^6.18.0",
    "vitest": "^1.2.0",
    "@testing-library/react": "^14.1.0",
    "@testing-library/jest-dom": "^6.2.0"
  }
}
```

### Backend Dependencies (Python)

No new Python dependencies required - uses existing:
- FastAPI
- SQLAlchemy 2.0
- Pydantic v2
- asyncpg

### Global Tools

```bash
# Agent-browser for UI validation
npm install -g agent-browser
agent-browser install
```


---

## Implementation Phases

### Phase 1: Kiro Setup + Backend Appointments [4-5 hours]

**Morning: Kiro Setup (2.5 hours)**
- Create admin-dashboard spec (requirements.md, design.md, tasks.md)
- Create frontend-agent and component-agent
- Create 3 new prompts
- Create 3 new hooks
- Create 2 new steering documents
- Install and configure agent-browser globally
- Create UI validation scripts

**Afternoon: Backend Appointments (2-3 hours)**
- Create appointments migration
- Create Appointment SQLAlchemy model
- Create Pydantic schemas
- Create AppointmentRepository
- Create AppointmentService with LoggerMixin
- Implement 8 appointment API endpoints
- Write tests (unit, functional, integration)

### Phase 2: Frontend Foundation [4-5 hours]

- Initialize Vite + React + TypeScript project
- Configure Tailwind CSS
- Install and configure shadcn/ui
- Set up TanStack Query provider
- Create Axios API client with interceptors
- Set up React Router with route definitions
- Create Layout component with sidebar navigation
- Create shared UI components
- Configure ESLint + Prettier
- Set up Vitest for testing
- Validate core layout with agent-browser

### Phase 3: Customer Feature Slice [4-5 hours]

- Create customer types matching backend schemas
- Create customerApi.ts with all API calls
- Create TanStack Query hooks (list, single, create, update)
- Create CustomerList, CustomerDetail, CustomerForm, CustomerSearch components
- Write component tests
- Validate with agent-browser

### Phase 4: Jobs Feature Slice [4-5 hours]

- Create job types matching backend schemas
- Create jobApi.ts with all API calls
- Create TanStack Query hooks
- Create JobList, JobDetail, JobForm, JobStatusBadge components
- Write component tests
- Validate with agent-browser

### Phase 5: Schedule Feature Slice [4-5 hours]

- Create appointment types
- Create appointmentApi.ts
- Create TanStack Query hooks
- Install and configure FullCalendar
- Create SchedulePage, CalendarView, AppointmentForm components
- Write component tests
- Validate with agent-browser

### Phase 6: Integration + Polish [4-5 hours]

- Dashboard page with metrics
- Staff feature slice (basic list/detail)
- Cross-feature navigation
- Error handling and loading states
- Responsive design verification
- Accessibility audit
- Full agent-browser E2E validation suite
- Documentation updates


---

## Definition of Done

### A feature is considered COMPLETE when ALL of the following are true:

#### Backend
1. All API endpoints implemented
2. All tests passing (`uv run pytest -v`)
3. Quality checks passing (`uv run ruff check src/ && uv run mypy src/`)

#### Frontend
1. All components implemented
2. All tests passing (`cd frontend && npm test`)
3. TypeScript compiles without errors (`npm run typecheck`)
4. ESLint passes (`npm run lint`)
5. Feature works in browser (manual verification)
6. Agent-browser validation passing

### Verification Commands

**Backend:**
```bash
uv run ruff check src/ && uv run mypy src/ && uv run pytest -v
```

**Frontend:**
```bash
cd frontend && npm run lint && npm run typecheck && npm test
```

**Agent-Browser UI Validation:**
```bash
# Ensure frontend is running first: cd frontend && npm run dev
bash scripts/validate-ui.sh
```

### Quality Standards

| Component | Requirement |
|-----------|-------------|
| Backend Tests | 85%+ coverage |
| Frontend Tests | Component tests for all features |
| TypeScript | Strict mode, no `any` types |
| ESLint | Zero errors |
| Accessibility | WCAG 2.1 AA compliance |
| Agent-Browser | All validation scripts passing |


---

## Appendix: shadcn/ui Components to Install

```bash
# Core components
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add input
npx shadcn-ui@latest add label
npx shadcn-ui@latest add select
npx shadcn-ui@latest add table
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add badge
npx shadcn-ui@latest add toast
npx shadcn-ui@latest add form
npx shadcn-ui@latest add calendar
npx shadcn-ui@latest add popover
npx shadcn-ui@latest add separator
npx shadcn-ui@latest add skeleton
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add textarea
```

