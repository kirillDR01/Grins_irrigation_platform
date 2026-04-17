/**
 * Shared routing-action hook for the leads feature.
 *
 * Consolidates the Mark Contacted / Move to Jobs / Move to Sales / Delete
 * handlers, the requires-estimate override dialog state, and the CR-6
 * duplicate-conflict modal state so that ``LeadsList`` and ``LeadDetail``
 * expose identical behavior without duplicating logic.
 *
 * The hook is intentionally navigation-agnostic: callers pass a ``navigate``
 * function so the same logic works in the list view (stays on /leads) and
 * the detail view (navigates to /jobs or /sales on success).
 *
 * Validates: H-1 (bughunt 2026-04-16).
 */
import { useCallback, useState } from 'react';
import { toast } from 'sonner';

import {
  useDeleteLead,
  useMarkContacted,
  useMoveToJobs,
  useMoveToSales,
} from './useLeadMutations';
import { isDuplicateConflict } from '../utils/isDuplicateConflict';
import type { DuplicateConflictCustomer, Lead } from '../types';

/** Action the admin is attempting when a modal opens. */
export type RequiresEstimateTarget = 'jobs' | 'sales';

/** Internal shape for the requires-estimate override dialog state. */
export interface RequiresEstimateState {
  lead: Lead;
  target: RequiresEstimateTarget;
}

/** Internal shape for the CR-6 duplicate conflict modal state. */
export interface ConflictState {
  lead: Lead;
  target: RequiresEstimateTarget;
  duplicates: DuplicateConflictCustomer[];
  phone: string | null;
  email: string | null;
}

/**
 * Optional success redirects. When a caller provides a navigate function,
 * ``navigateOnSuccess`` controls whether the hook navigates after a
 * successful move. ``LeadsList`` keeps the admin on /leads (no redirect);
 * ``LeadDetail`` jumps to /jobs or /sales.
 */
export interface UseLeadRoutingActionsOptions {
  /** Optional react-router navigate. Leave undefined to skip navigation. */
  navigate?: (path: string) => void;
  /** If true, navigate to /jobs or /sales on success. Default: false. */
  navigateOnSuccess?: boolean;
}

export interface UseLeadRoutingActionsResult {
  // Mutation pass-throughs (exposed so callers can read ``isPending``).
  markContactedMutation: ReturnType<typeof useMarkContacted>;
  moveToJobsMutation: ReturnType<typeof useMoveToJobs>;
  moveToSalesMutation: ReturnType<typeof useMoveToSales>;
  deleteLeadMutation: ReturnType<typeof useDeleteLead>;

  // Action callbacks. ``deleteLead`` returns whether the delete succeeded so
  // callers (e.g. LeadDetail) can conditionally navigate away.
  markContacted: (lead: Lead) => Promise<void>;
  moveToJobs: (lead: Lead) => Promise<void>;
  moveToSales: (lead: Lead) => Promise<void>;
  deleteLead: (lead: Lead) => Promise<boolean>;

  // Requires-estimate override modal state + resolvers.
  requiresEstimateState: RequiresEstimateState | null;
  resolveRequiresEstimate: (
    choice: 'jobs-force' | 'sales' | 'cancel',
  ) => Promise<void>;
  closeRequiresEstimate: () => void;

  // CR-6 duplicate-conflict modal state + resolvers.
  conflictState: ConflictState | null;
  onConvertAnyway: () => Promise<void>;
  onUseExisting: (customer: DuplicateConflictCustomer) => void;
  closeConflict: () => void;
}

/**
 * Shared hook driving lead routing actions for ``LeadsList`` and
 * ``LeadDetail``.
 */
export function useLeadRoutingActions(
  options: UseLeadRoutingActionsOptions = {},
): UseLeadRoutingActionsResult {
  const { navigate, navigateOnSuccess = false } = options;

  const markContactedMutation = useMarkContacted();
  const moveToJobsMutation = useMoveToJobs();
  const moveToSalesMutation = useMoveToSales();
  const deleteLeadMutation = useDeleteLead();

  const [requiresEstimateState, setRequiresEstimateState] =
    useState<RequiresEstimateState | null>(null);
  const [conflictState, setConflictState] = useState<ConflictState | null>(null);

  const closeRequiresEstimate = useCallback(() => {
    setRequiresEstimateState(null);
  }, []);

  const closeConflict = useCallback(() => {
    setConflictState(null);
  }, []);

  /** Low-level helper: attempt a move, handling the 409 conflict uniformly. */
  const attemptMoveToJobs = useCallback(
    async (lead: Lead, force: boolean): Promise<boolean> => {
      try {
        const result = await moveToJobsMutation.mutateAsync({
          id: lead.id,
          force,
        });
        if (!force && result.requires_estimate_warning) {
          setRequiresEstimateState({ lead, target: 'jobs' });
          return false;
        }
        toast.success(
          force
            ? `${lead.name} moved to Jobs (estimate override)`
            : `${lead.name} moved to Jobs`,
        );
        if (navigateOnSuccess && navigate) {
          navigate('/jobs');
        }
        return true;
      } catch (error: unknown) {
        if (isDuplicateConflict(error)) {
          const detail = error.response!.data.detail;
          setConflictState({
            lead,
            target: 'jobs',
            duplicates: detail.duplicates,
            phone: detail.phone,
            email: detail.email,
          });
          return false;
        }
        toast.error('Failed to move lead to Jobs');
        return false;
      }
    },
    [moveToJobsMutation, navigate, navigateOnSuccess],
  );

  const attemptMoveToSales = useCallback(
    async (lead: Lead): Promise<boolean> => {
      try {
        const result = await moveToSalesMutation.mutateAsync(lead.id);
        if (result.merged_into_customer) {
          toast.success(
            `Merged into existing customer: ${result.merged_into_customer.name}`,
          );
        } else {
          toast.success(`${lead.name} moved to Sales`);
        }
        if (navigateOnSuccess && navigate) {
          navigate('/sales');
        }
        return true;
      } catch (error: unknown) {
        if (isDuplicateConflict(error)) {
          const detail = error.response!.data.detail;
          setConflictState({
            lead,
            target: 'sales',
            duplicates: detail.duplicates,
            phone: detail.phone,
            email: detail.email,
          });
          return false;
        }
        toast.error('Failed to move lead to Sales');
        return false;
      }
    },
    [moveToSalesMutation, navigate, navigateOnSuccess],
  );

  // ---- Public action callbacks ----

  const markContacted = useCallback(
    async (lead: Lead) => {
      try {
        await markContactedMutation.mutateAsync(lead.id);
        toast.success(`${lead.name} marked as contacted`);
      } catch {
        toast.error('Failed to mark lead as contacted');
      }
    },
    [markContactedMutation],
  );

  const moveToJobs = useCallback(
    async (lead: Lead) => {
      await attemptMoveToJobs(lead, false);
    },
    [attemptMoveToJobs],
  );

  const moveToSales = useCallback(
    async (lead: Lead) => {
      await attemptMoveToSales(lead);
    },
    [attemptMoveToSales],
  );

  const deleteLead = useCallback(
    async (lead: Lead): Promise<boolean> => {
      try {
        await deleteLeadMutation.mutateAsync(lead.id);
        toast.success(`${lead.name} permanently deleted`);
        return true;
      } catch {
        toast.error('Failed to delete lead');
        return false;
      }
    },
    [deleteLeadMutation],
  );

  // ---- Requires-estimate resolver ----

  const resolveRequiresEstimate = useCallback(
    async (choice: 'jobs-force' | 'sales' | 'cancel') => {
      const state = requiresEstimateState;
      if (!state) return;
      setRequiresEstimateState(null);
      if (choice === 'cancel') return;
      if (choice === 'jobs-force') {
        await attemptMoveToJobs(state.lead, true);
        return;
      }
      // 'sales'
      await attemptMoveToSales(state.lead);
    },
    [requiresEstimateState, attemptMoveToJobs, attemptMoveToSales],
  );

  // ---- Conflict modal resolvers ----

  const onConvertAnyway = useCallback(async () => {
    const state = conflictState;
    if (!state) return;
    setConflictState(null);
    if (state.target === 'jobs') {
      // Force past the duplicate check AND any estimate warning.
      await attemptMoveToJobs(state.lead, true);
    } else {
      // move-to-sales currently has no force-flag but calling again lets the
      // admin retry once they've resolved the duplicate on the server side.
      await attemptMoveToSales(state.lead);
    }
  }, [conflictState, attemptMoveToJobs, attemptMoveToSales]);

  const onUseExisting = useCallback(
    (customer: DuplicateConflictCustomer) => {
      setConflictState(null);
      if (navigate) {
        navigate(`/customers/${customer.id}`);
      }
    },
    [navigate],
  );

  return {
    markContactedMutation,
    moveToJobsMutation,
    moveToSalesMutation,
    deleteLeadMutation,
    markContacted,
    moveToJobs,
    moveToSales,
    deleteLead,
    requiresEstimateState,
    resolveRequiresEstimate,
    closeRequiresEstimate,
    conflictState,
    onConvertAnyway,
    onUseExisting,
    closeConflict,
  };
}
