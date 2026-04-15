import { useMutation } from '@tanstack/react-query';
import { campaignsApi } from '../api/campaignsApi';

/** Upload a CSV file for ad-hoc audience with staff attestation */
export function useAudienceCsv() {
  return useMutation({
    mutationFn: ({
      file,
      attestation,
    }: {
      file: File;
      attestation: {
        staff_attestation_confirmed: boolean;
        attestation_text_shown: string;
        attestation_version: string;
      };
    }) => campaignsApi.uploadCsv(file, attestation),
  });
}
