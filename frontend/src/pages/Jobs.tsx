import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '@/shared/components/PageHeader';
import { JobList } from '@/features/jobs/components/JobList';
import { JobForm } from '@/features/jobs/components/JobForm';
import { JobDetail } from '@/features/jobs/components/JobDetail';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Plus } from 'lucide-react';

export function JobsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  // Sync URL param with selected job
  useEffect(() => {
    if (id) {
      setSelectedJobId(id);
    }
  }, [id]);

  const handleJobClick = (jobId: string) => {
    navigate(`/jobs/${jobId}`);
    setSelectedJobId(jobId);
  };

  const handleCloseDetail = () => {
    navigate('/jobs');
    setSelectedJobId(null);
  };

  return (
    <div data-testid="jobs-page" className="space-y-6">
      <PageHeader
        title="Jobs"
        description="Manage job requests and track their status"
        action={
          <Button onClick={() => setShowCreateDialog(true)} data-testid="add-job-btn">
            <Plus className="mr-2 h-4 w-4" />
            New Job
          </Button>
        }
      />

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
