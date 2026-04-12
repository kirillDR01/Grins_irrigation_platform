import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { salesPipelineApi } from '../api/salesPipelineApi';
import type { SalesEntryStatusUpdate } from '../types/pipeline';
import type {
  SalesCalendarEventCreate,
  SalesCalendarEventUpdate,
} from '../types/pipeline';

export const pipelineKeys = {
  all: ['sales-pipeline'] as const,
  lists: () => [...pipelineKeys.all, 'list'] as const,
  list: (params?: { skip?: number; limit?: number; status?: string }) =>
    [...pipelineKeys.lists(), params] as const,
  detail: (id: string) => [...pipelineKeys.all, 'detail', id] as const,
  documents: (customerId: string) =>
    [...pipelineKeys.all, 'documents', customerId] as const,
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
      qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
    },
  });
}

export function useForceConvertToJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => salesPipelineApi.forceConvert(id),
    onSuccess: () => {
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
      qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
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
    mutationFn: (body: SalesCalendarEventCreate) =>
      salesPipelineApi.createCalendarEvent(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: pipelineKeys.calendarEvents() });
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
      qc.invalidateQueries({ queryKey: pipelineKeys.calendarEvents() });
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
