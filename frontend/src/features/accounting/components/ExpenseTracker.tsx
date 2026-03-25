import { useState, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Textarea } from '@/components/ui/textarea';
import { Plus, Trash2, Upload, Receipt } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/shared/utils/cn';
import { LoadingSpinner } from '@/shared/components';
import { useExpenses, useCreateExpense, useDeleteExpense, useExtractReceipt } from '../hooks';
import type { ExpenseCategory, ExpenseListParams } from '../types';

const EXPENSE_CATEGORIES: { value: ExpenseCategory; label: string }[] = [
  { value: 'MATERIALS', label: 'Materials' },
  { value: 'FUEL', label: 'Fuel' },
  { value: 'MAINTENANCE', label: 'Maintenance' },
  { value: 'LABOR', label: 'Labor' },
  { value: 'MARKETING', label: 'Marketing' },
  { value: 'INSURANCE', label: 'Insurance' },
  { value: 'EQUIPMENT', label: 'Equipment' },
  { value: 'OFFICE', label: 'Office' },
  { value: 'SUBCONTRACTING', label: 'Subcontracting' },
  { value: 'OTHER', label: 'Other' },
];

const CATEGORY_COLORS: Record<ExpenseCategory, string> = {
  MATERIALS: 'bg-blue-100 text-blue-700',
  FUEL: 'bg-amber-100 text-amber-700',
  MAINTENANCE: 'bg-orange-100 text-orange-700',
  LABOR: 'bg-emerald-100 text-emerald-700',
  MARKETING: 'bg-purple-100 text-purple-700',
  INSURANCE: 'bg-slate-100 text-slate-700',
  EQUIPMENT: 'bg-cyan-100 text-cyan-700',
  OFFICE: 'bg-pink-100 text-pink-700',
  SUBCONTRACTING: 'bg-indigo-100 text-indigo-700',
  OTHER: 'bg-gray-100 text-gray-700',
};

const expenseSchema = z.object({
  category: z.string().min(1, 'Category is required'),
  description: z.string().min(1, 'Description is required').max(2000),
  amount: z.number().positive('Amount must be positive'),
  date: z.string().min(1, 'Date is required'),
  vendor: z.string().max(200).optional().or(z.literal('')),
  job_id: z.string().optional().or(z.literal('')),
  notes: z.string().max(5000).optional().or(z.literal('')),
});

type ExpenseFormData = z.infer<typeof expenseSchema>;

export function ExpenseTracker() {
  const [params, setParams] = useState<ExpenseListParams>({ page: 1, page_size: 20 });
  const [dialogOpen, setDialogOpen] = useState(false);
  const [receiptFile, setReceiptFile] = useState<File | null>(null);

  const { data: expenses, isLoading } = useExpenses(params);
  const createExpense = useCreateExpense();
  const deleteExpense = useDeleteExpense();
  const extractReceipt = useExtractReceipt();

  const form = useForm<ExpenseFormData>({
    resolver: zodResolver(expenseSchema),
    defaultValues: {
      category: '',
      description: '',
      amount: 0,
      date: new Date().toISOString().split('T')[0],
      vendor: '',
      job_id: '',
      notes: '',
    },
  });

  const handleReceiptUpload = useCallback(async (file: File) => {
    setReceiptFile(file);
    try {
      const result = await extractReceipt.mutateAsync(file);
      if (result.amount) form.setValue('amount', result.amount);
      if (result.vendor) form.setValue('vendor', result.vendor);
      if (result.category) form.setValue('category', result.category);
      toast.success('Receipt scanned', { description: 'Fields pre-populated from receipt' });
    } catch {
      toast.info('Receipt uploaded', { description: 'Could not extract data automatically' });
    }
  }, [extractReceipt, form]);

  const onSubmit = async (data: ExpenseFormData) => {
    try {
      await createExpense.mutateAsync({
        category: data.category as ExpenseCategory,
        description: data.description,
        amount: data.amount,
        date: data.date,
        vendor: data.vendor || undefined,
        job_id: data.job_id || undefined,
        notes: data.notes || undefined,
        receipt_file: receiptFile ?? undefined,
      });
      toast.success('Expense created');
      form.reset();
      setReceiptFile(null);
      setDialogOpen(false);
    } catch {
      toast.error('Failed to create expense');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteExpense.mutateAsync(id);
      toast.success('Expense deleted');
    } catch {
      toast.error('Failed to delete expense');
    }
  };

  return (
    <Card data-testid="expense-tracker">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Expenses</CardTitle>
          <div className="flex items-center gap-2">
            <Select
              value={params.category ?? 'all'}
              onValueChange={(v) => setParams((p) => ({ ...p, category: v === 'all' ? undefined : v as ExpenseCategory, page: 1 }))}
            >
              <SelectTrigger className="w-36" data-testid="expense-category-filter">
                <SelectValue placeholder="All Categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {EXPENSE_CATEGORIES.map((c) => (
                  <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button size="sm" data-testid="add-expense-btn">
                  <Plus className="h-4 w-4 mr-1" /> Add Expense
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader>
                  <DialogTitle>New Expense</DialogTitle>
                </DialogHeader>
                <Form {...form}>
                  <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" data-testid="expense-form">
                    {/* Receipt Upload */}
                    <div className="border-2 border-dashed rounded-lg p-4 text-center">
                      <label className="cursor-pointer flex flex-col items-center gap-2">
                        <Receipt className="h-8 w-8 text-slate-400" />
                        <span className="text-sm text-slate-500">
                          {receiptFile ? receiptFile.name : 'Upload receipt for auto-fill'}
                        </span>
                        <input
                          type="file"
                          accept="image/jpeg,image/png,application/pdf"
                          className="hidden"
                          data-testid="receipt-upload-input"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) handleReceiptUpload(file);
                          }}
                        />
                        <Button type="button" variant="outline" size="sm" data-testid="receipt-upload-btn">
                          <Upload className="h-4 w-4 mr-1" /> Choose File
                        </Button>
                      </label>
                    </div>

                    <FormField control={form.control} name="category" render={({ field }) => (
                      <FormItem>
                        <FormLabel>Category</FormLabel>
                        <Select onValueChange={field.onChange} value={field.value}>
                          <FormControl>
                            <SelectTrigger data-testid="expense-category-select">
                              <SelectValue placeholder="Select category" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {EXPENSE_CATEGORIES.map((c) => (
                              <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )} />

                    <FormField control={form.control} name="description" render={({ field }) => (
                      <FormItem>
                        <FormLabel>Description</FormLabel>
                        <FormControl>
                          <Input {...field} data-testid="expense-description-input" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )} />

                    <div className="grid grid-cols-2 gap-4">
                      <FormField control={form.control} name="amount" render={({ field }) => (
                        <FormItem>
                          <FormLabel>Amount ($)</FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              step="0.01"
                              data-testid="expense-amount-input"
                              value={field.value}
                              onChange={(e) => field.onChange(e.target.valueAsNumber || 0)}
                              onBlur={field.onBlur}
                              name={field.name}
                              ref={field.ref}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )} />

                      <FormField control={form.control} name="date" render={({ field }) => (
                        <FormItem>
                          <FormLabel>Date</FormLabel>
                          <FormControl>
                            <Input type="date" {...field} data-testid="expense-date-input" />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )} />
                    </div>

                    <FormField control={form.control} name="vendor" render={({ field }) => (
                      <FormItem>
                        <FormLabel>Vendor (optional)</FormLabel>
                        <FormControl>
                          <Input {...field} data-testid="expense-vendor-input" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )} />

                    <FormField control={form.control} name="job_id" render={({ field }) => (
                      <FormItem>
                        <FormLabel>Job Link (optional)</FormLabel>
                        <FormControl>
                          <Input {...field} placeholder="Job ID" data-testid="expense-job-input" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )} />

                    <FormField control={form.control} name="notes" render={({ field }) => (
                      <FormItem>
                        <FormLabel>Notes (optional)</FormLabel>
                        <FormControl>
                          <Textarea {...field} rows={2} data-testid="expense-notes-input" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )} />

                    <Button type="submit" className="w-full" disabled={createExpense.isPending} data-testid="expense-submit-btn">
                      {createExpense.isPending ? 'Creating...' : 'Create Expense'}
                    </Button>
                  </form>
                </Form>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex justify-center py-8"><LoadingSpinner /></div>
        ) : (
          <>
            <Table data-testid="expense-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Vendor</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {(expenses?.items ?? []).length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-slate-500 py-8">
                      No expenses recorded yet
                    </TableCell>
                  </TableRow>
                ) : (
                  expenses?.items.map((expense) => (
                    <TableRow key={expense.id} data-testid="expense-row">
                      <TableCell className="text-sm">{new Date(expense.date).toLocaleDateString()}</TableCell>
                      <TableCell>
                        <Badge className={cn('text-xs', CATEGORY_COLORS[expense.category])}>
                          {expense.category}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm max-w-[200px] truncate">{expense.description}</TableCell>
                      <TableCell className="text-sm text-slate-500">{expense.vendor ?? '—'}</TableCell>
                      <TableCell className="text-right font-medium">
                        ${expense.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(expense.id)}
                          data-testid="delete-expense-btn"
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
            {(expenses?.total_pages ?? 1) > 1 && (
              <div className="flex justify-center gap-2 mt-4">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={params.page === 1}
                  onClick={() => setParams((p) => ({ ...p, page: (p.page ?? 1) - 1 }))}
                  data-testid="expense-prev-page"
                >
                  Previous
                </Button>
                <span className="text-sm text-slate-500 self-center">
                  Page {params.page} of {expenses?.total_pages ?? 1}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={params.page === (expenses?.total_pages ?? 1)}
                  onClick={() => setParams((p) => ({ ...p, page: (p.page ?? 1) + 1 }))}
                  data-testid="expense-next-page"
                >
                  Next
                </Button>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
