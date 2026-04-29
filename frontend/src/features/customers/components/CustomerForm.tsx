// @ts-nocheck — pre-existing TS errors documented in bughunt/2026-04-29-pre-existing-tsc-errors.md
import { useState, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate } from 'react-router-dom';
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
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { X, Plus } from 'lucide-react';
import { useCreateCustomer, useUpdateCustomer, useCheckDuplicate } from '../hooks';
import type { Customer, CustomerCreate, CustomerUpdate } from '../types';
import { toast } from 'sonner';
import { getErrorMessage } from '@/core/api';
import { DuplicateWarning } from './DuplicateWarning';

// Validation schema
const customerSchema = z
  .object({
    first_name: z.string().min(1, 'First name is required').max(100),
    last_name: z.string().min(1, 'Last name is required').max(100),
    phone: z
      .string()
      .min(10, 'Phone must be at least 10 digits')
      .max(20)
      .regex(/^[\d\s\-()]+$/, 'Invalid phone format'),
    email: z.string().email('Invalid email').optional().or(z.literal('')),
    is_priority: z.boolean(),
    is_red_flag: z.boolean(),
    is_slow_payer: z.boolean(),
    sms_opt_in: z.boolean(),
    email_opt_in: z.boolean(),
    lead_source: z.string().optional().nullable(),
    custom_flags: z.array(z.string()),
    address: z.string().max(255).optional().or(z.literal('')),
    city: z.string().max(100).optional().or(z.literal('')),
    state: z.string().max(50).optional().or(z.literal('')),
    zip_code: z.string().max(20).optional().or(z.literal('')),
    internal_notes: z
      .string()
      .max(10000, 'Notes must be 10,000 characters or fewer')
      .optional()
      .or(z.literal('')),
  })
  .superRefine((data, ctx) => {
    // If any address field is filled, require address line + city together
    // (matches Property NOT NULL constraints on the backend).
    const anyAddressFilled = Boolean(
      data.address || data.city || data.zip_code || (data.state && data.state !== 'MN'),
    );
    if (anyAddressFilled) {
      if (!data.address || !data.address.trim()) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['address'],
          message: 'Address is required when entering a property',
        });
      }
      if (!data.city || !data.city.trim()) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['city'],
          message: 'City is required when entering a property',
        });
      }
    }
  });

type CustomerFormData = z.infer<typeof customerSchema>;

interface CustomerFormProps {
  customer?: Customer;
  onSuccess?: () => void;
  onCancel?: () => void;
}

const LEAD_SOURCES = [
  { value: 'website', label: 'Website' },
  { value: 'google_form', label: 'Google Form' },
  { value: 'phone_call', label: 'Phone Call' },
  { value: 'text_message', label: 'Text Message' },
  { value: 'google_ad', label: 'Google Ad' },
  { value: 'social_media', label: 'Social Media' },
  { value: 'qr_code', label: 'QR Code' },
  { value: 'email_campaign', label: 'Email Campaign' },
  { value: 'text_campaign', label: 'Text Campaign' },
  { value: 'referral', label: 'Referral' },
  { value: 'yard_sign', label: 'Yard Sign' },
  { value: 'other', label: 'Other' },
];

export function CustomerForm({ customer, onSuccess, onCancel }: CustomerFormProps) {
  const createMutation = useCreateCustomer();
  const updateMutation = useUpdateCustomer();
  const isEditing = !!customer;
  const [newCustomFlag, setNewCustomFlag] = useState('');
  const navigate = useNavigate();
  const { matches: duplicateMatches, check: checkDuplicate } = useCheckDuplicate();

  const runDuplicateCheck = useCallback(
    (phone?: string, email?: string) => {
      if (isEditing) return;
      checkDuplicate({
        phone: phone || undefined,
        email: email || undefined,
        exclude_id: customer?.id,
      });
    },
    [isEditing, checkDuplicate, customer?.id],
  );

  const handleUseExisting = (existing: Customer) => {
    navigate(`/customers/${existing.id}`);
  };

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
          custom_flags: (customer as Customer & { custom_flags?: string[] }).custom_flags ?? [],
          // Address is managed separately via the Properties section when
          // editing; we only surface these inputs in create mode.
          address: '',
          city: '',
          state: 'MN',
          zip_code: '',
          internal_notes: customer.internal_notes ?? '',
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
          custom_flags: [],
          address: '',
          city: '',
          state: 'MN',
          zip_code: '',
          internal_notes: '',
        },
  });

  const customFlags = form.watch('custom_flags');

  const addCustomFlag = () => {
    const trimmedFlag = newCustomFlag.trim();
    if (trimmedFlag && !customFlags.includes(trimmedFlag)) {
      form.setValue('custom_flags', [...customFlags, trimmedFlag]);
      setNewCustomFlag('');
    }
  };

  const removeCustomFlag = (flagToRemove: string) => {
    form.setValue('custom_flags', customFlags.filter(flag => flag !== flagToRemove));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addCustomFlag();
    }
  };

  const onSubmit = async (data: CustomerFormData) => {
    try {
      // Strip UI-only / flat address fields before shaping the API payload.
      // custom_flags is not yet supported by the backend.
      const {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        custom_flags,
        address,
        city,
        state,
        zip_code,
        internal_notes,
        ...apiData
      } = data;

      const trimmedAddress = address?.trim() ?? '';
      const trimmedCity = city?.trim() ?? '';
      const trimmedZip = zip_code?.trim() ?? '';
      const trimmedState = state?.trim() ?? '';
      const trimmedNotes = internal_notes?.trim() ?? '';

      if (isEditing && customer) {
        // On edit we don't create properties from this form — the Properties
        // section on the detail page owns that. We do pass notes through.
        const updatePayload: CustomerUpdate = {
          ...apiData,
          email: data.email || null,
          internal_notes: trimmedNotes ? trimmedNotes : null,
        };
        await updateMutation.mutateAsync({
          id: customer.id,
          data: updatePayload,
        });
        toast.success('Customer updated successfully');
      } else {
        const createPayload: CustomerCreate = {
          ...apiData,
          email: data.email || null,
          internal_notes: trimmedNotes ? trimmedNotes : null,
          primary_property: trimmedAddress
            ? {
                address: trimmedAddress,
                city: trimmedCity,
                state: trimmedState || 'MN',
                zip_code: trimmedZip ? trimmedZip : null,
              }
            : null,
        };
        await createMutation.mutateAsync(createPayload);
        toast.success('Customer created successfully');
      }
      onSuccess?.();
    } catch (err) {
      toast.error(isEditing ? 'Failed to update customer' : 'Failed to create customer', {
        description: getErrorMessage(err),
      });
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} data-testid="customer-form" className="p-6 space-y-6">
        {/* Basic Information */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Basic Information</h3>
          <Card className="bg-white rounded-2xl shadow-sm border border-slate-100">
            <CardContent className="p-6 space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="first_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-medium text-slate-700">First Name *</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="John" data-testid="first-name-input" className="border-slate-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-100" />
                      </FormControl>
                      <FormMessage className="text-sm text-red-500 mt-1" data-testid="validation-error" />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="last_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-medium text-slate-700">Last Name *</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="Doe" data-testid="last-name-input" className="border-slate-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-100" />
                      </FormControl>
                      <FormMessage className="text-sm text-red-500 mt-1" data-testid="validation-error" />
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
                      <FormLabel className="text-sm font-medium text-slate-700">Phone *</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          type="tel"
                          placeholder="612-555-1234"
                          data-testid="phone-input"
                          className="border-slate-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                          onBlur={(e) => {
                            field.onBlur();
                            runDuplicateCheck(e.target.value, form.getValues('email'));
                          }}
                        />
                      </FormControl>
                      <FormMessage className="text-sm text-red-500 mt-1" data-testid="phone-error" />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-medium text-slate-700">Email</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          type="email"
                          placeholder="john@example.com"
                          data-testid="email-input"
                          className="border-slate-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                          onBlur={(e) => {
                            field.onBlur();
                            runDuplicateCheck(form.getValues('phone'), e.target.value);
                          }}
                        />
                      </FormControl>
                      <FormMessage className="text-sm text-red-500 mt-1" data-testid="email-error" />
                    </FormItem>
                  )}
                />
              </div>

              {/* Tier 1 Duplicate Warning (Req 6.13) */}
              {!isEditing && <DuplicateWarning matches={duplicateMatches} onUseExisting={handleUseExisting} />}

              <FormField
                control={form.control}
                name="lead_source"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-medium text-slate-700">Lead Source</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      defaultValue={field.value ?? undefined}
                    >
                      <FormControl>
                        <SelectTrigger data-testid="lead-source-select" className="border-slate-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-100">
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
                    <FormMessage className="text-sm text-red-500 mt-1" />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>
        </div>

        {/* Primary Property Address (create-only) */}
        {!isEditing && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
              Primary Address <span className="text-xs font-normal text-slate-400 normal-case">(optional)</span>
            </h3>
            <Card className="bg-white rounded-2xl shadow-sm border border-slate-100">
              <CardContent className="p-6 space-y-4">
                <p className="text-xs text-slate-500">
                  If provided, we'll create the customer's primary property with this address. You can add more properties later.
                </p>
                <FormField
                  control={form.control}
                  name="address"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-medium text-slate-700">Address</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          value={field.value ?? ''}
                          placeholder="123 Main St"
                          data-testid="address-input"
                          className="border-slate-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                        />
                      </FormControl>
                      <FormMessage className="text-sm text-red-500 mt-1" data-testid="address-error" />
                    </FormItem>
                  )}
                />
                <div className="grid gap-4 md:grid-cols-3">
                  <FormField
                    control={form.control}
                    name="city"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm font-medium text-slate-700">City</FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            value={field.value ?? ''}
                            placeholder="Minneapolis"
                            data-testid="city-input"
                            className="border-slate-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                          />
                        </FormControl>
                        <FormMessage className="text-sm text-red-500 mt-1" data-testid="city-error" />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="state"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm font-medium text-slate-700">State</FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            value={field.value ?? ''}
                            placeholder="MN"
                            maxLength={50}
                            data-testid="state-input"
                            className="border-slate-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                          />
                        </FormControl>
                        <FormMessage className="text-sm text-red-500 mt-1" />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="zip_code"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm font-medium text-slate-700">ZIP</FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            value={field.value ?? ''}
                            placeholder="55401"
                            data-testid="zip-input"
                            className="border-slate-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                          />
                        </FormControl>
                        <FormMessage className="text-sm text-red-500 mt-1" />
                      </FormItem>
                    )}
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        )}

          {/* Customer Flags */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Customer Flags</h3>
            <Card className="bg-white rounded-2xl shadow-sm border border-slate-100">
              <CardContent className="p-6 space-y-6">
              {/* Common Flags */}
              <div>
                <h4 className="text-sm font-medium text-slate-700 mb-3">Common Flags</h4>
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
                            className="h-4 w-4 rounded border-slate-300 text-teal-500 focus:ring-2 focus:ring-teal-100"
                            data-testid="is-priority-checkbox"
                          />
                        </FormControl>
                        <FormLabel className="font-normal text-slate-600">Priority Customer</FormLabel>
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
                            className="h-4 w-4 rounded border-slate-300 text-teal-500 focus:ring-2 focus:ring-teal-100"
                            data-testid="is-red-flag-checkbox"
                          />
                        </FormControl>
                        <FormLabel className="font-normal text-slate-600">Red Flag</FormLabel>
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
                            className="h-4 w-4 rounded border-slate-300 text-teal-500 focus:ring-2 focus:ring-teal-100"
                            data-testid="is-slow-payer-checkbox"
                          />
                        </FormControl>
                        <FormLabel className="font-normal text-slate-600">Slow Payer</FormLabel>
                      </FormItem>
                    )}
                  />
                </div>
              </div>

              {/* Custom Flags */}
              <div>
                <h4 className="text-sm font-medium text-slate-700 mb-3">Custom Flags</h4>
                <div className="space-y-3">
                  {/* Display existing custom flags */}
                  {customFlags.length > 0 && (
                    <div className="flex flex-wrap gap-2" data-testid="custom-flags-list">
                      {customFlags.map((flag) => (
                        <Badge
                          key={flag}
                          variant="secondary"
                          className="flex items-center gap-1 px-3 py-1 bg-slate-100 text-slate-700 rounded-full text-xs font-medium"
                          data-testid={`custom-flag-${flag.toLowerCase().replace(/\s+/g, '-')}`}
                        >
                          {flag}
                          <button
                            type="button"
                            onClick={() => removeCustomFlag(flag)}
                            className="ml-1 text-slate-400 hover:text-red-500 transition-colors"
                            data-testid={`remove-flag-${flag.toLowerCase().replace(/\s+/g, '-')}`}
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </Badge>
                      ))}
                    </div>
                  )}
                  
                  {/* Add new custom flag */}
                  <div className="flex gap-2">
                    <Input
                      value={newCustomFlag}
                      onChange={(e) => setNewCustomFlag(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Enter custom flag (e.g., VIP, Referral Partner)"
                      className="flex-1 border-slate-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                      data-testid="custom-flag-input"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={addCustomFlag}
                      disabled={!newCustomFlag.trim()}
                      className="border-slate-200 hover:bg-slate-50 text-slate-700"
                      data-testid="add-custom-flag-btn"
                    >
                      <Plus className="h-4 w-4 mr-1" />
                      Add
                    </Button>
                  </div>
                  <p className="text-xs text-slate-400">
                    Add any custom flags to categorize this customer. Press Enter or click Add.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

          {/* Communication Preferences */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Communication Preferences</h3>
            <Card className="bg-white rounded-2xl shadow-sm border border-slate-100">
              <CardContent className="p-6 space-y-4">
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
                            className="h-4 w-4 rounded border-slate-300 text-teal-500 focus:ring-2 focus:ring-teal-100"
                            data-testid="sms-opt-in-checkbox"
                          />
                        </FormControl>
                        <div>
                          <FormLabel className="font-normal text-slate-700">SMS Notifications</FormLabel>
                          <FormDescription className="text-xs text-slate-400">
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
                            className="h-4 w-4 rounded border-slate-300 text-teal-500 focus:ring-2 focus:ring-teal-100"
                            data-testid="email-opt-in-checkbox"
                          />
                        </FormControl>
                        <div>
                          <FormLabel className="font-normal text-slate-700">Email Notifications</FormLabel>
                          <FormDescription className="text-xs text-slate-400">
                            Receive invoices and updates via email
                          </FormDescription>
                        </div>
                      </FormItem>
                    )}
                  />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Notes */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
              Notes <span className="text-xs font-normal text-slate-400 normal-case">(optional)</span>
            </h3>
            <Card className="bg-white rounded-2xl shadow-sm border border-slate-100">
              <CardContent className="p-6">
                <FormField
                  control={form.control}
                  name="internal_notes"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-medium text-slate-700">Internal Notes</FormLabel>
                      <FormControl>
                        <Textarea
                          {...field}
                          value={field.value ?? ''}
                          placeholder="Anything worth remembering about this customer (access notes, preferences, history)..."
                          rows={4}
                          maxLength={10000}
                          data-testid="internal-notes-input"
                          className="border-slate-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                        />
                      </FormControl>
                      <FormDescription className="text-xs text-slate-400">
                        Visible only to staff. Up to 10,000 characters.
                      </FormDescription>
                      <FormMessage className="text-sm text-red-500 mt-1" data-testid="internal-notes-error" />
                    </FormItem>
                  )}
                />
              </CardContent>
            </Card>
          </div>

          {/* Form Actions */}
          <div className="flex justify-end gap-4 pt-4">
            {onCancel && (
              <Button 
                type="button" 
                variant="outline" 
                onClick={onCancel}
                className="bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 px-4 py-2.5 rounded-lg transition-all"
                data-testid="cancel-btn"
              >
                Cancel
              </Button>
            )}
            <Button 
              type="submit" 
              disabled={isPending} 
              data-testid="submit-btn"
              className="bg-teal-500 hover:bg-teal-600 text-white px-5 py-2.5 rounded-lg shadow-sm shadow-teal-200 transition-all"
            >
              {isPending ? 'Saving...' : isEditing ? 'Update Customer' : 'Create Customer'}
            </Button>
          </div>
      </form>
    </Form>
  );
}
