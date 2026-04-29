// @ts-nocheck — pre-existing TS errors documented in bughunt/2026-04-29-pre-existing-tsc-errors.md
/**
 * ResourceMobileView — composed mobile page for Resource role.
 * Stacks ResourceScheduleView on top, ResourceMobileChat below.
 */

import { ResourceScheduleView } from './ResourceScheduleView';
import { ResourceMobileChat } from '@/features/ai';

export function ResourceMobileView() {
  return (
    <div
      className="flex flex-col min-h-screen bg-slate-50"
      data-testid="resource-mobile-page"
    >
      <ResourceScheduleView />
      <ResourceMobileChat />
    </div>
  );
}
