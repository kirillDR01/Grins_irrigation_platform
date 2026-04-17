/**
 * useBusinessSettings — React-Query wrappers around /api/v1/settings/business.
 *
 * H-12 (bughunt 2026-04-16): firm-wide threshold knobs. Invalidates the
 * lien-candidate query on mutation success so the review queue reflects the
 * new threshold without a page reload.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  businessSettingsApi,
  type BusinessThresholds,
  type BusinessThresholdsUpdate,
} from '../api/businessSettingsApi';

export const businessSettingsKeys = {
  all: ['business-settings'] as const,
  detail: () => [...businessSettingsKeys.all, 'detail'] as const,
};

export function useBusinessSettings() {
  return useQuery<BusinessThresholds>({
    queryKey: businessSettingsKeys.detail(),
    queryFn: () => businessSettingsApi.getBusinessThresholds(),
  });
}

export function useUpdateBusinessSettings() {
  const queryClient = useQueryClient();
  return useMutation<BusinessThresholds, Error, BusinessThresholdsUpdate>({
    mutationFn: (data) => businessSettingsApi.updateBusinessThresholds(data),
    onSuccess: (fresh) => {
      queryClient.setQueryData(businessSettingsKeys.detail(), fresh);
      // Lien thresholds feed the review queue; invalidate it too.
      queryClient.invalidateQueries({ queryKey: ['invoices', 'lien-candidates'] });
    },
  });
}
