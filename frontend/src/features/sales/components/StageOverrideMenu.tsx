import type { ReactNode } from 'react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { STAGES, type StageKey } from '../types/pipeline';

interface StageOverrideMenuProps {
  currentStage: StageKey | null;
  onSelect: (stage: StageKey) => void;
  children: ReactNode;
}

const STAGE_LABELS: Record<StageKey, string> = {
  schedule_estimate: 'Schedule',
  send_estimate: 'Estimate',
  pending_approval: 'Approval',
  send_contract: 'Contract',
  closed_won: 'Closed',
};

export function StageOverrideMenu({
  currentStage,
  onSelect,
  children,
}: StageOverrideMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>{children}</DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        data-testid="stage-override-menu"
        className="min-w-44"
      >
        {STAGES.map((stage) => {
          const isCurrent = stage.key === currentStage;
          return (
            <DropdownMenuItem
              key={stage.key}
              data-testid={`stage-override-${stage.key}`}
              disabled={isCurrent}
              onSelect={() => {
                if (!isCurrent) onSelect(stage.key);
              }}
              className={isCurrent ? 'opacity-60' : undefined}
            >
              {STAGE_LABELS[stage.key]}
              {isCurrent && (
                <span className="ml-auto text-xs text-slate-400">current</span>
              )}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
