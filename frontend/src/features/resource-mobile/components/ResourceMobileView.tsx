/**
 * ResourceMobileView — composed mobile page for Resource role.
 * Stacks ResourceScheduleView on top, ResourceMobileChat below.
 *
 * Bug 2 fix: previously rendered ResourceScheduleView with no props, which
 * crashed at runtime because schedule was undefined. Now wires
 * useResourceSchedule(staffId, today) and renders loading/error/data states
 * inside an ErrorBoundary.
 */

import { useMemo, useState } from 'react';

import { ResourceMobileChat } from '@/features/ai';
import { useAuth } from '@/features/auth';
import { ErrorBoundary, ErrorMessage } from '@/shared/components/ErrorBoundary';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';

import { useResourceSchedule } from '../hooks/useResourceSchedule';
import { ResourceScheduleView } from './ResourceScheduleView';

function todayIsoDate(): string {
  return new Date().toISOString().split('T')[0];
}

export function ResourceMobileView() {
  const { user } = useAuth();
  const staffId = user?.id ?? '';
  const [date] = useState<string>(() => todayIsoDate());

  const { data, isLoading, error } = useResourceSchedule(staffId, date);

  const schedulePane = useMemo(() => {
    if (isLoading) {
      return (
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner />
        </div>
      );
    }
    if (error) {
      return <ErrorMessage error={error as Error} />;
    }
    if (!data) {
      return (
        <p className="text-sm text-gray-500 py-4 text-center">
          No schedule available.
        </p>
      );
    }
    return <ResourceScheduleView schedule={data} />;
  }, [data, error, isLoading]);

  return (
    <div
      className="flex flex-col min-h-screen bg-slate-50"
      data-testid="resource-mobile-page"
    >
      <ErrorBoundary fallback={<div>Schedule unavailable</div>}>
        {schedulePane}
      </ErrorBoundary>
      <ResourceMobileChat />
    </div>
  );
}
