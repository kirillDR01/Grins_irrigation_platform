/**
 * Appointment form component.
 * Handles creating and editing appointments.
 */

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { format } from 'date-fns';
import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { MapPin } from 'lucide-react';
import { useCreateAppointment, useUpdateAppointment } from '../hooks/useAppointmentMutations';
import { useJobsReadyToSchedule } from '@/features/jobs/hooks';
import { useStaff } from '@/features/staff/hooks';
import { jobApi } from '@/features/jobs/api/jobApi';
import { customerApi } from '@/features/customers/api/customerApi';
import { JobSelectorCombobox } from './JobSelectorCombobox';
import type { Appointment, AppointmentCreate, AppointmentUpdate } from '../types';

// Form validation schema
const appointmentSchema = z.object({
  job_id: z.string().uuid('Please select a valid job'),
  staff_id: z.string().uuid('Please select a valid staff member'),
  scheduled_date: z.string().min(1, 'Date is required'),
  time_window_start: z.string().min(1, 'Start time is required'),
  time_window_end: z.string().min(1, 'End time is required'),
  notes: z.string().optional(),
}).refine(
  (data) => {
    if (data.time_window_start && data.time_window_end) {
      return data.time_window_end > data.time_window_start;
    }
    return true;
  },
  {
    message: 'End time must be after start time',
    path: ['time_window_end'],
  }
);

type FormData = z.infer<typeof appointmentSchema>;

interface AppointmentFormProps {
  appointment?: Appointment;
  initialDate?: Date;
  initialJobId?: string;
  initialStaffId?: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function AppointmentForm({
  appointment,
  initialDate,
  initialJobId,
  initialStaffId,
  onSuccess,
  onCancel,
}: AppointmentFormProps) {
  const createMutation = useCreateAppointment();
  const updateMutation = useUpdateAppointment();
  
  // Fetch real jobs and staff from API
  const { data: jobsData, isLoading: jobsLoading } = useJobsReadyToSchedule();
  const { data: staffData, isLoading: staffLoading } = useStaff({ is_active: true });

  const isEditing = !!appointment;

  const form = useForm<FormData>({
    resolver: zodResolver(appointmentSchema),
    defaultValues: {
      job_id: appointment?.job_id ?? initialJobId ?? '',
      staff_id: appointment?.staff_id ?? initialStaffId ?? '',
      scheduled_date: appointment?.scheduled_date ?? 
        (initialDate ? format(initialDate, 'yyyy-MM-dd') : ''),
      time_window_start: appointment?.time_window_start?.slice(0, 5) ?? '08:00',
      time_window_end: appointment?.time_window_end?.slice(0, 5) ?? '10:00',
      notes: appointment?.notes ?? '',
    },
  });

  // Address auto-populate from customer's primary property (Req 29)
  const [autoAddress, setAutoAddress] = useState<string | null>(null);
  const [addressOverridden, setAddressOverridden] = useState(false);

  const selectedJobId = form.watch('job_id');

  // Fetch job to get customer_id when a job is selected
  const { data: selectedJob } = useQuery({
    queryKey: ['jobs', 'detail', selectedJobId],
    queryFn: () => jobApi.get(selectedJobId),
    enabled: !!selectedJobId && selectedJobId !== 'no-jobs',
  });

  // Fetch customer to get primary property address
  const { data: selectedCustomer } = useQuery({
    queryKey: ['customers', 'detail', selectedJob?.customer_id],
    queryFn: () => customerApi.get(selectedJob!.customer_id),
    enabled: !!selectedJob?.customer_id,
  });

  // Auto-populate address when customer data loads
  useEffect(() => {
    if (selectedCustomer?.properties && selectedCustomer.properties.length > 0) {
      const primary = selectedCustomer.properties.find((p) => p.is_primary) ?? selectedCustomer.properties[0];
      const addr = [primary.address, primary.city, primary.state, primary.zip_code]
        .filter(Boolean)
        .join(', ');
      setAutoAddress(addr);
      setAddressOverridden(false);
    } else {
      setAutoAddress(null);
    }
  }, [selectedCustomer]);

  const onSubmit = async (data: FormData) => {
    try {
      if (isEditing) {
        const updateData: AppointmentUpdate = {
          staff_id: data.staff_id,
          scheduled_date: data.scheduled_date,
          time_window_start: data.time_window_start + ':00',
          time_window_end: data.time_window_end + ':00',
          notes: data.notes || undefined,
        };
        await updateMutation.mutateAsync({
          id: appointment.id,
          data: updateData,
        });
      } else {
        const createData: AppointmentCreate = {
          job_id: data.job_id,
          staff_id: data.staff_id,
          scheduled_date: data.scheduled_date,
          time_window_start: data.time_window_start + ':00',
          time_window_end: data.time_window_end + ':00',
          notes: data.notes || undefined,
        };
        await createMutation.mutateAsync(createData);
      }
      onSuccess?.();
    } catch (error) {
      console.error('Failed to save appointment:', error);
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;
  const isLoadingData = jobsLoading || staffLoading;
  
  // Get jobs and staff arrays
  const jobs = jobsData?.items ?? [];
  const staff = staffData?.items ?? [];

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="p-6 space-y-6"
        data-testid="appointment-form"
      >
        {/* Job Selection — Searchable Combobox (Req 11.1-11.6) */}
        <FormField
          control={form.control}
          name="job_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Job</FormLabel>
              <FormControl>
                <JobSelectorCombobox
                  jobs={jobs}
                  value={field.value}
                  onChange={field.onChange}
                  disabled={isEditing || isLoadingData}
                  isLoading={jobsLoading}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Staff Selection */}
        <FormField
          control={form.control}
          name="staff_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Staff Member</FormLabel>
              <Select 
                onValueChange={field.onChange} 
                defaultValue={field.value}
                disabled={isLoadingData}
              >
                <FormControl>
                  <SelectTrigger data-testid="staff-select">
                    <SelectValue placeholder={staffLoading ? "Loading staff..." : "Select staff member"} />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {staff.length === 0 && !staffLoading && (
                    <SelectItem value="no-staff" disabled>No staff available</SelectItem>
                  )}
                  {staff.map((member) => (
                    <SelectItem key={member.id} value={member.id}>
                      {member.name} ({member.role})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Date */}
        <FormField
          control={form.control}
          name="scheduled_date"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Date</FormLabel>
              <FormControl>
                <Input type="date" {...field} data-testid="date-input" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Auto-populated Address (Req 29) */}
        {autoAddress && (
          <div data-testid="auto-address-section">
            <FormLabel>Property Address</FormLabel>
            <div className="mt-1.5 flex items-start gap-2 p-3 bg-slate-50 rounded-lg border border-slate-200">
              <MapPin className="h-4 w-4 text-slate-400 mt-0.5 shrink-0" />
              <div className="flex-1">
                {addressOverridden ? (
                  <Input
                    defaultValue={autoAddress}
                    className="text-sm"
                    data-testid="address-override-input"
                  />
                ) : (
                  <p className="text-sm text-slate-700">{autoAddress}</p>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {!addressOverridden && (
                  <Badge
                    variant="outline"
                    className="text-xs text-teal-600 border-teal-200 bg-teal-50"
                    data-testid="auto-filled-badge"
                  >
                    Auto-filled
                  </Badge>
                )}
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="text-xs text-slate-500 h-6 px-2"
                  onClick={() => setAddressOverridden(!addressOverridden)}
                  data-testid="address-override-btn"
                >
                  {addressOverridden ? 'Reset' : 'Override'}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Time Window */}
        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="time_window_start"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Start Time</FormLabel>
                <FormControl>
                  <Input type="time" {...field} data-testid="start-time-input" />
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
                  <Input type="time" {...field} data-testid="end-time-input" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* Notes */}
        <FormField
          control={form.control}
          name="notes"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Notes (Optional)</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Add any notes about this appointment..."
                  {...field}
                  data-testid="notes-input"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
          {onCancel && (
            <Button 
              type="button" 
              variant="secondary" 
              onClick={onCancel}
              className="px-4 py-2.5"
            >
              Cancel
            </Button>
          )}
          <Button 
            type="submit" 
            disabled={isPending} 
            data-testid="submit-btn"
            className="px-5 py-2.5"
          >
            {isPending
              ? 'Saving...'
              : isEditing
                ? 'Update Appointment'
                : 'Create Appointment'}
          </Button>
        </div>
      </form>
    </Form>
  );
}
