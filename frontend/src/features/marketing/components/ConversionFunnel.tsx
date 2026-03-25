import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/shared/utils/cn';
import type { FunnelStage } from '../types';

interface ConversionFunnelProps {
  stages: FunnelStage[];
}

const stageColors = [
  'bg-teal-500',
  'bg-teal-400',
  'bg-emerald-400',
  'bg-emerald-300',
];

export function ConversionFunnel({ stages }: ConversionFunnelProps) {
  const maxCount = stages.length > 0 ? Math.max(...stages.map((s) => s.count), 1) : 1;

  return (
    <Card data-testid="conversion-funnel">
      <CardHeader>
        <CardTitle className="text-lg">Conversion Funnel</CardTitle>
      </CardHeader>
      <CardContent>
        {stages.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-4">No funnel data available</p>
        ) : (
          <div className="space-y-3">
            {stages.map((stage, index) => {
              const widthPercent = Math.max((stage.count / maxCount) * 100, 8);
              return (
                <div key={stage.stage} className="space-y-1" data-testid={`funnel-stage-${index}`}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-slate-700">{stage.stage}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-slate-800 font-semibold">{stage.count}</span>
                      {index > 0 && stage.conversion_rate != null && (
                        <span className="text-xs text-slate-400">
                          ({stage.conversion_rate.toFixed(1)}%)
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="h-8 bg-slate-100 rounded-md overflow-hidden">
                    <div
                      className={cn(
                        'h-full rounded-md transition-all duration-500',
                        stageColors[index % stageColors.length],
                      )}
                      style={{ width: `${widthPercent}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
