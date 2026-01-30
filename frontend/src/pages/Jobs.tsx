import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '@/shared/components/PageHeader';
import { JobList } from '@/features/jobs/components/JobList';
import { JobForm } from '@/features/jobs/components/JobForm';
import { JobDetail } from '@/features/jobs/components/JobDetail';
import { useAICategorize } from '@/features/ai/hooks/useAICategorize';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Plus, Sparkles, AlertTriangle } from 'lucide-react';

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
        <DialogContent className="max-w-xl p-0 overflow-hidden" aria-describedby="categorize-job-description" data-testid="ai-categorize-modal">
          {/* Gradient Header */}
          <div className="bg-gradient-to-r from-teal-500 to-teal-600 text-white p-6 rounded-t-2xl">
            <DialogHeader className="space-y-2">
              <DialogTitle className="flex items-center gap-2 text-white text-lg font-bold">
                <Sparkles className="h-5 w-5" />
                AI Job Categorization
              </DialogTitle>
              <p id="categorize-job-description" className="text-teal-100 text-sm">
                Enter a job description and let AI categorize it for you.
              </p>
            </DialogHeader>
          </div>
          
          <div className="p-6 space-y-4">
            {/* Input Section */}
            <div>
              <label htmlFor="job-description" className="block text-sm font-medium text-slate-700 mb-2">
                Job Description
              </label>
              <textarea
                id="job-description"
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="e.g., Broken sprinkler head in front yard, water leaking..."
                className="w-full px-4 py-3 border border-slate-200 rounded-xl bg-white text-slate-700 text-sm placeholder-slate-400 min-h-[100px] focus:border-teal-500 focus:ring-2 focus:ring-teal-100 focus:outline-none transition-all"
                data-testid="job-description-input"
              />
            </div>
            
            <Button
              onClick={handleCategorizeJob}
              disabled={!jobDescription.trim() || isCategorizing}
              className="w-full bg-teal-500 hover:bg-teal-600 text-white"
              data-testid="analyze-btn"
            >
              {isCategorizing ? 'Analyzing...' : 'Analyze Job'}
            </Button>

            {/* Error State */}
            {categorizeError && (
              <Alert variant="destructive" className="border-l-4 border-red-400">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{categorizeError}</AlertDescription>
              </Alert>
            )}

            {/* AI Suggestion Section */}
            {categorization && !isCategorizing && (
              <div className="bg-teal-50 rounded-xl p-4 border border-teal-100" data-testid="ai-suggestion">
                <div className="flex items-center gap-2 mb-3">
                  <div className="bg-teal-100 p-2 rounded-full">
                    <Sparkles className="h-4 w-4 text-teal-600" />
                  </div>
                  <span className="font-semibold text-slate-800">AI Suggestion</span>
                </div>
                
                <div className="space-y-3">
                  {/* Category Badge */}
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-600">Category:</span>
                    <Badge className="bg-teal-500 text-white">{categorization.category}</Badge>
                  </div>
                  
                  {/* Confidence Indicator */}
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-600">Confidence:</span>
                    <div className="flex items-center gap-2">
                      <div className="w-24 h-2 bg-slate-200 rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${
                            categorization.confidence_score >= 80 ? 'bg-emerald-500' : 
                            categorization.confidence_score >= 60 ? 'bg-amber-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${categorization.confidence_score}%` }}
                        />
                      </div>
                      <span className={`text-sm font-medium ${
                        categorization.confidence_score >= 80 ? 'text-emerald-600' : 
                        categorization.confidence_score >= 60 ? 'text-amber-600' : 'text-red-600'
                      }`}>
                        {categorization.confidence_score}%
                      </span>
                    </div>
                  </div>
                  
                  {/* Reasoning */}
                  <div>
                    <span className="text-sm font-medium text-slate-600">Reasoning:</span>
                    <p className="text-sm text-slate-500 mt-1">
                      {categorization.reasoning}
                    </p>
                  </div>
                  
                  {/* Suggested Services */}
                  {categorization.suggested_services.length > 0 && (
                    <div>
                      <span className="text-sm font-medium text-slate-600">Suggested Services:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {categorization.suggested_services.map((service, idx) => (
                          <Badge key={idx} variant="outline" className="bg-white border-slate-200 text-slate-600">
                            {service}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Review Warning */}
                  {categorization.needs_review && (
                    <div className="flex items-center gap-2 p-3 bg-amber-50 rounded-lg border border-amber-100">
                      <AlertTriangle className="h-4 w-4 text-amber-500" />
                      <span className="text-sm text-amber-700">
                        This categorization needs manual review due to low confidence.
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Footer Buttons */}
            <div className="flex justify-end gap-3 pt-2 border-t border-slate-100">
              <Button 
                variant="outline" 
                onClick={handleCloseCategorization} 
                className="border-slate-200 text-slate-700 hover:bg-slate-50"
                data-testid="close-modal-btn"
              >
                Cancel
              </Button>
              {categorization && (
                <Button 
                  className="bg-teal-500 hover:bg-teal-600 text-white"
                  data-testid="apply-suggestion-btn"
                >
                  Apply Suggestion
                </Button>
              )}
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
