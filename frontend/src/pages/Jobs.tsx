import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '@/shared/components/PageHeader';
import { JobList } from '@/features/jobs/components/JobList';
import { JobForm } from '@/features/jobs/components/JobForm';
import { JobDetail } from '@/features/jobs/components/JobDetail';
import { AICategorization } from '@/features/ai/components/AICategorization';
import { useAICategorize } from '@/features/ai/hooks/useAICategorize';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Plus, Sparkles } from 'lucide-react';

export function JobsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showCategorization, setShowCategorization] = useState(false);
  
  // AI Categorization hook
  const {
    categorizations,
    summary,
    isLoading: isCategorizing,
    error: categorizeError,
    categorizeJobs,
    approveBulk,
    clearCategorizations,
  } = useAICategorize();
  
  // Sync URL param with selected job - use id directly instead of effect
  const selectedJobId = id || null;

  const handleJobClick = (jobId: string) => {
    navigate(`/jobs/${jobId}`);
  };

  const handleCloseDetail = () => {
    navigate('/jobs');
  };

  const handleCategorizeJobs = async () => {
    setShowCategorization(true);
    await categorizeJobs({
      job_ids: [], // Empty array means categorize all uncategorized jobs
    });
  };

  const handleApproveAll = async () => {
    const readyJobIds = categorizations
      .filter(c => !c.requires_review)
      .map(c => c.job_id);
    await approveBulk(readyJobIds);
  };

  const handleApproveJob = async (jobId: string) => {
    await approveBulk([jobId]);
  };

  const handleReviewJob = (jobId: string) => {
    navigate(`/jobs/${jobId}`);
    setShowCategorization(false);
  };

  return (
    <div data-testid="jobs-page" className="space-y-6">
      <PageHeader
        title="Jobs"
        description="Manage job requests and track their status"
        action={
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={handleCategorizeJobs}
              data-testid="categorize-jobs-btn"
            >
              <Sparkles className="mr-2 h-4 w-4" />
              AI Categorize
            </Button>
            <Button onClick={() => setShowCreateDialog(true)} data-testid="add-job-btn">
              <Plus className="mr-2 h-4 w-4" />
              New Job
            </Button>
          </div>
        }
      />

      {/* AI Categorization Section */}
      {showCategorization && (categorizations.length > 0 || isCategorizing || categorizeError) && (
        <div className="mb-6">
          <AICategorization
            categorizations={categorizations}
            summary={summary || {
              total_jobs: 0,
              ready_to_schedule: 0,
              requires_review: 0,
              avg_confidence: 0,
            }}
            isLoading={isCategorizing}
            error={categorizeError ? new Error(categorizeError) : null}
            onApproveAll={handleApproveAll}
            onApproveJob={handleApproveJob}
            onReviewJob={handleReviewJob}
          />
        </div>
      )}

      <JobList onJobClick={handleJobClick} />

      {/* Create Job Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" aria-describedby="create-job-description">
          <DialogHeader>
            <DialogTitle>Create New Job</DialogTitle>
            <p id="create-job-description" className="text-sm text-muted-foreground">
              Fill in the details below to create a new job request.
            </p>
          </DialogHeader>
          <JobForm
            onSuccess={() => setShowCreateDialog(false)}
            onCancel={() => setShowCreateDialog(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Job Detail Dialog */}
      <Dialog open={!!selectedJobId} onOpenChange={handleCloseDetail}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto" aria-describedby="job-detail-description">
          <DialogHeader>
            <DialogTitle>Job Details</DialogTitle>
            <p id="job-detail-description" className="text-sm text-muted-foreground">
              View and manage job information.
            </p>
          </DialogHeader>
          {selectedJobId && (
            <JobDetail
              jobId={selectedJobId}
              onClose={handleCloseDetail}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
