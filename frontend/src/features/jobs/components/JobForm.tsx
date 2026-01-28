import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
import { SearchableCustomerDropdown } from './SearchableCustomerDropdown';
import type { Job, JobCreate, JobUpdate, JobSource } from '../types';

// Form validation schema - using simple types without coerce
const jobFormSchema = z.object({
  customer_id: z.string().min(1, 'Please select a customer'),
  property_id: z.string().optional().nullable(),
  service_offering_id: z.string().optional().nullable(),
  job_type: z.string().min(1, 'Job type is required'),
  description: z.string().optional().nullable(),
  estimated_duration_minutes: z.number().positive().optional().nullable(),
  priority_level: z.number().min(0).max(2),
  weather_sensitive: z.boolean(),
  staffing_required: z.number().min(1),
  quoted_amount: z.number().nonnegative().optional().nullable(),
  source: z.enum(['website', 'google', 'referral', 'phone', 'partner']).optional().nullable(),
});

type JobFormData = z.infer<typeof jobFormSchema>;

interface JobFormProps {
  job?: Job;
  customerId?: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function JobForm({ job, customerId, onSuccess, onCancel }: JobFormProps) {
  const createMutation = useCreateJob();
  const updateMutation = useUpdateJob();
  const isEditing = !!job;

  const form = useForm<JobFormData>({
    resolver: zodResolver(jobFormSchema),
    defaultValues: {
      customer_id: job?.customer_id || customerId || '',
      property_id: job?.property_id || null,
      service_offering_id: job?.service_offering_id || null,
      job_type: job?.job_type || '',
      description: job?.description || '',
      estimated_duration_minutes: job?.estimated_duration_minutes || null,
      priority_level: job?.priority_level ?? 0,
      weather_sensitive: job?.weather_sensitive ?? false,
      staffing_required: job?.staffing_required ?? 1,
      quoted_amount: job?.quoted_amount || null,
      source: job?.source || null,
    },
  });

  const onSubmit = async (data: JobFormData) => {
    try {
      if (isEditing && job) {
        const updateData: JobUpdate = {
          property_id: data.property_id,
          service_offering_id: data.service_offering_id,
          job_type: data.job_type,
          description: data.description,
          estimated_duration_minutes: data.estimated_duration_minutes,
          priority_level: data.priority_level,
          weather_sensitive: data.weather_sensitive,
          staffing_required: data.staffing_required,
          quoted_amount: data.quoted_amount,
          source: data.source as JobSource | null,
        };
        await updateMutation.mutateAsync({ id: job.id, data: updateData });
      } else {
        const createData: JobCreate = {
          customer_id: data.customer_id,
          property_id: data.property_id,
          service_offering_id: data.service_offering_id,
          job_type: data.job_type,
          description: data.description,
          estimated_duration_minutes: data.estimated_duration_minutes,
          priority_level: data.priority_level,
          weather_sensitive: data.weather_sensitive,
          staffing_required: data.staffing_required,
          quoted_amount: data.quoted_amount,
          source: data.source as JobSource | null,
        };
        await createMutation.mutateAsync(createData);
      }
      onSuccess?.();
    } catch (error) {
      console.error('Failed to save job:', error);
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="space-y-6"
        data-testid="job-form"
      >
        {/* Customer ID - required for new jobs, read-only when editing */}
        {!customerId && (
          <FormField
            control={form.control}
            name="customer_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Customer *</FormLabel>
                <FormControl>
                  <SearchableCustomerDropdown
                    value={field.value}
                    onChange={field.onChange}
                    disabled={isEditing}
                  />
                </FormControl>
                <FormDescription>
                  {isEditing
                    ? 'Customer cannot be changed after job creation'
                    : 'Search and select the customer for this job'}
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
        )}

        {/* Job Type */}
        <FormField
          control={form.control}
          name="job_type"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Job Type *</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger data-testid="job-type-select">
                    <SelectValue placeholder="Select job type" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
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

        {/* Description */}
        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  value={field.value || ''}
                  placeholder="Job description and notes"
                  data-testid="description-input"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid grid-cols-2 gap-4">
          {/* Priority Level */}
          <FormField
            control={form.control}
            name="priority_level"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Priority</FormLabel>
                <Select
                  onValueChange={(value) => field.onChange(parseInt(value))}
                  defaultValue={field.value?.toString()}
                >
                  <FormControl>
                    <SelectTrigger data-testid="priority-select">
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

          {/* Staffing Required */}
          <FormField
            control={form.control}
            name="staffing_required"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Staff Required</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    min={1}
                    value={field.value || 1}
                    onChange={(e) => field.onChange(parseInt(e.target.value) || 1)}
                    data-testid="staffing-input"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* Estimated Duration */}
          <FormField
            control={form.control}
            name="estimated_duration_minutes"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Duration (minutes)</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    min={1}
                    value={field.value ?? ''}
                    onChange={(e) =>
                      field.onChange(e.target.value ? parseInt(e.target.value) : null)
                    }
                    placeholder="e.g., 60"
                    data-testid="duration-input"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Quoted Amount */}
          <FormField
            control={form.control}
            name="quoted_amount"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Quoted Amount ($)</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    min={0}
                    step="0.01"
                    value={field.value ?? ''}
                    onChange={(e) =>
                      field.onChange(e.target.value ? parseFloat(e.target.value) : null)
                    }
                    placeholder="e.g., 150.00"
                    data-testid="amount-input"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* Source */}
        <FormField
          control={form.control}
          name="source"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Lead Source</FormLabel>
              <Select
                onValueChange={field.onChange}
                defaultValue={field.value || undefined}
              >
                <FormControl>
                  <SelectTrigger data-testid="source-select">
                    <SelectValue placeholder="Select source" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="website">Website</SelectItem>
                  <SelectItem value="google">Google</SelectItem>
                  <SelectItem value="referral">Referral</SelectItem>
                  <SelectItem value="phone">Phone</SelectItem>
                  <SelectItem value="partner">Partner</SelectItem>
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Weather Sensitive */}
        <FormField
          control={form.control}
          name="weather_sensitive"
          render={({ field }) => (
            <FormItem className="flex items-center gap-2">
              <FormControl>
                <input
                  type="checkbox"
                  checked={field.value}
                  onChange={field.onChange}
                  className="h-4 w-4 rounded border-gray-300"
                  data-testid="weather-checkbox"
                />
              </FormControl>
              <Label className="!mt-0">Weather Sensitive</Label>
            </FormItem>
          )}
        />

        {/* Form Actions */}
        <div className="flex justify-end gap-2">
          {onCancel && (
            <Button type="button" variant="outline" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button type="submit" disabled={isPending} data-testid="submit-btn">
            {isPending ? 'Saving...' : isEditing ? 'Update Job' : 'Create Job'}
          </Button>
        </div>
      </form>
    </Form>
  );
}
