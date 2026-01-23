import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useCreateCustomer, useUpdateCustomer } from '../hooks';
import type { Customer, CustomerCreate, CustomerUpdate } from '../types';
import { toast } from 'sonner';

// Validation schema
const customerSchema = z.object({
  first_name: z.string().min(1, 'First name is required').max(100),
  last_name: z.string().min(1, 'Last name is required').max(100),
  phone: z
    .string()
    .min(10, 'Phone must be at least 10 digits')
    .max(20)
    .regex(/^[\d\s\-()]+$/, 'Invalid phone format'),
  email: z.string().email('Invalid email').optional().or(z.literal('')),
  is_priority: z.boolean().default(false),
  is_red_flag: z.boolean().default(false),
  is_slow_payer: z.boolean().default(false),
  sms_opt_in: z.boolean().default(false),
  email_opt_in: z.boolean().default(false),
  lead_source: z.string().optional().nullable(),
});

type CustomerFormData = z.infer<typeof customerSchema>;

interface CustomerFormProps {
  customer?: Customer;
  onSuccess?: () => void;
  onCancel?: () => void;
}

const LEAD_SOURCES = [
  { value: 'website', label: 'Website' },
  { value: 'google', label: 'Google' },
  { value: 'referral', label: 'Referral' },
  { value: 'facebook', label: 'Facebook' },
  { value: 'nextdoor', label: 'Nextdoor' },
  { value: 'yard_sign', label: 'Yard Sign' },
  { value: 'repeat', label: 'Repeat Customer' },
  { value: 'other', label: 'Other' },
];

export function CustomerForm({ customer, onSuccess, onCancel }: CustomerFormProps) {
  const createMutation = useCreateCustomer();
  const updateMutation = useUpdateCustomer();
  const isEditing = !!customer;

  const form = useForm<CustomerFormData>({
    resolver: zodResolver(customerSchema),
    defaultValues: customer
      ? {
          first_name: customer.first_name,
          last_name: customer.last_name,
          phone: customer.phone,
          email: customer.email ?? '',
          is_priority: customer.is_priority,
          is_red_flag: customer.is_red_flag,
          is_slow_payer: customer.is_slow_payer,
          sms_opt_in: customer.sms_opt_in,
          email_opt_in: customer.email_opt_in,
          lead_source: customer.lead_source,
        }
      : {
          first_name: '',
          last_name: '',
          phone: '',
          email: '',
          is_priority: false,
          is_red_flag: false,
          is_slow_payer: false,
          sms_opt_in: false,
          email_opt_in: false,
          lead_source: null,
        },
  });

  const onSubmit = async (data: CustomerFormData) => {
    try {
      // Clean up email - convert empty string to null
      const cleanedData = {
        ...data,
        email: data.email || null,
      };

      if (isEditing && customer) {
        await updateMutation.mutateAsync({
          id: customer.id,
          data: cleanedData as CustomerUpdate,
        });
        toast.success('Customer updated successfully');
      } else {
        await createMutation.mutateAsync(cleanedData as CustomerCreate);
        toast.success('Customer created successfully');
      }
      onSuccess?.();
    } catch {
      toast.error(isEditing ? 'Failed to update customer' : 'Failed to create customer');
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} data-testid="customer-form">
        <div className="space-y-6">
          {/* Basic Information */}
          <Card>
            <CardHeader>
              <CardTitle>Basic Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="first_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>First Name *</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="John" data-testid="first-name-input" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="last_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Last Name *</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="Doe" data-testid="last-name-input" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="phone"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Phone *</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          type="tel"
                          placeholder="612-555-1234"
                          data-testid="phone-input"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Email</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          type="email"
                          placeholder="john@example.com"
                          data-testid="email-input"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="lead_source"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Lead Source</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      defaultValue={field.value ?? undefined}
                    >
                      <FormControl>
                        <SelectTrigger data-testid="lead-source-select">
                          <SelectValue placeholder="Select lead source" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {LEAD_SOURCES.map((source) => (
                          <SelectItem key={source.value} value={source.value}>
                            {source.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Customer Flags */}
          <Card>
            <CardHeader>
              <CardTitle>Customer Flags</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-3">
                <FormField
                  control={form.control}
                  name="is_priority"
                  render={({ field }) => (
                    <FormItem className="flex items-center space-x-2 space-y-0">
                      <FormControl>
                        <input
                          type="checkbox"
                          checked={field.value}
                          onChange={field.onChange}
                          className="h-4 w-4 rounded border-gray-300"
                          data-testid="is-priority-checkbox"
                        />
                      </FormControl>
                      <FormLabel className="font-normal">Priority Customer</FormLabel>
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="is_red_flag"
                  render={({ field }) => (
                    <FormItem className="flex items-center space-x-2 space-y-0">
                      <FormControl>
                        <input
                          type="checkbox"
                          checked={field.value}
                          onChange={field.onChange}
                          className="h-4 w-4 rounded border-gray-300"
                          data-testid="is-red-flag-checkbox"
                        />
                      </FormControl>
                      <FormLabel className="font-normal">Red Flag</FormLabel>
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="is_slow_payer"
                  render={({ field }) => (
                    <FormItem className="flex items-center space-x-2 space-y-0">
                      <FormControl>
                        <input
                          type="checkbox"
                          checked={field.value}
                          onChange={field.onChange}
                          className="h-4 w-4 rounded border-gray-300"
                          data-testid="is-slow-payer-checkbox"
                        />
                      </FormControl>
                      <FormLabel className="font-normal">Slow Payer</FormLabel>
                    </FormItem>
                  )}
                />
              </div>
            </CardContent>
          </Card>

          {/* Communication Preferences */}
          <Card>
            <CardHeader>
              <CardTitle>Communication Preferences</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="sms_opt_in"
                  render={({ field }) => (
                    <FormItem className="flex items-center space-x-2 space-y-0">
                      <FormControl>
                        <input
                          type="checkbox"
                          checked={field.value}
                          onChange={field.onChange}
                          className="h-4 w-4 rounded border-gray-300"
                          data-testid="sms-opt-in-checkbox"
                        />
                      </FormControl>
                      <div>
                        <FormLabel className="font-normal">SMS Notifications</FormLabel>
                        <FormDescription>
                          Receive appointment reminders via text
                        </FormDescription>
                      </div>
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="email_opt_in"
                  render={({ field }) => (
                    <FormItem className="flex items-center space-x-2 space-y-0">
                      <FormControl>
                        <input
                          type="checkbox"
                          checked={field.value}
                          onChange={field.onChange}
                          className="h-4 w-4 rounded border-gray-300"
                          data-testid="email-opt-in-checkbox"
                        />
                      </FormControl>
                      <div>
                        <FormLabel className="font-normal">Email Notifications</FormLabel>
                        <FormDescription>
                          Receive invoices and updates via email
                        </FormDescription>
                      </div>
                    </FormItem>
                  )}
                />
              </div>
            </CardContent>
          </Card>

          {/* Form Actions */}
          <div className="flex justify-end gap-4">
            {onCancel && (
              <Button type="button" variant="outline" onClick={onCancel}>
                Cancel
              </Button>
            )}
            <Button type="submit" disabled={isPending} data-testid="submit-btn">
              {isPending ? 'Saving...' : isEditing ? 'Update Customer' : 'Create Customer'}
            </Button>
          </div>
        </div>
      </form>
    </Form>
  );
}
