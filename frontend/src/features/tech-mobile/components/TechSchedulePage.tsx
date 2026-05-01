import { useState } from 'react';
import { format } from 'date-fns';
import { Calendar, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/features/auth/components/AuthProvider';
import { useStaffDailySchedule } from '@/features/schedule/hooks/useAppointments';
import { AppointmentModal } from '@/features/schedule/components/AppointmentModal';
import type { Appointment } from '@/features/schedule/types';
import { TechHeader } from './TechHeader';
import { MobileJobCard } from './MobileJobCard';
import { deriveCardState } from '../utils/cardState';

export function TechSchedulePage() {
  const { user } = useAuth();
  const today = format(new Date(), 'yyyy-MM-dd');
  const { data, isLoading, isError, refetch } = useStaffDailySchedule(
    user?.id,
    today
  );
  const [openId, setOpenId] = useState<string | null>(null);

  if (!user) return null;

  const visible: Appointment[] = (data?.appointments ?? [])
    .filter((a: Appointment) => deriveCardState(a.status) !== 'hidden')
    .sort((a: Appointment, b: Appointment) =>
      a.time_window_start.localeCompare(b.time_window_start)
    );

  return (
    <>
      <TechHeader
        userName={user.name}
        jobCount={visible.length}
        date={new Date()}
      />

      {isLoading && (
        <div className="px-3 pt-3 space-y-3">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="bg-slate-100 animate-pulse rounded-2xl h-32"
            />
          ))}
        </div>
      )}

      {isError && (
        <div className="px-3 pt-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-5 text-center">
            <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-3" />
            <p className="text-slate-900 font-semibold mb-1">
              Couldn't load your schedule
            </p>
            <p className="text-sm text-slate-500 mb-4">
              Check your connection and try again.
            </p>
            <Button
              onClick={() => {
                void refetch();
              }}
              variant="outline"
            >
              Retry
            </Button>
          </div>
        </div>
      )}

      {!isLoading && !isError && visible.length === 0 && (
        <div
          className="flex flex-col items-center justify-center px-6 pt-16 pb-12 text-center"
          data-testid="tech-empty-state"
        >
          <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
            <Calendar className="w-7 h-7 text-slate-400" />
          </div>
          <p className="text-slate-900 font-semibold">No appointments today</p>
          <p className="text-sm text-slate-500 mt-1">
            Enjoy the day — we'll notify you when something is added.
          </p>
        </div>
      )}

      {!isLoading && !isError && visible.length > 0 && (
        <div className="px-3 pt-3 pb-6 space-y-3">
          {visible.map((a) => (
            <MobileJobCard key={a.id} appointment={a} onOpen={setOpenId} />
          ))}
        </div>
      )}

      {openId && (
        <AppointmentModal
          appointmentId={openId}
          open={!!openId}
          onClose={() => setOpenId(null)}
        />
      )}
    </>
  );
}
