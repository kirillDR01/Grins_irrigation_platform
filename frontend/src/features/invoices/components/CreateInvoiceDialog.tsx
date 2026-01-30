/**
 * CreateInvoiceDialog component.
 * Dialog for creating new invoices by selecting from completed jobs.
 */

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Plus, Search, FileText, Calendar, DollarSign, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { jobApi } from '@/features/jobs/api/jobApi';
import { invoiceApi } from '../api/invoiceApi';
import { InvoiceForm } from './InvoiceForm';
import type { Job } from '@/features/jobs/types';

interface CreateInvoiceDialogProps {
  onSuccess?: () => void;
}

function formatCurrency(amount: number | null | undefined): string {
  if (amount == null) return '$0.00';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return 'N/A';
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function CreateInvoiceDialog({ onSuccess }: CreateInvoiceDialogProps) {
  const [open, setOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedJobIds, setSelectedJobIds] = useState<Set<string>>(new Set());

  // Fetch completed jobs
  const { data: completedJobsData, isLoading: loadingJobs } = useQuery({
    queryKey: ['jobs', 'completed-for-invoice'],
    queryFn: () => jobApi.list({ status: 'completed', page_size: 100 }),
    enabled: open,
  });

  // Fetch closed jobs too (they might also need invoices)
  const { data: closedJobsData } = useQuery({
    queryKey: ['jobs', 'closed-for-invoice'],
    queryFn: () => jobApi.list({ status: 'closed', page_size: 100 }),
    enabled: open,
  });

  // Fetch existing invoices to filter out jobs that already have invoices
  // Note: API max page_size is 100, so we use that
  const { data: existingInvoices } = useQuery({
    queryKey: ['invoices', 'all-for-filter'],
    queryFn: () => invoiceApi.list({ page_size: 100 }),
    enabled: open,
    // Always refetch when dialog opens to get latest invoice data
    refetchOnMount: 'always',
    staleTime: 0,
  });

  // Combine and filter jobs
  const availableJobs = useMemo(() => {
    const allJobs = [
      ...(completedJobsData?.items || []),
      ...(closedJobsData?.items || []),
    ];

    // Get job IDs that already have invoices
    const jobsWithInvoices = new Set(
      existingInvoices?.items?.map((inv) => inv.job_id) || []
    );

    // Filter out jobs that already have invoices
    const jobsWithoutInvoices = allJobs.filter(
      (job) => !jobsWithInvoices.has(job.id)
    );

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      return jobsWithoutInvoices.filter(
        (job) =>
          job.description?.toLowerCase().includes(query) ||
          job.job_type?.toLowerCase().includes(query) ||
          job.customer_id?.toLowerCase().includes(query)
      );
    }

    return jobsWithoutInvoices;
  }, [completedJobsData, closedJobsData, existingInvoices, searchQuery]);

  const handleJobSelect = (job: Job) => {
    setSelectedJob(job);
  };

  const handleJobCheckboxChange = (jobId: string, checked: boolean) => {
    setSelectedJobIds((prev) => {
      const newSet = new Set(prev);
      if (checked) {
        newSet.add(jobId);
      } else {
        newSet.delete(jobId);
      }
      return newSet;
    });
  };

  const handleBack = () => {
    setSelectedJob(null);
  };

  const handleSuccess = () => {
    setOpen(false);
    setSelectedJob(null);
    setSearchQuery('');
    setSelectedJobIds(new Set());
    onSuccess?.();
  };

  const handleOpenChange = (newOpen: boolean) => {
    setOpen(newOpen);
    if (!newOpen) {
      setSelectedJob(null);
      setSearchQuery('');
      setSelectedJobIds(new Set());
    }
  };

  // Get the best price to use for the invoice (final_amount > quoted_amount > 0)
  // Ensure we return a number, not a string
  const getJobAmount = (job: Job): number => {
    const amount = job.final_amount ?? job.quoted_amount ?? 0;
    return typeof amount === 'string' ? parseFloat(amount) : amount;
  };

  // Handle creating invoice from selected job (when using checkbox selection)
  const handleCreateFromSelection = () => {
    if (selectedJobIds.size === 1) {
      const jobId = Array.from(selectedJobIds)[0];
      const job = availableJobs.find((j) => j.id === jobId);
      if (job) {
        setSelectedJob(job);
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button data-testid="create-invoice-btn">
          <Plus className="h-4 w-4 mr-2" />
          Create Invoice
        </Button>
      </DialogTrigger>
      <DialogContent 
        className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col bg-white rounded-2xl shadow-xl" 
        data-testid="create-invoice-dialog"
      >
        {!selectedJob ? (
          <>
            <DialogHeader className="p-6 border-b border-slate-100 bg-slate-50/50">
              <DialogTitle className="text-lg font-bold text-slate-800">Create Invoice</DialogTitle>
              <DialogDescription className="text-slate-500 text-sm">
                Select a completed job to create an invoice for. Only jobs without
                existing invoices are shown.
              </DialogDescription>
            </DialogHeader>

            {/* Search */}
            <div className="px-6 pt-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  placeholder="Search jobs by description or type..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-slate-50 border-slate-200 rounded-lg focus:ring-2 focus:ring-teal-100 focus:border-teal-500"
                  data-testid="job-search-input"
                />
              </div>
            </div>

            {/* Job List */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
              {loadingJobs ? (
                <div className="flex items-center justify-center h-32">
                  <div className="w-8 h-8 border-4 border-teal-200 border-t-teal-500 rounded-full animate-spin" />
                </div>
              ) : availableJobs.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-32 text-center">
                  <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mb-3">
                    <FileText className="h-6 w-6 text-slate-400" />
                  </div>
                  <p className="text-slate-600 font-medium">
                    {searchQuery
                      ? 'No matching jobs found'
                      : 'No completed jobs without invoices'}
                  </p>
                  <p className="text-sm text-slate-400 mt-1">
                    Complete a job first to create an invoice
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {availableJobs.map((job) => (
                    <div
                      key={job.id}
                      className="flex items-start gap-3 p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors cursor-pointer group"
                      onClick={() => handleJobSelect(job)}
                      data-testid={`job-option-${job.id}`}
                    >
                      <Checkbox
                        checked={selectedJobIds.has(job.id)}
                        onCheckedChange={(checked) => {
                          handleJobCheckboxChange(job.id, checked as boolean);
                        }}
                        onClick={(e) => e.stopPropagation()}
                        className="mt-1 data-[state=checked]:bg-teal-500 data-[state=checked]:border-teal-500"
                        data-testid="job-checkbox"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-slate-700 truncate">
                            {job.description || 'No description'}
                          </span>
                          <Badge variant="secondary" className="shrink-0 bg-emerald-100 text-emerald-700">
                            {job.status}
                          </Badge>
                        </div>
                        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-500">
                          <span className="flex items-center gap-1">
                            <FileText className="h-3 w-3" />
                            {job.job_type || 'Unknown type'}
                          </span>
                          {job.completed_at && (
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              Completed: {formatDate(job.completed_at)}
                            </span>
                          )}
                          {(job.final_amount != null || job.quoted_amount != null) && (
                            <span className="flex items-center gap-1">
                              <DollarSign className="h-3 w-3" />
                              {job.final_amount != null
                                ? `Final: ${formatCurrency(job.final_amount)}`
                                : `Quoted: ${formatCurrency(job.quoted_amount)}`}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                        <Check className="h-5 w-5 text-teal-500" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <DialogFooter className="p-6 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between">
              <span className="text-sm text-slate-500">
                {availableJobs.length} job{availableJobs.length !== 1 ? 's' : ''} available
                {selectedJobIds.size > 0 && ` • ${selectedJobIds.size} selected`}
              </span>
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  onClick={() => setOpen(false)}
                  className="bg-white hover:bg-slate-50 border-slate-200 text-slate-700"
                  data-testid="cancel-btn"
                >
                  Cancel
                </Button>
                {selectedJobIds.size === 1 && (
                  <Button
                    onClick={handleCreateFromSelection}
                    className="bg-teal-500 hover:bg-teal-600 text-white shadow-sm shadow-teal-200"
                    data-testid="create-from-selection-btn"
                  >
                    Create Invoice
                  </Button>
                )}
              </div>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader className="p-6 border-b border-slate-100 bg-slate-50/50">
              <DialogTitle className="text-lg font-bold text-slate-800">Create Invoice</DialogTitle>
              <DialogDescription className="text-slate-500 text-sm">
                Creating invoice for: {selectedJob.description || 'Job'}
              </DialogDescription>
            </DialogHeader>

            {/* Selected Job Summary */}
            <div className="px-6 pt-4">
              <div className="p-4 bg-teal-50 rounded-xl border border-teal-100">
                <div className="flex items-center gap-2 text-sm">
                  <FileText className="h-4 w-4 text-teal-600" />
                  <span className="font-medium text-slate-700">{selectedJob.job_type}</span>
                  <span className="text-slate-400">•</span>
                  <span className="text-slate-500">
                    {selectedJob.description}
                  </span>
                </div>
                {(selectedJob.final_amount != null || selectedJob.quoted_amount != null) && (
                  <div className="flex items-center gap-2 text-sm mt-2">
                    <DollarSign className="h-4 w-4 text-teal-600" />
                    <span className="text-slate-700 font-medium">
                      {selectedJob.final_amount != null
                        ? `Final Amount: ${formatCurrency(selectedJob.final_amount)}`
                        : `Quoted: ${formatCurrency(selectedJob.quoted_amount)}`}
                    </span>
                  </div>
                )}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-4">
              <InvoiceForm
                jobId={selectedJob.id}
                defaultAmount={getJobAmount(selectedJob)}
                onSuccess={handleSuccess}
                onCancel={handleBack}
              />
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
