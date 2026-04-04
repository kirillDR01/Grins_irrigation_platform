/**
 * ResourceMobileView — composed mobile page for field technicians.
 * Stacks ResourceScheduleView on top with ResourceMobileChat below.
 */

import { ResourceScheduleView } from './ResourceScheduleView';
import { ResourceMobileChat } from '@/features/ai/components/ResourceMobileChat';

export function ResourceMobileView() {
  return (
    <div data-testid="resource-mobile-page" className="flex flex-col h-full">
      <ResourceScheduleView />
      <ResourceMobileChat />
    </div>
  );
}
