import { useQuery } from '@tanstack/react-query';
import { customerApi } from '../api/customerApi';
import type { MergeFieldSelection } from '../types';
import { customerKeys } from './useCustomers';

export function usePreviewMerge(
  primaryId: string,
  duplicateId: string,
  fieldSelections: MergeFieldSelection[],
  enabled: boolean,
) {
  return useQuery({
    queryKey: [...customerKeys.all, 'merge-preview', primaryId, duplicateId, fieldSelections],
    queryFn: () =>
      customerApi.previewMerge(primaryId, {
        duplicate_id: duplicateId,
        field_selections: fieldSelections,
      }),
    enabled,
    staleTime: 30_000,
  });
}
