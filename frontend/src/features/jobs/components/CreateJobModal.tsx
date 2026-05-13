import { useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { startOfWeek } from 'date-fns';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { useCreateJob, useUpdateJob } from '../hooks';
import type { Job, JobCreate, JobUpdate } from '../types';
import { useCustomer } from '@/features/customers/hooks';
import {
  useOverrideSalesStatus,
  pipelineKeys,
} from '@/features/sales/hooks/useSalesPipeline';
import type { SalesEntry } from '@/features/sales/types/pipeline';

const createJobModalSchema = z.object({
  property_id: z.string().optional().nullable(),
  job_type: z.string().min(1, 'Job type is required'),
  description: z.string().optional().nullable(),
  priority_level: z.number().min(0).max(2),
  estimated_duration_minutes: z.number().positive().nullable(),
  staffing_required: z.number().min(1),
  target_start_date: z.string().optional().nullable(),
});

type CreateJobModalFormData = z.infer<typeof createJobModalSchema>;

interface CreateJobModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  salesEntry: SalesEntry;
  onCreated?: (job: Job) => void;
}

/**
 * Modal opened from StatusActionButton / SalesDetail when the user converts
 * a sales entry into a Job. Replaces the old SignWell-gated convert flow.
 *
 * On submit:
 *   1. POST /api/v1/jobs with the form values (via useCreateJob).
 *   2. If a target Mon-start date is set, PATCH /api/v1/jobs/{id} with the
 *      Mon-Sun window (backend rejects target_start_date on create).
 *   3. PATCH /api/v1/sales/pipeline/{id}/status with status='closed_won'.
 */
export function CreateJobModal({
  open,
  onOpenChange,
  salesEntry,
  onCreated,
}: CreateJobModalProps) {
  const createJob = useCreateJob();
  const updateJob = useUpdateJob();
  const overrideStatus = useOverrideSalesStatus();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { data: customer } = useCustomer(salesEntry.customer_id);

  const properties = useMemo(() => customer?.properties ?? [], [customer]);

  const form = useForm<CreateJobModalFormData>({
    resolver: zodResolver(createJobModalSchema),
    defaultValues: {
      property_id: salesEntry.property_id ?? null,
      job_type: salesEntry.job_type ?? 'estimate',
      description: salesEntry.notes ?? '',
      priority_level: 0,
      estimated_duration_minutes: null,
      staffing_required: 1,
      target_start_date: null,
    },
  });

  // Lead source display — SalesEntry has no lead_source field today; fall
  // back to the customer's lead_source when present.
  const leadSourceLabel = customer?.lead_source ?? '—';

  const onSubmit = async (values: CreateJobModalFormData) => {
    try {
      // Normalize target_start_date to the Monday of the chosen week.
      let mondayIso: string | null = null;
      let sundayIso: string | null = null;
      if (values.target_start_date) {
        const picked = new Date(values.target_start_date + 'T00:00:00');
        const monday = startOfWeek(picked, { weekStartsOn: 1 });
        const sunday = new Date(monday);
        sunday.setDate(monday.getDate() + 6);
        mondayIso = monday.toISOString().slice(0, 10);
        sundayIso = sunday.toISOString().slice(0, 10);
      }

      const createPayload: JobCreate = {
        customer_id: salesEntry.customer_id,
        property_id: values.property_id || null,
        job_type: values.job_type,
        description: values.description ?? null,
        priority_level: values.priority_level,
        estimated_duration_minutes: values.estimated_duration_minutes,
        staffing_required: values.staffing_required,
      };

      const job = await createJob.mutateAsync(createPayload);

      // Backend rejects target_start_date on create — patch it in if set.
      if (mondayIso && sundayIso) {
        try {
          const updatePayload: JobUpdate = {
            target_start_date: mondayIso,
            target_end_date: sundayIso,
          };
          await updateJob.mutateAsync({ id: job.id, data: updatePayload });
        } catch {
          // Non-fatal — the job exists, the target window can be edited
          // manually from JobDetail.
        }
      }

      await overrideStatus.mutateAsync({
        id: salesEntry.id,
        body: { status: 'closed_won' },
      });

      toast.success('Job created');
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all });
      onCreated?.(job);
      onOpenChange(false);
      navigate(`/jobs/${job.id}`);
    } catch (err) {
      toast.error('Failed to create job', {
        description: err instanceof Error ? err.message : undefined,
      });
    }
  };

  const isPending =
    createJob.isPending || updateJob.isPending || overrideStatus.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        data-testid="create-job-modal"
        className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto"
      >
        <DialogHeader>
          <DialogTitle>Create Job</DialogTitle>
          <DialogDescription>
            Confirm the details below. A new Job will be created and this sales
            entry will be marked Closed Won.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="space-y-4"
            data-testid="create-job-form"
          >
            {/* 1. Customer (readonly) */}
            <FormItem>
              <FormLabel>Customer</FormLabel>
              <Input
                value={salesEntry.customer_name ?? '—'}
                readOnly
                data-testid="create-job-customer-input"
              />
            </FormItem>

            {/* 2. Property */}
            <FormField
              control={form.control}
              name="property_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Property</FormLabel>
                  <Select
                    onValueChange={(v) => field.onChange(v === '__none' ? null : v)}
                    value={field.value ?? '__none'}
                  >
                    <FormControl>
                      <SelectTrigger data-testid="create-job-property-select">
                        <SelectValue placeholder="Select property" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="__none">— None —</SelectItem>
                      {properties.map((p) => (
                        <SelectItem key={p.id} value={p.id}>
                          {p.address}
                          {p.city ? `, ${p.city}` : ''}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 3. Job Type */}
            <FormField
              control={form.control}
              name="job_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Job Type *</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger data-testid="create-job-type-select">
                        <SelectValue placeholder="Select job type" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="estimate">Estimate</SelectItem>
                      <SelectItem value="spring_startup">Spring Startup</SelectItem>
                      <SelectItem value="summer_tuneup">Summer Tune-up</SelectItem>
                      <SelectItem value="winterization">Winterization</SelectItem>
                      <SelectItem value="repair">Repair</SelectItem>
                      <SelectItem value="diagnostic">Diagnostic</SelectItem>
                      <SelectItem value="installation">Installation</SelectItem>
                      <SelectItem value="landscaping">Landscaping</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 4. Description */}
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea
                      {...field}
                      value={field.value ?? ''}
                      placeholder="Job description and notes"
                      data-testid="create-job-description-input"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 5. Priority */}
            <FormField
              control={form.control}
              name="priority_level"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Priority</FormLabel>
                  <Select
                    onValueChange={(v) => field.onChange(parseInt(v, 10))}
                    value={field.value.toString()}
                  >
                    <FormControl>
                      <SelectTrigger data-testid="create-job-priority-select">
                        <SelectValue placeholder="Select priority" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="0">Normal</SelectItem>
                      <SelectItem value="1">High</SelectItem>
                      <SelectItem value="2">Urgent</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 6. Estimated duration */}
            <FormField
              control={form.control}
              name="estimated_duration_minutes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Estimated duration (minutes)</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min={1}
                      value={field.value ?? ''}
                      onChange={(e) =>
                        field.onChange(
                          e.target.value ? parseInt(e.target.value, 10) : null,
                        )
                      }
                      placeholder="e.g., 60"
                      data-testid="create-job-duration-input"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 7. Staffing required */}
            <FormField
              control={form.control}
              name="staffing_required"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Staffing required</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min={1}
                      value={field.value || 1}
                      onChange={(e) =>
                        field.onChange(parseInt(e.target.value, 10) || 1)
                      }
                      data-testid="create-job-staffing-input"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 8. Target start date */}
            <FormField
              control={form.control}
              name="target_start_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Target start date</FormLabel>
                  <FormControl>
                    <Input
                      type="date"
                      value={field.value ?? ''}
                      onChange={(e) => field.onChange(e.target.value || null)}
                      data-testid="create-job-start-date-input"
                    />
                  </FormControl>
                  <FormDescription>
                    Will snap to the Monday of the selected week.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 9. Lead source (readonly) */}
            <FormItem>
              <FormLabel>Lead source</FormLabel>
              <Input
                value={leadSourceLabel}
                readOnly
                data-testid="create-job-lead-source-input"
              />
            </FormItem>

            {/* 10. Tags (disabled placeholder) */}
            <FormItem>
              <FormLabel>Tags</FormLabel>
              <Input
                disabled
                placeholder=""
                data-testid="create-job-tags-input"
              />
              <FormDescription>
                Tags will be editable once Cluster A ships.
              </FormDescription>
            </FormItem>

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isPending}
                data-testid="create-job-cancel-btn"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isPending}
                data-testid="create-job-submit-btn"
              >
                {isPending ? 'Creating…' : 'Create Job'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
