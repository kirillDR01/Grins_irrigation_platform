/**
 * Hook for parsing natural language constraints.
 */

import { useMutation } from '@tanstack/react-query';
import { scheduleGenerationApi } from '../api/scheduleGenerationApi';
import type { ParseConstraintsRequest, ParseConstraintsResponse } from '../types';

export function useConstraintParser() {
  return useMutation<ParseConstraintsResponse, Error, ParseConstraintsRequest>({
    mutationFn: (request) => scheduleGenerationApi.parseConstraints(request),
  });
}
