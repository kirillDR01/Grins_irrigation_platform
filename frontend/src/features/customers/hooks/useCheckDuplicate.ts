/**
 * Hook for Tier 1 duplicate check on customer create/convert.
 *
 * Validates: Requirement 6.13
 */

import { useState, useCallback } from 'react';
import { customerApi } from '../api/customerApi';
import type { Customer } from '../types';

interface UseCheckDuplicateResult {
  matches: Customer[];
  isChecking: boolean;
  check: (params: { phone?: string; email?: string; exclude_id?: string }) => Promise<Customer[]>;
  clear: () => void;
}

export function useCheckDuplicate(): UseCheckDuplicateResult {
  const [matches, setMatches] = useState<Customer[]>([]);
  const [isChecking, setIsChecking] = useState(false);

  const check = useCallback(
    async (params: { phone?: string; email?: string; exclude_id?: string }) => {
      if (!params.phone && !params.email) {
        setMatches([]);
        return [];
      }
      setIsChecking(true);
      try {
        const result = await customerApi.checkDuplicate(params);
        setMatches(result);
        return result;
      } catch {
        setMatches([]);
        return [];
      } finally {
        setIsChecking(false);
      }
    },
    [],
  );

  const clear = useCallback(() => setMatches([]), []);

  return { matches, isChecking, check, clear };
}
