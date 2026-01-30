import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
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
        className="p-6 space-y-6"
        data-testid="job-form"
      >
        {/* Customer Section */}
        {!customerId && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
              Customer
            </h3>
            <FormField
              control={form.control}
              name="customer_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-slate-700">Customer *</FormLabel>
                  <FormControl>
                    <SearchableCustomerDropdown
                      value={field.value}
                      onChange={field.onChange}
                      disabled={isEditing}
                      data-testid="customer-dropdown"
                    />
                  </FormControl>
                  <FormDescription className="text-xs text-slate-500">
                    {isEditing
                      ? 'Customer cannot be changed after job creation'
                      : 'Search and select the customer for this job'}
                  </FormDescription>
                  <FormMessage className="text-sm text-red-500 mt-1" data-testid="validation-error" />
                </FormItem>
              )}
            />
          </div>
        )}

        {/* Job Details Section */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
            Job Details
          </h3>
          
          {/* Job Type */}
          <FormField
            control={form.control}
            name="job_type"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-sm font-medium text-slate-700">Job Type *</FormLabel>
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
                <FormMessage className="text-sm text-red-500 mt-1" data-testid="validation-error" />
              </FormItem>
            )}
          />

          {/* Description - using Textarea with teal focus ring */}
          <FormField
            control={form.control}
            name="description"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-sm font-medium text-slate-700">Description</FormLabel>
                <FormControl>
                  <Textarea
                    {...field}
                    value={field.value || ''}
                    placeholder="Job description and notes"
                    className="min-h-[100px]"
                    data-testid="description-input"
                  />
                </FormControl>
                <FormMessage className="text-sm text-red-500 mt-1" data-testid="validation-error" />
              </FormItem>
            )}
          />
        </div>

        {/* Priority & Staffing Section */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
            Priority & Staffing
          </h3>
          
          <div className="grid grid-cols-2 gap-4">
            {/* Priority Level */}
            <FormField
              control={form.control}
              name="priority_level"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-slate-700">Priority</FormLabel>
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
                  <FormMessage className="text-sm text-red-500 mt-1" data-testid="validation-error" />
                </FormItem>
              )}
            />

            {/* Staffing Required */}
            <FormField
              control={form.control}
              name="staffing_required"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-slate-700">Staff Required</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min={1}
                      value={field.value || 1}
                      onChange={(e) => field.onChange(parseInt(e.target.value) || 1)}
                      data-testid="staffing-input"
                    />
                  </FormControl>
                  <FormMessage className="text-sm text-red-500 mt-1" data-testid="validation-error" />
                </FormItem>
              )}
            />
          </div>
        </div>

        {/* Scheduling & Pricing Section */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
            Scheduling & Pricing
          </h3>
          
          <div className="grid grid-cols-2 gap-4">
            {/* Estimated Duration */}
            <FormField
              control={form.control}
              name="estimated_duration_minutes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-slate-700">Duration (minutes)</FormLabel>
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
                  <FormMessage className="text-sm text-red-500 mt-1" data-testid="validation-error" />
                </FormItem>
              )}
            />

            {/* Quoted Amount - with currency formatting */}
            <FormField
              control={form.control}
              name="quoted_amount"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-slate-700">Quoted Amount ($)</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">$</span>
                      <Input
                        type="number"
                        min={0}
                        step="0.01"
                        value={field.value ?? ''}
                        onChange={(e) =>
                          field.onChange(e.target.value ? parseFloat(e.target.value) : null)
                        }
                        placeholder="0.00"
                        className="pl-7"
                        data-testid="amount-input"
                      />
                    </div>
                  </FormControl>
                  <FormMessage className="text-sm text-red-500 mt-1" data-testid="validation-error" />
                </FormItem>
              )}
            />
          </div>
        </div>

        {/* Source & Options Section */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
            Source & Options
          </h3>
          
          {/* Source */}
          <FormField
            control={form.control}
            name="source"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-sm font-medium text-slate-700">Lead Source</FormLabel>
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
                <FormMessage className="text-sm text-red-500 mt-1" data-testid="validation-error" />
              </FormItem>
            )}
          />

          {/* Weather Sensitive - using Checkbox component with teal checked state */}
          <FormField
            control={form.control}
            name="weather_sensitive"
            render={({ field }) => (
              <FormItem className="flex items-center gap-3 space-y-0">
                <FormControl>
                  <Checkbox
                    checked={field.value}
                    onCheckedChange={field.onChange}
                    data-testid="weather-checkbox"
                  />
                </FormControl>
                <Label className="text-sm font-medium text-slate-700 cursor-pointer">
                  Weather Sensitive
                </Label>
              </FormItem>
            )}
          />
        </div>

        {/* Form Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
          {onCancel && (
            <Button 
              type="button" 
              variant="outline" 
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
            {isPending ? 'Saving...' : isEditing ? 'Update Job' : 'Create Job'}
          </Button>
        </div>
      </form>
    </Form>
  );
}
