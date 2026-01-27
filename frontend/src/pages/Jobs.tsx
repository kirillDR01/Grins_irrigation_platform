import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '@/shared/components/PageHeader';
import { JobList } from '@/features/jobs/components/JobList';
import { JobForm } from '@/features/jobs/components/JobForm';
import { JobDetail } from '@/features/jobs/components/JobDetail';
import { useAICategorize } from '@/features/ai/hooks/useAICategorize';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Plus, Sparkles, CheckCircle, AlertTriangle, X } from 'lucide-react';

export function JobsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showCategorizeDialog, setShowCategorizeDialog] = useState(false);
  const [jobDescription, setJobDescription] = useState('');
  
  // AI Categorization hook
  const {
    categorization,
    isLoading: isCategorizing,
    error: categorizeError,
    categorizeJobs,
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

  const handleCategorizeJob = async () => {
    if (!jobDescription.trim()) return;
    await categorizeJobs({
      description: jobDescription,
    });
  };

  const handleCloseCategorization = () => {
    setShowCategorizeDialog(false);
    setJobDescription('');
    clearCategorizations();
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
              onClick={() => setShowCategorizeDialog(true)}
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

      <JobList onJobClick={handleJobClick} />

      {/* AI Categorize Dialog */}
      <Dialog open={showCategorizeDialog} onOpenChange={setShowCategorizeDialog}>
        <DialogContent className="max-w-2xl" aria-describedby="categorize-job-description">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" />
              AI Job Categorization
            </DialogTitle>
            <p id="categorize-job-description" className="text-sm text-muted-foreground">
              Enter a job description and let AI categorize it for you.
            </p>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* Input Section */}
            <div>
              <label htmlFor="job-description" className="block text-sm font-medium mb-2">
                Job Description
              </label>
              <textarea
                id="job-description"
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="e.g., Broken sprinkler head in front yard, water leaking..."
                className="w-full px-3 py-2 border rounded-md min-h-[100px]"
                data-testid="job-description-input"
              />
            </div>
            
            <Button
              onClick={handleCategorizeJob}
              disabled={!jobDescription.trim() || isCategorizing}
              className="w-full"
              data-testid="categorize-btn"
            >
              {isCategorizing ? 'Categorizing...' : 'Categorize Job'}
            </Button>

            {/* Error State */}
            {categorizeError && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{categorizeError}</AlertDescription>
              </Alert>
            )}

            {/* Result Section */}
            {categorization && !isCategorizing && (
              <Card data-testid="categorization-result">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <CheckCircle className="h-5 w-5 text-green-600" />
                    Categorization Result
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">Category:</span>
                    <Badge>{categorization.category}</Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">Confidence:</span>
                    <Badge variant={categorization.confidence_score >= 70 ? 'default' : 'secondary'}>
                      {categorization.confidence_score}%
                    </Badge>
                  </div>
                  <div>
                    <span className="font-medium">Reasoning:</span>
                    <p className="text-sm text-muted-foreground mt-1">
                      {categorization.reasoning}
                    </p>
                  </div>
                  {categorization.suggested_services.length > 0 && (
                    <div>
                      <span className="font-medium">Suggested Services:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {categorization.suggested_services.map((service, idx) => (
                          <Badge key={idx} variant="outline">{service}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  {categorization.needs_review && (
                    <Alert>
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>
                        This categorization needs manual review due to low confidence.
                      </AlertDescription>
                    </Alert>
                  )}
                </CardContent>
              </Card>
            )}

            <div className="flex justify-end">
              <Button variant="outline" onClick={handleCloseCategorization}>
                <X className="h-4 w-4 mr-2" />
                Close
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

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
