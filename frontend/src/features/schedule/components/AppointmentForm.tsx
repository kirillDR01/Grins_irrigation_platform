/**
 * Appointment form component.
 * Handles creating and editing appointments.
 */

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { format } from 'date-fns';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
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
import { useCreateAppointment, useUpdateAppointment } from '../hooks/useAppointmentMutations';
import { useJobsReadyToSchedule } from '@/features/jobs/hooks';
import { useStaff } from '@/features/staff/hooks';
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
        {/* Job Selection */}
        <FormField
          control={form.control}
          name="job_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Job</FormLabel>
              <Select
                onValueChange={field.onChange}
                defaultValue={field.value}
                disabled={isEditing || isLoadingData}
              >
                <FormControl>
                  <SelectTrigger data-testid="job-select">
                    <SelectValue placeholder={jobsLoading ? "Loading jobs..." : "Select a job"} />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {jobs.length === 0 && !jobsLoading && (
                    <SelectItem value="no-jobs" disabled>No jobs ready to schedule</SelectItem>
                  )}
                  {jobs.map((job) => (
                    <SelectItem key={job.id} value={job.id}>
                      {job.job_type} - {job.description?.slice(0, 40) || 'No description'}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
