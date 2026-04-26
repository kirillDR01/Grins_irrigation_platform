import { useCallback, useSyncExternalStore } from 'react';

/**
 * Subscribe to a CSS media query and return whether it currently matches.
 *
 * Uses React 18's useSyncExternalStore for race-free subscription to the
 * matchMedia store — automatically resyncs when `query` changes.
 *
 * @param query - The media query string (e.g. '(max-width: 767px)')
 * @returns true when the query matches the current viewport, false otherwise
 *
 * @example
 *   const isMobile = useMediaQuery('(max-width: 767px)');
 *   const isDark = useMediaQuery('(prefers-color-scheme: dark)');
 */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onStoreChange: () => void) => {
      if (typeof window === 'undefined') return () => {};
      const mediaQuery = window.matchMedia(query);
      mediaQuery.addEventListener('change', onStoreChange);
      return () => mediaQuery.removeEventListener('change', onStoreChange);
    },
    [query]
  );

  const getSnapshot = useCallback(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia(query).matches;
  }, [query]);

  const getServerSnapshot = () => false;

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
