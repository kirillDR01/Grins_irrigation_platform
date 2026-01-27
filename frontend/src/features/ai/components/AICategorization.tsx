/**
 * AICategorization Component
 * 
 * AI-powered job categorization interface
 * Displays categorization results grouped by category with confidence scores,
 * suggested pricing, and provides approval/review actions
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { CheckCircle, AlertTriangle, DollarSign, FileText } from 'lucide-react';
import { AILoadingState } from './AILoadingState';
import { AIErrorState } from './AIErrorState';
import type { JobCategorization, CategorizationSummary } from '../types';

interface AICategorizationProps {
  categorizations: JobCategorization[];
  summary: CategorizationSummary;
  isLoading?: boolean;
  error?: Error | null;
  onApproveAll?: () => void;
  onApproveJob?: (jobId: string) => void;
  onReviewJob?: (jobId: string) => void;
}

export function AICategorization({
  categorizations,
  summary,
  isLoading = false,
  error = null,
  onApproveAll,
  onApproveJob,
  onReviewJob,
}: AICategorizationProps) {
  const [selectedJobs, setSelectedJobs] = useState<Set<string>>(new Set());

  if (isLoading) {
    return <AILoadingState message="AI is categorizing jobs..." />;
  }

  if (error) {
    return <AIErrorState error={error} onRetry={() => window.location.reload()} />;
  }

  const readyJobs = categorizations.filter(c => !c.requires_review);
  const reviewJobs = categorizations.filter(c => c.requires_review);

  const toggleJobSelection = (jobId: string) => {
    const newSelected = new Set(selectedJobs);
    if (newSelected.has(jobId)) {
      newSelected.delete(jobId);
    } else {
      newSelected.add(jobId);
    }
    setSelectedJobs(newSelected);
  };

  const handleBulkApprove = () => {
    if (selectedJobs.size > 0) {
      selectedJobs.forEach(jobId => onApproveJob?.(jobId));
      setSelectedJobs(new Set());
    } else {
      onApproveAll?.();
    }
  };

  const getConfidenceColor = (score: number): string => {
    if (score >= 0.85) return 'text-green-600';
    if (score >= 0.70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getConfidenceBadge = (score: number) => {
    const percentage = Math.round(score * 100);
    const variant = score >= 0.85 ? 'default' : score >= 0.70 ? 'secondary' : 'destructive';
    return (
      <Badge variant={variant} data-testid="confidence-score">
        {percentage}% confident
      </Badge>
    );
  };

  return (
    <div data-testid="ai-categorization" className="space-y-4">
      {/* Summary Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            AI Categorization Results
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Total Jobs</p>
              <p className="text-2xl font-bold">{summary.total_jobs}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Ready to Schedule</p>
              <p className="text-2xl font-bold text-green-600">{summary.ready_to_schedule}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Requires Review</p>
              <p className="text-2xl font-bold text-yellow-600">{summary.requires_review}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Avg Confidence</p>
              <p className="text-2xl font-bold">{Math.round(summary.avg_confidence * 100)}%</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Bulk Actions */}
      <div className="flex gap-2">
        <Button
          onClick={handleBulkApprove}
          disabled={readyJobs.length === 0}
          data-testid="approve-all-btn"
        >
          <CheckCircle className="h-4 w-4 mr-2" />
          {selectedJobs.size > 0 ? `Approve Selected (${selectedJobs.size})` : 'Approve All Ready'}
        </Button>
        <Button
          variant="outline"
          onClick={() => setSelectedJobs(new Set())}
          disabled={selectedJobs.size === 0}
          data-testid="clear-selection-btn"
        >
          Clear Selection
        </Button>
      </div>

      {/* Ready to Schedule Section */}
      {readyJobs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-green-600">
              <CheckCircle className="h-5 w-5" />
              Ready to Schedule ({readyJobs.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div data-testid="categorization-results" className="space-y-3">
              {readyJobs.map((cat) => (
                <Card key={cat.job_id} className="border-green-200">
                  <CardContent className="pt-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <input
                            type="checkbox"
                            checked={selectedJobs.has(cat.job_id)}
                            onChange={() => toggleJobSelection(cat.job_id)}
                            className="h-4 w-4"
                            data-testid={`job-checkbox-${cat.job_id}`}
                          />
                          <h4 className="font-semibold">Job #{cat.job_id}</h4>
                          {getConfidenceBadge(cat.confidence_score)}
                        </div>
                        <div className="space-y-1 text-sm">
                          <p>
                            <span className="font-medium">Category:</span> {cat.suggested_category}
                          </p>
                          <p>
                            <span className="font-medium">Job Type:</span> {cat.suggested_job_type}
                          </p>
                          {cat.suggested_price && (
                            <p className="flex items-center gap-1">
                              <DollarSign className="h-4 w-4" />
                              <span className="font-medium">Suggested Price:</span> {cat.suggested_price}
                            </p>
                          )}
                          {cat.ai_notes && (
                            <Alert className="mt-2">
                              <AlertDescription className="text-xs">
                                <strong>AI Notes:</strong> {cat.ai_notes}
                              </AlertDescription>
                            </Alert>
                          )}
                        </div>
                      </div>
                      <Button
                        size="sm"
                        onClick={() => onApproveJob?.(cat.job_id)}
                        data-testid={`approve-job-${cat.job_id}`}
                      >
                        Approve
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Requires Review Section */}
      {reviewJobs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-yellow-600">
              <AlertTriangle className="h-5 w-5" />
              Requires Review ({reviewJobs.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {reviewJobs.map((cat) => (
                <Card key={cat.job_id} className="border-yellow-200">
                  <CardContent className="pt-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h4 className="font-semibold">Job #{cat.job_id}</h4>
                          {getConfidenceBadge(cat.confidence_score)}
                          <Badge variant="outline" className="text-yellow-600">
                            Low Confidence
                          </Badge>
                        </div>
                        <div className="space-y-1 text-sm">
                          <p>
                            <span className="font-medium">Category:</span> {cat.suggested_category}
                          </p>
                          <p>
                            <span className="font-medium">Job Type:</span> {cat.suggested_job_type}
                          </p>
                          {cat.suggested_price && (
                            <p className="flex items-center gap-1">
                              <DollarSign className="h-4 w-4" />
                              <span className="font-medium">Suggested Price:</span> {cat.suggested_price}
                            </p>
                          )}
                          {cat.ai_notes && (
                            <Alert className="mt-2">
                              <AlertDescription className="text-xs">
                                <strong>AI Notes:</strong> {cat.ai_notes}
                              </AlertDescription>
                            </Alert>
                          )}
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onReviewJob?.(cat.job_id)}
                        data-testid={`review-job-${cat.job_id}`}
                      >
                        Review
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {categorizations.length === 0 && (
        <Alert>
          <AlertDescription>No jobs to categorize at this time.</AlertDescription>
        </Alert>
      )}
    </div>
  );
}
