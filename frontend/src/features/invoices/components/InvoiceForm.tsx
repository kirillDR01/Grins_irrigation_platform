import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Plus, Trash2, CalendarIcon } from 'lucide-react';
import { format } from 'date-fns';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Calendar } from '@/components/ui/calendar';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { cn } from '@/lib/utils';
import { useCreateInvoice, useUpdateInvoice } from '../hooks/useInvoiceMutations';
import type { Invoice, InvoiceCreate, InvoiceUpdate, InvoiceLineItem } from '../types';

const lineItemSchema = z.object({
  description: z.string().min(1, 'Description is required'),
  quantity: z.number().positive('Quantity must be positive'),
  unit_price: z.number().nonnegative('Unit price must be non-negative'),
  total: z.number().nonnegative(),
});

const invoiceFormSchema = z.object({
  job_id: z.string().min(1, 'Job ID is required'),
  amount: z.number().positive('Amount must be positive'),
  late_fee_amount: z.number().nonnegative().optional(),
  due_date: z.string().min(1, 'Due date is required'),
  line_items: z.array(lineItemSchema).optional(),
  notes: z.string().optional(),
});

type InvoiceFormData = z.infer<typeof invoiceFormSchema>;

interface InvoiceFormProps {
  invoice?: Invoice;
  jobId?: string;
  defaultAmount?: number;
  defaultLineItems?: InvoiceLineItem[];
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function InvoiceForm({
  invoice,
  jobId,
  defaultAmount,
  defaultLineItems,
  onSuccess,
  onCancel,
}: InvoiceFormProps) {
  const createMutation = useCreateInvoice();
  const updateMutation = useUpdateInvoice();
  const isEditing = !!invoice;

  // Default due date is 14 days from now
  const defaultDueDate = new Date();
  defaultDueDate.setDate(defaultDueDate.getDate() + 14);
  const defaultDueDateStr = defaultDueDate.toISOString().split('T')[0];

  const form = useForm<InvoiceFormData>({
    resolver: zodResolver(invoiceFormSchema),
    defaultValues: {
      job_id: invoice?.job_id || jobId || '',
      amount: invoice?.amount || defaultAmount || 0,
      late_fee_amount: invoice?.late_fee_amount || 0,
      due_date: invoice?.due_date?.split('T')[0] || defaultDueDateStr,
      line_items: invoice?.line_items || defaultLineItems || [],
      notes: invoice?.notes || '',
    },
  });

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: 'line_items',
  });

  const addLineItem = () => {
    append({ description: '', quantity: 1, unit_price: 0, total: 0 });
  };

  const updateLineItemTotal = (index: number) => {
    const lineItems = form.getValues('line_items') || [];
    const item = lineItems[index];
    if (item) {
      const total = item.quantity * item.unit_price;
      form.setValue(`line_items.${index}.total`, total);
    }
  };

  const calculateTotalFromLineItems = () => {
    const lineItems = form.getValues('line_items') || [];
    const total = lineItems.reduce((sum, item) => sum + (item.total || 0), 0);
    form.setValue('amount', total);
  };

  const onSubmit = async (data: InvoiceFormData) => {
    try {
      if (isEditing && invoice) {
        const updateData: InvoiceUpdate = {
          amount: data.amount,
          late_fee_amount: data.late_fee_amount,
          due_date: data.due_date,
          line_items: data.line_items,
          notes: data.notes,
        };
        await updateMutation.mutateAsync({ id: invoice.id, data: updateData });
      } else {
        const createData: InvoiceCreate = {
          job_id: data.job_id,
          amount: data.amount,
          late_fee_amount: data.late_fee_amount,
          due_date: data.due_date,
          line_items: data.line_items,
          notes: data.notes,
        };
        await createMutation.mutateAsync(createData);
      }
      onSuccess?.();
    } catch (error) {
      console.error('Failed to save invoice:', error);
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="p-6 space-y-6"
        data-testid="invoice-form"
      >
        {/* Invoice Details Section */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
            Invoice Details
          </h3>

          {/* Job ID - hidden when editing or when jobId is provided */}
          {!isEditing && !jobId && (
            <FormField
              control={form.control}
              name="job_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-slate-700">Job ID *</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter job ID"
                      data-testid="job-id-input"
                    />
                  </FormControl>
                  <FormMessage className="text-sm text-red-500 mt-1" data-testid="validation-error" />
                </FormItem>
              )}
            />
          )}

          <div className="grid grid-cols-2 gap-4">
            {/* Amount */}
            <FormField
              control={form.control}
              name="amount"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-slate-700">Amount ($) *</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">$</span>
                      <Input
                        type="number"
                        min={0}
                        step="0.01"
                        value={field.value || ''}
                        onChange={(e) =>
                          field.onChange(e.target.value ? parseFloat(e.target.value) : 0)
                        }
                        placeholder="0.00"
                        className="pl-7"
                        data-testid="invoice-amount"
                      />
                    </div>
                  </FormControl>
                  <FormMessage className="text-sm text-red-500 mt-1" data-testid="validation-error" />
                </FormItem>
              )}
            />

            {/* Late Fee Amount */}
            <FormField
              control={form.control}
              name="late_fee_amount"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-slate-700">Late Fee ($)</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">$</span>
                      <Input
                        type="number"
                        min={0}
                        step="0.01"
                        value={field.value || ''}
                        onChange={(e) =>
                          field.onChange(e.target.value ? parseFloat(e.target.value) : 0)
                        }
                        placeholder="0.00"
                        className="pl-7"
                        data-testid="late-fee-input"
                      />
                    </div>
                  </FormControl>
                  <FormMessage className="text-sm text-red-500 mt-1" data-testid="validation-error" />
                </FormItem>
              )}
            />
          </div>
        </div>

        {/* Due Date Section */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
            Payment Terms
          </h3>
          <FormField
            control={form.control}
            name="due_date"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-sm font-medium text-slate-700">Due Date *</FormLabel>
                <FormControl>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        className={cn(
                          'w-full justify-start text-left font-normal border-slate-200 rounded-lg bg-white text-slate-700 text-sm hover:bg-slate-50 focus:border-teal-500 focus:ring-2 focus:ring-teal-100',
                          !field.value && 'text-slate-400'
                        )}
                        data-testid="due-date-input"
                      >
                        <CalendarIcon className="mr-2 h-4 w-4 text-slate-400" />
                        {field.value ? format(new Date(field.value), 'PPP') : 'Select due date'}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent
                      className="w-auto p-0 bg-white rounded-xl shadow-lg border border-slate-100"
                      align="start"
                      data-testid="due-date-calendar"
                    >
                      <Calendar
                        mode="single"
                        selected={field.value ? new Date(field.value) : undefined}
                        onSelect={(date) => {
                          if (date) {
                            field.onChange(date.toISOString().split('T')[0]);
                          }
                        }}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                </FormControl>
                <FormMessage className="text-sm text-red-500 mt-1" data-testid="validation-error" />
              </FormItem>
            )}
          />
        </div>

        {/* Line Items Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
              Line Items
            </h3>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={addLineItem}
              data-testid="add-line-item-btn"
            >
              <Plus className="h-4 w-4 mr-1" />
              Add Item
            </Button>
          </div>

          {fields.length > 0 && (
            <div className="space-y-3">
              {/* Table Header */}
              <div className="grid grid-cols-12 gap-2 px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                <div className="col-span-5">Description</div>
                <div className="col-span-2">Qty</div>
                <div className="col-span-2">Price</div>
                <div className="col-span-2">Total</div>
                <div className="col-span-1"></div>
              </div>

              {fields.map((field, index) => (
                <div
                  key={field.id}
                  className="grid grid-cols-12 gap-2 items-center p-3 bg-slate-50 rounded-xl border border-slate-100"
                  data-testid={`line-item-${index}`}
                >
                  {/* Description */}
                  <div className="col-span-5">
                    <FormField
                      control={form.control}
                      name={`line_items.${index}.description`}
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <Input
                              {...field}
                              placeholder="Service description"
                              data-testid="line-item-description"
                            />
                          </FormControl>
                          <FormMessage className="text-sm text-red-500 mt-1" />
                        </FormItem>
                      )}
                    />
                  </div>

                  {/* Quantity */}
                  <div className="col-span-2">
                    <FormField
                      control={form.control}
                      name={`line_items.${index}.quantity`}
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <Input
                              type="number"
                              min={1}
                              value={field.value || ''}
                              onChange={(e) => {
                                field.onChange(
                                  e.target.value ? parseInt(e.target.value) : 1
                                );
                                updateLineItemTotal(index);
                              }}
                              data-testid="line-item-quantity"
                            />
                          </FormControl>
                          <FormMessage className="text-sm text-red-500 mt-1" />
                        </FormItem>
                      )}
                    />
                  </div>

                  {/* Unit Price */}
                  <div className="col-span-2">
                    <FormField
                      control={form.control}
                      name={`line_items.${index}.unit_price`}
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <Input
                              type="number"
                              min={0}
                              step="0.01"
                              value={field.value || ''}
                              onChange={(e) => {
                                field.onChange(
                                  e.target.value ? parseFloat(e.target.value) : 0
                                );
                                updateLineItemTotal(index);
                              }}
                              data-testid="line-item-amount"
                            />
                          </FormControl>
                          <FormMessage className="text-sm text-red-500 mt-1" />
                        </FormItem>
                      )}
                    />
                  </div>

                  {/* Total (read-only) */}
                  <div className="col-span-2">
                    <FormField
                      control={form.control}
                      name={`line_items.${index}.total`}
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <Input
                              type="number"
                              value={field.value?.toFixed(2) || '0.00'}
                              readOnly
                              className="bg-slate-100 text-slate-600 font-medium"
                              data-testid="line-item-total"
                            />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                  </div>

                  {/* Remove Button */}
                  <div className="col-span-1 flex justify-center">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => remove(index)}
                      className="text-red-500 hover:text-red-700 hover:bg-red-50"
                      data-testid="remove-line-item-btn"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}

              {/* Totals Section */}
              <div className="flex justify-end pt-4 border-t border-slate-100">
                <div className="w-64 space-y-2">
                  <div className="flex justify-between text-sm text-slate-600">
                    <span>Subtotal:</span>
                    <span className="font-medium">${(form.watch('line_items') || []).reduce((sum, item) => sum + (item.total || 0), 0).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-sm text-slate-600">
                    <span>Late Fee:</span>
                    <span className="font-medium">${(form.watch('late_fee_amount') || 0).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-lg font-bold text-slate-800 pt-2 border-t border-slate-200">
                    <span>Total:</span>
                    <span>${((form.watch('line_items') || []).reduce((sum, item) => sum + (item.total || 0), 0) + (form.watch('late_fee_amount') || 0)).toFixed(2)}</span>
                  </div>
                </div>
              </div>

              {/* Calculate Total Button */}
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={calculateTotalFromLineItems}
                className="w-full"
                data-testid="calculate-total-btn"
              >
                Calculate Total from Line Items
              </Button>
            </div>
          )}
        </div>

        {/* Notes Section */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
            Additional Information
          </h3>
          <FormField
            control={form.control}
            name="notes"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-sm font-medium text-slate-700">Notes</FormLabel>
                <FormControl>
                  <Textarea
                    {...field}
                    value={field.value || ''}
                    placeholder="Additional notes for this invoice"
                    rows={3}
                    data-testid="notes-input"
                  />
                </FormControl>
                <FormMessage className="text-sm text-red-500 mt-1" data-testid="validation-error" />
              </FormItem>
            )}
          />
        </div>

        {/* Form Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
          {onCancel && (
            <Button
              type="button"
              variant="secondary"
              onClick={onCancel}
              data-testid="cancel-btn"
            >
              Cancel
            </Button>
          )}
          <Button type="submit" variant="primary" disabled={isPending} data-testid="submit-invoice-btn">
            {isPending
              ? 'Saving...'
              : isEditing
                ? 'Update Invoice'
                : 'Create Invoice'}
          </Button>
        </div>
      </form>
    </Form>
  );
}
