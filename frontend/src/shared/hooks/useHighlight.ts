import { useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';

/**
 * Hook that reads `?highlight=<id>` from the URL and provides:
 * - `highlightId`: the ID to highlight (null if not present)
 * - `isHighlighted(id)`: check if a given ID should be highlighted
 * - `highlightRef`: callback ref to attach to the highlighted element for auto-scroll
 *
 * The CSS animation (`animate-highlight-pulse`) handles the 3-second fade.
 * The highlight param stays in the URL for refresh persistence.
 */
export function useHighlight() {
  const [searchParams] = useSearchParams();
  const highlightId = searchParams.get('highlight');

  const isHighlighted = useCallback(
    (id: string) => highlightId === id,
    [highlightId],
  );

  // Callback ref for auto-scroll to the first highlighted element
  const highlightRef = useCallback(
    (node: HTMLElement | null) => {
      if (node) {
        node.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    },
    [],
  );

  return { highlightId, isHighlighted, highlightRef };
}
