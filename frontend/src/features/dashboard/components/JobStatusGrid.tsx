/**
 * JobStatusGrid — displays 6 job status category cards on the dashboard.
 * Each card is clickable and navigates to /jobs?status={status}.
 *
 * Validates: Requirements 6.1
 */

import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import {
  Inbox,
  FileText,
  Clock,
  CalendarCheck,
  Loader,
  CheckCircle,
} from 'lucide-react';
import { useJobStatusMetrics } from '../hooks';
import type { ComponentType } from 'react';
import type { LucideProps } from 'lucide-react';

interface StatusCategory {
  key: string;
  label: string;
  queryParam: string;
  icon: ComponentType<LucideProps>;
  iconBg: string;
  iconColor: string;
  testId: string;
}

const STATUS_CATEGORIES: StatusCategory[] = [
  {
    key: 'new_requests',
    label: 'New Requests',
    queryParam: 'requested',
    icon: Inbox,
    iconBg: 'bg-amber-100',
    iconColor: 'text-amber-600',
    testId: 'job-status-new-requests',
  },
  {
    key: 'estimates',
    label: 'Estimates',
    queryParam: 'requires_estimate',
    icon: FileText,
    iconBg: 'bg-blue-100',
    iconColor: 'text-blue-600',
    testId: 'job-status-estimates',
  },
  {
    key: 'pending_approval',
    label: 'Pending Approval',
    queryParam: 'pending_approval',
    icon: Clock,
    iconBg: 'bg-purple-100',
    iconColor: 'text-purple-600',
    testId: 'job-status-pending-approval',
  },
  {
    key: 'to_be_scheduled',
    label: 'To Be Scheduled',
    queryParam: 'approved',
    icon: CalendarCheck,
    iconBg: 'bg-teal-100',
    iconColor: 'text-teal-600',
    testId: 'job-status-to-be-scheduled',
  },
  {
    key: 'in_progress',
    label: 'In Progress',
    queryParam: 'in_progress',
    icon: Loader,
    iconBg: 'bg-orange-100',
    iconColor: 'text-orange-600',
    testId: 'job-status-in-progress',
  },
  {
    key: 'complete',
    label: 'Complete',
    queryParam: 'completed',
    icon: CheckCircle,
    iconBg: 'bg-green-100',
    iconColor: 'text-green-600',
    testId: 'job-status-complete',
  },
];

export function JobStatusGrid() {
  const navigate = useNavigate();
  const { data, isLoading } = useJobStatusMetrics();

  return (
    <div
      data-testid="job-status-grid"
      className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4"
    >
      {STATUS_CATEGORIES.map((category) => {
        const Icon = category.icon;
        const count =
          data?.[category.key as keyof typeof data] ?? 0;

        const handleClick = () => {
          navigate(`/jobs?status=${category.queryParam}`);
        };

        return (
          <Card
            key={category.key}
            data-testid={category.testId}
            className="cursor-pointer transition-all hover:shadow-md"
            onClick={handleClick}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleClick();
              }
            }}
          >
            <CardContent className="p-4">
              <div className="flex flex-col items-center text-center gap-2">
                <div className={cn('p-2 rounded-xl', category.iconBg)}>
                  <Icon className={cn('h-5 w-5', category.iconColor)} />
                </div>
                <div className="text-2xl font-bold text-slate-800">
                  {isLoading ? '—' : count}
                </div>
                <p className="text-xs font-medium text-slate-500">
                  {category.label}
                </p>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
