import { useMutation } from '@tanstack/react-query';
import { campaignsApi } from '../api/campaignsApi';
import type { TargetAudience } from '../types/campaign';

/** Preview audience for a target audience filter (returns counts + sample matches) */
export function useAudiencePreview() {
  return useMutation({
    mutationFn: (targetAudience: TargetAudience) =>
      campaignsApi.previewAudience(targetAudience),
  });
}
