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

// Mock data for job and staff selection
// In a real app, these would come from API hooks
const mockJobs = [
  { id: '123e4567-e89b-12d3-a456-426614174001', label: 'Spring Startup - John Doe' },
  { id: '123e4567-e89b-12d3-a456-426614174002', label: 'Winterization - Jane Smith' },
  { id: '123e4567-e89b-12d3-a456-426614174003', label: 'Repair - Bob Wilson' },
];

const mockStaff = [
  { id: '123e4567-e89b-12d3-a456-426614174010', name: 'Viktor' },
  { id: '123e4567-e89b-12d3-a456-426614174011', name: 'Vas' },
  { id: '123e4567-e89b-12d3-a456-426614174012', name: 'Dad' },
];

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

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="space-y-4"
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
                disabled={isEditing}
              >
                <FormControl>
                  <SelectTrigger data-testid="job-select">
                    <SelectValue placeholder="Select a job" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {mockJobs.map((job) => (
                    <SelectItem key={job.id} value={job.id}>
                      {job.label}
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
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger data-testid="staff-select">
                    <SelectValue placeholder="Select staff member" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {mockStaff.map((staff) => (
                    <SelectItem key={staff.id} value={staff.id}>
                      {staff.name}
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
        <div className="flex justify-end gap-2 pt-4">
          {onCancel && (
            <Button type="button" variant="outline" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button type="submit" disabled={isPending} data-testid="submit-btn">
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
