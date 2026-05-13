/**
 * ActionTrack — 3 side-by-side ActionCards for the appointment workflow.
 * Optimistic step advancement with revert on failure.
 * Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8
 */

import { Navigation, MapPin, CheckCircle, Info } from 'lucide-react';
import { toast } from 'sonner';
import { ActionCard } from './ActionCard';
import {
  useMarkAppointmentArrived,
  useMarkAppointmentCompleted,
} from '../../hooks/useAppointmentMutations';
import { useOnMyWay } from '@/features/jobs/hooks';
import type { AppointmentStatus } from '../../types';
import { deriveStep } from '../../hooks/useModalState';
import {
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
} from '@/shared/components/ui/alert';

interface ActionTrackProps {
  appointmentId: string;
  jobId: string;
  status: AppointmentStatus;
  arrivedAt?: string | null;
  enRouteAt?: string | null;
  completedAt?: string | null;
}

const TERMINAL_STATUSES: AppointmentStatus[] = ['pending', 'draft', 'cancelled', 'no_show'];

export function ActionTrack({
  appointmentId,
  jobId,
  status,
  arrivedAt,
  enRouteAt,
  completedAt,
}: ActionTrackProps) {
  const step = deriveStep(status);
  // Cluster D Item 5: canonical on-the-way path is job-side so the audited
  // `job.on_my_way_at` write + SMS dispatch + appointment auto-transition
  // happen in one server-side flow (api/v1/jobs.py).
  const onMyWayMutation = useOnMyWay();
  const arrivedMutation = useMarkAppointmentArrived();
  const completedMutation = useMarkAppointmentCompleted();

  // Cluster D Item 3: when the customer hasn't yet replied Y, render an
  // explanatory banner instead of disabled cards — workflow actions
  // unlock only after CONFIRMED.
  if (status === 'scheduled') {
    return (
      <div className="px-3 sm:px-5 pb-4">
        <Alert variant="info" data-testid="awaiting-confirmation-banner">
          <div className="flex items-start gap-3">
            <AlertIcon variant="info">
              <Info className="h-4 w-4" />
            </AlertIcon>
            <div>
              <AlertTitle>Waiting for customer confirmation</AlertTitle>
              <AlertDescription>
                On My Way, Job Started, and Job Complete unlock once the
                customer replies <strong>Y</strong> to the confirmation text.
              </AlertDescription>
            </div>
          </div>
        </Alert>
      </div>
    );
  }

  if (TERMINAL_STATUSES.includes(status)) return null;

  const cardState = (cardStep: number) => {
    if (step === null) return 'disabled' as const;
    if (step > cardStep) return 'done' as const;
    if (step === cardStep) return 'active' as const;
    return 'disabled' as const;
  };

  const handleEnRoute = () => {
    onMyWayMutation.mutate(jobId, {
      onError: () => toast.error("Couldn't update status — try again"),
    });
  };

  const handleArrived = () => {
    arrivedMutation.mutate(appointmentId, {
      onError: () => toast.error("Couldn't update status — try again"),
    });
  };

  const handleCompleted = () => {
    completedMutation.mutate(appointmentId, {
      onError: () => toast.error("Couldn't update status — try again"),
    });
  };

  return (
    <div className="px-3 sm:px-5 pb-4 flex gap-1.5 sm:gap-2 flex-shrink-0">
      <ActionCard
        label="On my way"
        icon={<Navigation />}
        stageColor="bg-cyan-600"
        state={cardState(1)}
        completedAt={enRouteAt}
        onClick={handleEnRoute}
        aria-label="Mark as on my way"
      />
      <ActionCard
        label="Job started"
        icon={<MapPin />}
        stageColor="bg-orange-500"
        state={cardState(2)}
        completedAt={arrivedAt}
        onClick={handleArrived}
        aria-label="Mark job as started"
      />
      <ActionCard
        label="Job complete"
        icon={<CheckCircle />}
        stageColor="bg-green-600"
        state={cardState(3)}
        completedAt={completedAt}
        onClick={handleCompleted}
        aria-label="Mark job as complete"
      />
    </div>
  );
}
