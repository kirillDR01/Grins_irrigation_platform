import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { salesPipelineApi } from '../api/salesPipelineApi';
import type { SalesEntryStatusUpdate } from '../types/pipeline';
import type {
  SalesCalendarEventCreate,
  SalesCalendarEventUpdate,
} from '../types/pipeline';
import {
  invalidateAfterSalesPipelineTransition,
} from '@/shared/utils/invalidationHelpers';

export const pipelineKeys = {
  all: ['sales-pipeline'] as const,
  lists: () => [...pipelineKeys.all, 'list'] as const,
  list: (params?: { skip?: number; limit?: number; status?: string }) =>
    [...pipelineKeys.lists(), params] as const,
  detail: (id: string) => [...pipelineKeys.all, 'detail', id] as const,
  documents: (customerId: string) =>
    [...pipelineKeys.all, 'documents', customerId] as const,
  documentPresign: (customerId: string, documentId: string) =>
    [...pipelineKeys.all, 'documents', customerId, documentId, 'presign'] as const,
  calendarEvents: () => [...pipelineKeys.all, 'calendar'] as const,
  calendarEventList: (params?: {
    start_date?: string;
    end_date?: string;
    sales_entry_id?: string;
  }) => [...pipelineKeys.calendarEvents(), params] as const,
};

export function useSalesPipeline(params?: {
  skip?: number;
  limit?: number;
  status?: string;
}) {
  return useQuery({
    queryKey: pipelineKeys.list(params),
    queryFn: () => salesPipelineApi.list(params),
  });
}

export function useSalesEntry(id: string) {
  return useQuery({
    queryKey: pipelineKeys.detail(id),
    queryFn: () => salesPipelineApi.get(id),
    enabled: !!id,
  });
}

export function useAdvanceSalesEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => salesPipelineApi.advance(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
    },
  });
}

export function useOverrideSalesStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: SalesEntryStatusUpdate }) =>
      salesPipelineApi.overrideStatus(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
    },
  });
}

export function useConvertToJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => salesPipelineApi.convert(id),
    onSuccess: () => {
      invalidateAfterSalesPipelineTransition(qc, true);
    },
  });
}

export function useForceConvertToJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => salesPipelineApi.forceConvert(id),
    onSuccess: () => {
      invalidateAfterSalesPipelineTransition(qc, true);
    },
  });
}

// NEW-D: pause/unpause nudges, send text confirmation, dismiss row.
// Mirror the invalidation strategy used by useOverrideSalesStatus —
// each mutation invalidates the entry detail and the lists view.

export function usePauseNudges() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => salesPipelineApi.pauseNudges(id),
    onSuccess: (entry) => {
      qc.invalidateQueries({ queryKey: pipelineKeys.detail(entry.id) });
      qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
    },
  });
}

export function useUnpauseNudges() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => salesPipelineApi.unpauseNudges(id),
    onSuccess: (entry) => {
      qc.invalidateQueries({ queryKey: pipelineKeys.detail(entry.id) });
      qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
    },
  });
}

export function useSendTextConfirmation() {
  return useMutation({
    mutationFn: (id: string) => salesPipelineApi.sendTextConfirmation(id),
  });
}

export function useDismissSalesEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => salesPipelineApi.dismiss(id),
    onSuccess: (entry) => {
      qc.invalidateQueries({ queryKey: pipelineKeys.detail(entry.id) });
      qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
    },
  });
}

export function useMarkSalesLost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      closedReason,
    }: {
      id: string;
      closedReason?: string;
    }) => salesPipelineApi.markLost(id, closedReason),
    onSuccess: () => {
      invalidateAfterSalesPipelineTransition(qc);
    },
  });
}

export function useTriggerEmailSigning() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => salesPipelineApi.triggerEmailSigning(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
    },
  });
}

export function useGetEmbeddedSigningUrl() {
  return useMutation({
    mutationFn: (id: string) => salesPipelineApi.getEmbeddedSigningUrl(id),
  });
}

export function useSalesDocuments(customerId: string) {
  return useQuery({
    queryKey: pipelineKeys.documents(customerId),
    queryFn: () => salesPipelineApi.listDocuments(customerId),
    enabled: !!customerId,
  });
}

export function useUploadSalesDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      customerId,
      file,
      documentType,
    }: {
      customerId: string;
      file: File;
      documentType: string;
    }) => salesPipelineApi.uploadDocument(customerId, file, documentType),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({
        queryKey: pipelineKeys.documents(variables.customerId),
      });
    },
  });
}

/**
 * bughunt M-17: resolve a document's presigned download URL at render
 * time so a stored ``file_key`` that no longer exists in S3 (404) or
 * has expired surfaces as a hook ``error`` rather than an empty/broken
 * iframe when the user clicks Sign or Download. Components can read
 * ``isLoading`` for spinners and ``error``/``data == null`` to gate
 * their action buttons.
 *
 * Backed by the existing /customers/{cid}/documents/{did}/download
 * endpoint, which returns a presigned S3 URL with a 1-hour TTL.
 */
export function useDocumentPresign(
  customerId: string | null | undefined,
  documentId: string | null | undefined,
) {
  const enabled = Boolean(customerId && documentId);
  return useQuery({
    queryKey:
      customerId && documentId
        ? pipelineKeys.documentPresign(customerId, documentId)
        : ['sales-pipeline', 'documents', 'idle'],
    queryFn: () =>
      salesPipelineApi.downloadDocument(customerId as string, documentId as string),
    enabled,
    // Presigned URLs expire after ~1 hour; refetch a bit early so the
    // signing iframe never opens on a near-expired URL.
    staleTime: 50 * 60 * 1000,
    retry: false,
  });
}

export function useDownloadSalesDocument() {
  return useMutation({
    mutationFn: ({
      customerId,
      documentId,
    }: {
      customerId: string;
      documentId: string;
    }) => salesPipelineApi.downloadDocument(customerId, documentId),
  });
}

export function useDeleteSalesDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      customerId,
      documentId,
    }: {
      customerId: string;
      documentId: string;
    }) => salesPipelineApi.deleteDocument(customerId, documentId),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({
        queryKey: pipelineKeys.documents(variables.customerId),
      });
    },
  });
}

// Calendar event hooks — Req 15.1, 15.2, 15.3

export function useSalesCalendarEvents(params?: {
  start_date?: string;
  end_date?: string;
  sales_entry_id?: string;
}) {
  return useQuery({
    queryKey: pipelineKeys.calendarEventList(params),
    queryFn: () => salesPipelineApi.listCalendarEvents(params),
  });
}

export function useCreateCalendarEvent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: {
      body: SalesCalendarEventCreate;
      sendConfirmation?: boolean;
    }) =>
      salesPipelineApi.createCalendarEvent(args.body, {
        sendConfirmation: args.sendConfirmation,
      }),
    onSuccess: (_data, args) => {
      qc.invalidateQueries({ queryKey: pipelineKeys.calendarEvents() });
      qc.invalidateQueries({
        queryKey: pipelineKeys.detail(args.body.sales_entry_id),
      });
      qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
    },
  });
}

/**
 * Send or resend the estimate-visit Y/R/C SMS for a SalesCalendarEvent.
 * Used by the modal's primary submit (combined create+send) fallback path
 * and by the NowCard "Resend confirmation text" button.
 */
export function useSendCalendarEventConfirmation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      eventId,
      resend,
    }: {
      eventId: string;
      resend?: boolean;
    }) =>
      salesPipelineApi.sendCalendarEventConfirmation(eventId, { resend }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: pipelineKeys.calendarEvents() });
      qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
    },
  });
}

export function useUpdateCalendarEvent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      eventId,
      body,
    }: {
      eventId: string;
      body: SalesCalendarEventUpdate;
    }) => salesPipelineApi.updateCalendarEvent(eventId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: pipelineKeys.all });
    },
  });
}

export function useDeleteCalendarEvent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (eventId: string) =>
      salesPipelineApi.deleteCalendarEvent(eventId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: pipelineKeys.calendarEvents() });
    },
  });
}
