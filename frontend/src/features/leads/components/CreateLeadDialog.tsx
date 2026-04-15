/**
 * CreateLeadDialog component.
 *
 * Dialog for manually creating a new lead via the CRM interface.
 * Uses React Hook Form + Zod for validation. Name and phone are required.
 *
 * Validates: Requirement 7.1-7.5
 */

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { UserPlus, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
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
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';

import { useCreateManualLead } from '../hooks';
import { LEAD_SITUATION_LABELS } from '../types';
import type { LeadSituation } from '../types';

const createLeadSchema = z.object({
  name: z.string().min(1, 'Name is required').max(200),
  phone: z
    .string()
    .min(7, 'Phone must be at least 7 digits')
    .max(20)
    .regex(/^\+?[\d\s\-().]+$/, 'Invalid phone format'),
  email: z.string().email('Invalid email').optional().or(z.literal('')),
  address: z.string().max(500).optional().or(z.literal('')),
  city: z.string().max(100).optional().or(z.literal('')),
  state: z.string().max(2).optional().or(z.literal('')),
  zip_code: z.string().max(10).optional().or(z.literal('')),
  situation: z.enum([
    'new_system',
    'upgrade',
    'repair',
    'exploring',
    'winterization',
    'seasonal_maintenance',
  ]),
  notes: z.string().max(1000).optional().or(z.literal('')),
});

type CreateLeadFormData = z.infer<typeof createLeadSchema>;

interface CreateLeadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateLeadDialog({ open, onOpenChange }: CreateLeadDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-lg bg-white rounded-2xl shadow-xl"
        data-testid="create-lead-dialog"
      >
        {open && <CreateLeadForm onOpenChange={onOpenChange} />}
      </DialogContent>
    </Dialog>
  );
}

function CreateLeadForm({ onOpenChange }: { onOpenChange: (open: boolean) => void }) {
  const createMutation = useCreateManualLead();

  const form = useForm<CreateLeadFormData>({
    resolver: zodResolver(createLeadSchema),
    defaultValues: {
      name: '',
      phone: '',
      email: '',
      address: '',
      city: '',
      state: '',
      zip_code: '',
      situation: 'exploring',
      notes: '',
    },
  });

  const onSubmit = async (data: CreateLeadFormData) => {
    try {
      await createMutation.mutateAsync({
        name: data.name,
        phone: data.phone,
        email: data.email || null,
        address: data.address || null,
        city: data.city || null,
        state: data.state || null,
        zip_code: data.zip_code || null,
        situation: data.situation as LeadSituation,
        notes: data.notes || null,
      });

      toast.success('Lead Created', {
        description: `${data.name} has been added to your leads.`,
      });

      onOpenChange(false);
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : 'Failed to create lead';
      toast.error('Creation Failed', {
        description: message,
      });
    }
  };

  return (
    <>
      <DialogHeader className="pb-2">
        <DialogTitle className="flex items-center gap-2 text-lg font-bold text-slate-800">
          <UserPlus className="h-5 w-5 text-teal-600" />
          Add New Lead
        </DialogTitle>
        <DialogDescription className="text-slate-500 text-sm">
          Manually create a lead from a phone call, walk-in, or other offline source.
        </DialogDescription>
      </DialogHeader>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4 py-2" data-testid="create-lead-form">
          {/* Name & Phone (required) */}
          <div className="grid grid-cols-2 gap-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-slate-700">
                    Name <span className="text-red-500">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Full name"
                      data-testid="create-lead-name"
                      className="bg-slate-50 border-slate-200 rounded-lg"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="phone"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-slate-700">
                    Phone <span className="text-red-500">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="(555) 123-4567"
                      data-testid="create-lead-phone"
                      className="bg-slate-50 border-slate-200 rounded-lg"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Email */}
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
                    placeholder="email@example.com"
                    data-testid="create-lead-email"
                    className="bg-slate-50 border-slate-200 rounded-lg"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Address */}
          <FormField
            control={form.control}
            name="address"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-sm font-medium text-slate-700">Address</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    placeholder="Street address"
                    data-testid="create-lead-address"
                    className="bg-slate-50 border-slate-200 rounded-lg"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* City, State, Zip */}
          <div className="grid grid-cols-3 gap-4">
            <FormField
              control={form.control}
              name="city"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-slate-700">City</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="City"
                      data-testid="create-lead-city"
                      className="bg-slate-50 border-slate-200 rounded-lg"
                    />
                  </FormControl>
                  <FormMessage />
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
                      placeholder="MN"
                      maxLength={2}
                      data-testid="create-lead-state"
                      className="bg-slate-50 border-slate-200 rounded-lg"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="zip_code"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-slate-700">Zip</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="55401"
                      data-testid="create-lead-zip"
                      className="bg-slate-50 border-slate-200 rounded-lg"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Situation */}
          <FormField
            control={form.control}
            name="situation"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-sm font-medium text-slate-700">Situation</FormLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger data-testid="create-lead-situation" className="bg-slate-50 border-slate-200 rounded-lg">
                      <SelectValue placeholder="Select situation" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {(Object.entries(LEAD_SITUATION_LABELS) as [LeadSituation, string][]).map(
                      ([value, label]) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      )
                    )}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Notes */}
          <FormField
            control={form.control}
            name="notes"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-sm font-medium text-slate-700">Notes</FormLabel>
                <FormControl>
                  <Textarea
                    {...field}
                    placeholder="Any additional notes..."
                    rows={3}
                    data-testid="create-lead-notes"
                    className="bg-slate-50 border-slate-200 rounded-lg resize-none"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={createMutation.isPending}
              className="bg-white hover:bg-slate-50 border-slate-200 text-slate-700"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              data-testid="create-lead-submit"
              disabled={createMutation.isPending}
              className="bg-teal-500 hover:bg-teal-600 text-white shadow-sm shadow-teal-200"
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <UserPlus className="mr-2 h-4 w-4" />
                  Add Lead
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </Form>
    </>
  );
}

export default CreateLeadDialog;
