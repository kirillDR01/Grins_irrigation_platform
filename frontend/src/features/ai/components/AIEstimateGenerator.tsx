import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { AlertCircle, FileText, Calendar, DollarSign, Calculator, RefreshCw } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import type { EstimateResponse, EstimateSimilarJob } from '../types';

interface AIEstimateGeneratorProps {
  estimate: EstimateResponse | null;
  isLoading: boolean;
  error: Error | null;
  onGeneratePDF: () => void;
  onScheduleSiteVisit: () => void;
  onAdjustQuote: () => void;
  onRegenerate?: () => void;
}

export function AIEstimateGenerator({
  estimate,
  isLoading,
  error,
  onGeneratePDF,
  onScheduleSiteVisit,
  onAdjustQuote,
  onRegenerate,
}: AIEstimateGeneratorProps) {
  if (isLoading) {
    return (
      <Card data-testid="ai-estimate-generator-loading" className="bg-white rounded-2xl shadow-sm border border-slate-100">
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <div className="w-12 h-12 border-4 border-teal-200 border-t-teal-500 rounded-full animate-spin" />
            <span className="ml-3 text-slate-600">Generating estimate...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card data-testid="ai-estimate-generator-error" className="bg-white rounded-2xl shadow-sm border border-slate-100">
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
    <Card data-testid="ai-estimate-generator" className="bg-white rounded-2xl shadow-sm border border-slate-100">
      <CardHeader className="p-6 border-b border-slate-100 bg-slate-50/50">
        <div className="flex items-center gap-2">
          <Calculator className="h-5 w-5 text-teal-500" />
          <CardTitle className="text-lg font-bold text-slate-800">AI-Generated Estimate</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="p-6 space-y-6">
        {/* Estimate Analysis */}
        <div>
          <h3 className="font-semibold text-slate-800 mb-2">Property Analysis</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-sm text-slate-600">Estimated Zones:</span>
              <span className="ml-2 font-medium text-slate-800">{estimate.estimated_zones}</span>
            </div>
            <div>
              <span className="text-sm text-slate-600">Confidence:</span>
              <Badge 
                variant={estimate.confidence_score >= 0.85 ? 'default' : 'secondary'}
                className="ml-2"
              >
                {Math.round(estimate.confidence_score * 100)}%
              </Badge>
            </div>
          </div>
        </div>

        <Separator className="bg-slate-100" />

        {/* Similar Jobs */}
        {estimate.similar_jobs && estimate.similar_jobs.length > 0 && (
          <>
            <div data-testid="similar-jobs">
              <h3 className="font-semibold text-slate-800 mb-2">Similar Completed Jobs</h3>
              <div className="space-y-2">
                {estimate.similar_jobs.map((job: EstimateSimilarJob, idx: number) => (
                  <div key={idx} className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                    <div>
                      <span className="text-sm text-slate-700">{job.service_type}</span>
                      <span className="text-xs text-slate-500 ml-2">
                        {job.zone_count} zones
                      </span>
                    </div>
                    <span className="font-medium text-slate-800">${job.final_price.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
            <Separator className="bg-slate-100" />
          </>
        )}

        {/* Price Breakdown */}
        <div data-testid="estimate-breakdown" className="bg-slate-50 rounded-xl p-4">
          <h3 className="font-semibold text-slate-800 mb-3">Price Breakdown</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-slate-600">Materials:</span>
              <span className="font-medium text-slate-800">${estimate.breakdown.materials.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-slate-600">Labor:</span>
              <span className="font-medium text-slate-800">${estimate.breakdown.labor.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-slate-600">Equipment:</span>
              <span className="font-medium text-slate-800">${estimate.breakdown.equipment.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-slate-600">Margin:</span>
              <span className="font-medium text-slate-800">${estimate.breakdown.margin.toFixed(2)}</span>
            </div>
            <Separator className="bg-slate-200 my-3" />
            <div className="flex justify-between text-xl font-bold text-slate-800">
              <span>Total Estimate:</span>
              <span>${estimate.estimated_price.toFixed(2)}</span>
            </div>
          </div>
        </div>

        {/* Confidence Indicator */}
        <div data-testid="confidence-indicator">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-slate-700">Confidence Level</span>
            <span className="text-sm font-bold text-teal-600">
              {Math.round(estimate.confidence_score * 100)}%
            </span>
          </div>
          <div className="w-full bg-slate-200 rounded-full h-2">
            <div 
              className="bg-teal-500 h-2 rounded-full transition-all"
              style={{ width: `${estimate.confidence_score * 100}%` }}
            />
          </div>
        </div>

        {/* AI Recommendation */}
        {estimate.recommendation && (
          <>
            <Separator className="bg-slate-100" />
            <Alert className="bg-teal-50 border-teal-100">
              <AlertCircle className="h-4 w-4 text-teal-600" />
              <AlertDescription className="text-slate-700">
                <strong className="text-slate-800">AI Recommendation:</strong> {estimate.recommendation}
              </AlertDescription>
            </Alert>
          </>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 flex-wrap">
          {onRegenerate && (
            <Button
              onClick={onRegenerate}
              variant="outline"
              data-testid="regenerate-btn"
              className="flex items-center gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Regenerate
            </Button>
          )}
          <Button
            onClick={onAdjustQuote}
            data-testid="adjust-quote-btn"
            className="flex items-center gap-2 bg-teal-500 hover:bg-teal-600 text-white"
          >
            <DollarSign className="h-4 w-4" />
            Apply to Job
          </Button>
          <Button
            onClick={onGeneratePDF}
            variant="outline"
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
            Schedule Visit
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
