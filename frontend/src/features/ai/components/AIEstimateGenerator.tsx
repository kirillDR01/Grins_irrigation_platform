import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { AlertCircle, FileText, Calendar, DollarSign } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import type { EstimateResponse, SimilarJob } from '../types';

interface AIEstimateGeneratorProps {
  estimate: EstimateResponse | null;
  isLoading: boolean;
  error: Error | null;
  onGeneratePDF: () => void;
  onScheduleSiteVisit: () => void;
  onAdjustQuote: () => void;
}

export function AIEstimateGenerator({
  estimate,
  isLoading,
  error,
  onGeneratePDF,
  onScheduleSiteVisit,
  onAdjustQuote,
}: AIEstimateGeneratorProps) {
  if (isLoading) {
    return (
      <Card data-testid="ai-estimate-generator-loading">
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
            <span className="ml-3">Generating estimate...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card data-testid="ai-estimate-generator-error">
        <CardContent className="p-6">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error.message}</AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!estimate) {
    return null;
  }

  return (
    <Card data-testid="ai-estimate-generator">
      <CardHeader>
        <CardTitle>AI-Generated Estimate</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Estimate Analysis */}
        <div>
          <h3 className="font-semibold mb-2">Property Analysis</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-sm text-gray-600">Estimated Zones:</span>
              <span className="ml-2 font-medium">{estimate.estimated_zones}</span>
            </div>
            <div>
              <span className="text-sm text-gray-600">Confidence:</span>
              <Badge variant={estimate.confidence_score >= 0.85 ? 'default' : 'secondary'}>
                {Math.round(estimate.confidence_score * 100)}%
              </Badge>
            </div>
          </div>
        </div>

        <Separator />

        {/* Similar Jobs */}
        {estimate.similar_jobs && estimate.similar_jobs.length > 0 && (
          <>
            <div data-testid="similar-jobs">
              <h3 className="font-semibold mb-2">Similar Completed Jobs</h3>
              <div className="space-y-2">
                {estimate.similar_jobs.map((job: SimilarJob, idx: number) => (
                  <div key={idx} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                    <div>
                      <span className="text-sm">{job.service_type}</span>
                      <span className="text-xs text-gray-600 ml-2">
                        {job.zone_count} zones
                      </span>
                    </div>
                    <span className="font-medium">${job.final_price.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
            <Separator />
          </>
        )}

        {/* Price Breakdown */}
        <div data-testid="estimate-breakdown">
          <h3 className="font-semibold mb-2">Price Breakdown</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Materials:</span>
              <span className="font-medium">${estimate.breakdown.materials.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Labor:</span>
              <span className="font-medium">${estimate.breakdown.labor.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Equipment:</span>
              <span className="font-medium">${estimate.breakdown.equipment.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Margin:</span>
              <span className="font-medium">${estimate.breakdown.margin.toFixed(2)}</span>
            </div>
            <Separator />
            <div className="flex justify-between text-lg font-bold">
              <span>Total Estimate:</span>
              <span>${estimate.estimated_price.toFixed(2)}</span>
            </div>
          </div>
        </div>

        {/* AI Recommendation */}
        {estimate.recommendation && (
          <>
            <Separator />
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <strong>AI Recommendation:</strong> {estimate.recommendation}
              </AlertDescription>
            </Alert>
          </>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 flex-wrap">
          <Button
            onClick={onGeneratePDF}
            data-testid="generate-pdf-btn"
            className="flex items-center gap-2"
          >
            <FileText className="h-4 w-4" />
            Generate PDF
          </Button>
          <Button
            onClick={onScheduleSiteVisit}
            variant="outline"
            data-testid="schedule-visit-btn"
            className="flex items-center gap-2"
          >
            <Calendar className="h-4 w-4" />
            Schedule Site Visit
          </Button>
          <Button
            onClick={onAdjustQuote}
            variant="outline"
            data-testid="adjust-quote-btn"
            className="flex items-center gap-2"
          >
            <DollarSign className="h-4 w-4" />
            Adjust Quote
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
