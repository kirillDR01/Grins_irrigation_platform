/**
 * CreateInvoiceDialog component.
 * Dialog for creating new invoices by selecting from completed jobs.
 */

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Plus, Search, FileText, Calendar, DollarSign } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
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

  const handleBack = () => {
    setSelectedJob(null);
  };

  const handleSuccess = () => {
    setOpen(false);
    setSelectedJob(null);
    setSearchQuery('');
    onSuccess?.();
  };

  const handleOpenChange = (newOpen: boolean) => {
    setOpen(newOpen);
    if (!newOpen) {
      setSelectedJob(null);
      setSearchQuery('');
    }
  };

  // Get the best price to use for the invoice (final_amount > quoted_amount > 0)
  // Ensure we return a number, not a string
  const getJobAmount = (job: Job): number => {
    const amount = job.final_amount ?? job.quoted_amount ?? 0;
    return typeof amount === 'string' ? parseFloat(amount) : amount;
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button data-testid="create-invoice-btn">
          <Plus className="h-4 w-4 mr-2" />
          Create Invoice
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[90vh]" data-testid="create-invoice-dialog">
        {!selectedJob ? (
          <>
            <DialogHeader>
              <DialogTitle>Create New Invoice</DialogTitle>
              <DialogDescription>
                Select a completed job to create an invoice for. Only jobs without
                existing invoices are shown.
              </DialogDescription>
            </DialogHeader>

            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search jobs by description or type..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
                data-testid="job-search-input"
              />
            </div>

            {/* Job List */}
            <div className="h-[400px] overflow-y-auto pr-4">
              {loadingJobs ? (
                <div className="flex items-center justify-center h-32">
                  <p className="text-muted-foreground">Loading jobs...</p>
                </div>
              ) : availableJobs.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-32 text-center">
                  <FileText className="h-8 w-8 text-muted-foreground mb-2" />
                  <p className="text-muted-foreground">
                    {searchQuery
                      ? 'No matching jobs found'
                      : 'No completed jobs without invoices'}
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Complete a job first to create an invoice
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {availableJobs.map((job) => (
                    <button
                      key={job.id}
                      onClick={() => handleJobSelect(job)}
                      className="w-full p-4 border rounded-lg hover:bg-accent transition-colors text-left"
                      data-testid={`job-option-${job.id}`}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium truncate">
                              {job.description || 'No description'}
                            </span>
                            <Badge variant="secondary" className="shrink-0">
                              {job.status}
                            </Badge>
                          </div>
                          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
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
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="text-sm text-muted-foreground text-center">
              {availableJobs.length} job{availableJobs.length !== 1 ? 's' : ''} available
            </div>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Create Invoice</DialogTitle>
              <DialogDescription>
                Creating invoice for: {selectedJob.description || 'Job'}
              </DialogDescription>
            </DialogHeader>

            {/* Selected Job Summary */}
            <div className="p-3 bg-muted rounded-lg mb-4">
              <div className="flex items-center gap-2 text-sm">
                <FileText className="h-4 w-4" />
                <span className="font-medium">{selectedJob.job_type}</span>
                <span className="text-muted-foreground">•</span>
                <span className="text-muted-foreground">
                  {selectedJob.description}
                </span>
              </div>
              {(selectedJob.final_amount != null || selectedJob.quoted_amount != null) && (
                <div className="flex items-center gap-2 text-sm mt-1">
                  <DollarSign className="h-4 w-4" />
                  <span>
                    {selectedJob.final_amount != null
                      ? `Final Amount: ${formatCurrency(selectedJob.final_amount)}`
                      : `Quoted: ${formatCurrency(selectedJob.quoted_amount)}`}
                  </span>
                </div>
              )}
            </div>

            <InvoiceForm
              jobId={selectedJob.id}
              defaultAmount={getJobAmount(selectedJob)}
              onSuccess={handleSuccess}
              onCancel={handleBack}
            />
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
