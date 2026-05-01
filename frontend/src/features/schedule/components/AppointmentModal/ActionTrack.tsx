/**
 * ActionTrack — 3 side-by-side ActionCards for the appointment workflow.
 * Optimistic step advancement with revert on failure.
 * Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8
 */

import { Navigation, MapPin, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';
import { ActionCard } from './ActionCard';
import {
  useMarkAppointmentEnRoute,
  useMarkAppointmentArrived,
  useMarkAppointmentCompleted,
} from '../../hooks/useAppointmentMutations';
import type { AppointmentStatus } from '../../types';
import { deriveStep } from '../../hooks/useModalState';

interface ActionTrackProps {
  appointmentId: string;
  status: AppointmentStatus;
  arrivedAt?: string | null;
  enRouteAt?: string | null;
  completedAt?: string | null;
}

const TERMINAL_STATUSES: AppointmentStatus[] = ['pending', 'draft', 'cancelled', 'no_show'];

export function ActionTrack({
  appointmentId,
  status,
  arrivedAt,
  enRouteAt,
  completedAt,
}: ActionTrackProps) {
  const step = deriveStep(status);
  const enRouteMutation = useMarkAppointmentEnRoute();
  const arrivedMutation = useMarkAppointmentArrived();
  const completedMutation = useMarkAppointmentCompleted();

  if (TERMINAL_STATUSES.includes(status)) return null;

  const cardState = (cardStep: number) => {
    if (step === null) return 'disabled' as const;
    if (step > cardStep) return 'done' as const;
    if (step === cardStep) return 'active' as const;
    return 'disabled' as const;
  };

  const handleEnRoute = () => {
    enRouteMutation.mutate(appointmentId, {
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
