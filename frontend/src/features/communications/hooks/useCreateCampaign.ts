import { useMutation, useQueryClient } from '@tanstack/react-query';
import { campaignsApi } from '../api/campaignsApi';
import type { CampaignCreate, CampaignUpdate } from '../types/campaign';
import { campaignKeys } from './useCampaigns';

/** Create a new campaign (draft) */
export function useCreateCampaign() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (data: CampaignCreate) => campaignsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: campaignKeys.lists() });
    },
  });
}

/** Update a draft campaign (partial fields) */
export function useUpdateCampaign() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CampaignUpdate }) =>
      campaignsApi.update(id, data),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: campaignKeys.detail(id) });
      qc.invalidateQueries({ queryKey: campaignKeys.lists() });
    },
  });
}

/** Delete a campaign */
export function useDeleteCampaign() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => campaignsApi.delete(id),
    onSuccess: (_data, id) => {
      qc.removeQueries({ queryKey: campaignKeys.detail(id) });
      qc.invalidateQueries({ queryKey: campaignKeys.lists() });
    },
  });
}
