import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { settingsApi } from '../api/settingsApi';
import type { BusinessSettings } from '../types';

export const settingsKeys = {
  all: ['settings'] as const,
  detail: () => [...settingsKeys.all, 'detail'] as const,
};

export function useSettings() {
  return useQuery({
    queryKey: settingsKeys.detail(),
    queryFn: () => settingsApi.getSettings(),
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<BusinessSettings>) => settingsApi.updateSettings(data),
    onSuccess: (updated) => {
      qc.setQueryData(settingsKeys.detail(), updated);
    },
  });
}

export function useUploadLogo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => settingsApi.uploadLogo(file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: settingsKeys.detail() });
    },
  });
}
