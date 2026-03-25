/**
 * Inline customer/job info panel (Req 27).
 * Slide-over from right side using Radix Sheet.
 * URL does NOT change when panel opens.
 */

import { Link } from 'react-router-dom';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  User,
  Phone,
  Mail,
  MapPin,
  Clock,
  FileText,
  ExternalLink,
  Briefcase,
} from 'lucide-react';
import { useAppointment } from '../hooks/useAppointments';
import { useQuery } from '@tanstack/react-query';
import { jobApi } from '@/features/jobs/api/jobApi';
import { customerApi } from '@/features/customers/api/customerApi';
import { appointmentStatusConfig } from '../types';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';

interface InlineCustomerPanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  appointmentId: string | null;
}

export function InlineCustomerPanel({
  open,
  onOpenChange,
  appointmentId,
}: InlineCustomerPanelProps) {
  const { data: appointment, isLoading: apptLoading } = useAppointment(
    appointmentId ?? undefined
  );

  const { data: job, isLoading: jobLoading } = useQuery({
    queryKey: ['jobs', 'detail', appointment?.job_id],
    queryFn: () => jobApi.get(appointment!.job_id),
    enabled: !!appointment?.job_id,
  });

  const { data: customer, isLoading: customerLoading } = useQuery({
    queryKey: ['customers', 'detail', job?.customer_id],
    queryFn: () => customerApi.get(job!.customer_id),
    enabled: !!job?.customer_id,
  });

  const isLoading = apptLoading || jobLoading || customerLoading;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full h-[90vh] rounded-t-2xl fixed bottom-0 left-0 right-0 overflow-y-auto md:w-[450px] md:h-full md:rounded-t-none md:static"
        data-testid="inline-customer-panel"
      >
        <SheetHeader>
          <SheetTitle>Customer & Job Info</SheetTitle>
          <SheetDescription>
            View details without leaving the schedule.
          </SheetDescription>
        </SheetHeader>

        {isLoading ? (
          <div className="flex items-center justify-center h-48">
            <LoadingSpinner />
          </div>
        ) : !appointment ? (
          <p className="text-sm text-slate-500 mt-4">No appointment selected.</p>
        ) : (
          <div className="mt-6 space-y-6">
            {/* Customer Info */}
            {customer && (
              <section data-testid="panel-customer-info">
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
                  Customer
                </h3>
                <div className="space-y-2.5">
                  <div className="flex items-center gap-2">
                    <User className="h-4 w-4 text-slate-400" />
                    <span className="text-sm font-medium text-slate-800">
                      {customer.first_name} {customer.last_name}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Phone className="h-4 w-4 text-slate-400" />
                    <a
                      href={`tel:${customer.phone}`}
                      className="text-sm text-teal-600 hover:underline"
                    >
                      {customer.phone}
                    </a>
                  </div>
                  {customer.email && (
                    <div className="flex items-center gap-2">
                      <Mail className="h-4 w-4 text-slate-400" />
                      <a
                        href={`mailto:${customer.email}`}
                        className="text-sm text-teal-600 hover:underline"
                      >
                        {customer.email}
                      </a>
                    </div>
                  )}
                  {customer.properties?.[0] && (
                    <div className="flex items-start gap-2">
                      <MapPin className="h-4 w-4 text-slate-400 mt-0.5" />
                      <span className="text-sm text-slate-600">
                        {customer.properties[0].address}, {customer.properties[0].city},{' '}
                        {customer.properties[0].state} {customer.properties[0].zip_code}
                      </span>
                    </div>
                  )}
                  {customer.preferred_service_times && (
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-slate-400" />
                      <span className="text-sm text-slate-600">
                        Preferred: {customer.preferred_service_times.preference}
                      </span>
                    </div>
                  )}
                  {customer.internal_notes && (
                    <div className="flex items-start gap-2">
                      <FileText className="h-4 w-4 text-slate-400 mt-0.5" />
                      <p className="text-sm text-slate-600 line-clamp-3">
                        {customer.internal_notes}
                      </p>
                    </div>
                  )}
                </div>
              </section>
            )}

            {/* Job Info */}
            {job && (
              <section data-testid="panel-job-info">
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
                  Job Details
                </h3>
                <div className="space-y-2.5">
                  <div className="flex items-center gap-2">
                    <Briefcase className="h-4 w-4 text-slate-400" />
                    <span className="text-sm font-medium text-slate-800">
                      {job.job_type}
                    </span>
                  </div>
                  {job.description && (
                    <p className="text-sm text-slate-600 pl-6">
                      {job.description}
                    </p>
                  )}
                  {job.notes && (
                    <p className="text-sm text-slate-500 pl-6 italic">
                      {job.notes}
                    </p>
                  )}
                </div>
              </section>
            )}

            {/* Appointment Status */}
            {appointment && (
              <section data-testid="panel-appointment-info">
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
                  Appointment
                </h3>
                <div className="flex items-center gap-2">
                  <Badge
                    className={`${appointmentStatusConfig[appointment.status].bgColor} ${appointmentStatusConfig[appointment.status].color} text-xs`}
                  >
                    {appointmentStatusConfig[appointment.status].label}
                  </Badge>
                  <span className="text-sm text-slate-600">
                    {appointment.time_window_start.slice(0, 5)} -{' '}
                    {appointment.time_window_end.slice(0, 5)}
                  </span>
                </div>
                {appointment.notes && (
                  <p className="text-sm text-slate-500 mt-2">{appointment.notes}</p>
                )}
              </section>
            )}

            {/* View Full Details Links */}
            <div className="flex gap-3 pt-4 border-t border-slate-100">
              {customer && (
                <Button variant="outline" size="sm" asChild>
                  <Link
                    to={`/customers/${customer.id}`}
                    data-testid="view-full-customer"
                  >
                    <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                    View Full Details
                  </Link>
                </Button>
              )}
              {job && (
                <Button variant="outline" size="sm" asChild>
                  <Link to={`/jobs/${job.id}`} data-testid="view-full-job">
                    <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                    View Job
                  </Link>
                </Button>
              )}
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
