import { describe, it, expect, vi } from 'vitest';
import type { QueryClient } from '@tanstack/react-query';
import {
  invalidateAfterLeadRouting,
  invalidateAfterMarkContacted,
  invalidateAfterCustomerMutation,
} from './invalidationHelpers';
import { dashboardKeys } from '@/features/dashboard/hooks/useDashboard';

function makeMockQueryClient(): QueryClient {
  return { invalidateQueries: vi.fn() } as unknown as QueryClient;
}

describe('invalidationHelpers — dashboard metrics invalidation', () => {
  it('invalidates dashboard metrics on lead routing to sales', () => {
    const queryClient = makeMockQueryClient();
    invalidateAfterLeadRouting(queryClient, 'sales');
    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
      queryKey: dashboardKeys.metrics(),
    });
  });

  it('invalidates dashboard metrics on lead routing to jobs', () => {
    const queryClient = makeMockQueryClient();
    invalidateAfterLeadRouting(queryClient, 'jobs');
    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
      queryKey: dashboardKeys.metrics(),
    });
  });

  it('invalidates dashboard metrics after mark-contacted', () => {
    const queryClient = makeMockQueryClient();
    invalidateAfterMarkContacted(queryClient);
    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
      queryKey: dashboardKeys.metrics(),
    });
  });

  it('invalidates dashboard metrics after customer mutation', () => {
    const queryClient = makeMockQueryClient();
    invalidateAfterCustomerMutation(queryClient, 'cust-123');
    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
      queryKey: dashboardKeys.metrics(),
    });
  });
});
