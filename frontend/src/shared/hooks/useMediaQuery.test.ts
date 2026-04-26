import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useMediaQuery } from './useMediaQuery';

interface MockMediaQueryList {
  matches: boolean;
  media: string;
  onchange: ((this: MediaQueryList, ev: MediaQueryListEvent) => void) | null;
  addEventListener: ReturnType<typeof vi.fn>;
  removeEventListener: ReturnType<typeof vi.fn>;
  addListener: ReturnType<typeof vi.fn>;
  removeListener: ReturnType<typeof vi.fn>;
  dispatchEvent: ReturnType<typeof vi.fn>;
  _trigger: (matches: boolean) => void;
}

function createMockMediaQueryList(
  initialMatches: boolean,
  query = ''
): MockMediaQueryList {
  let listener: ((event: MediaQueryListEvent) => void) | null = null;
  const mql: MockMediaQueryList = {
    matches: initialMatches,
    media: query,
    onchange: null,
    addEventListener: vi.fn((_event: string, l: (event: MediaQueryListEvent) => void) => {
      listener = l;
    }),
    removeEventListener: vi.fn(() => {
      listener = null;
    }),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(() => true),
    _trigger: (matches: boolean) => {
      mql.matches = matches;
      if (listener) {
        listener({ matches, media: query } as MediaQueryListEvent);
      }
    },
  };
  return mql;
}

describe('useMediaQuery', () => {
  let originalMatchMedia: typeof window.matchMedia;
  let mockMql: MockMediaQueryList;

  beforeEach(() => {
    originalMatchMedia = window.matchMedia;
  });

  afterEach(() => {
    window.matchMedia = originalMatchMedia;
    vi.restoreAllMocks();
  });

  it('returns the initial match value when the query matches', () => {
    mockMql = createMockMediaQueryList(true, '(max-width: 767px)');
    window.matchMedia = vi
      .fn()
      .mockReturnValue(mockMql) as unknown as typeof window.matchMedia;

    const { result } = renderHook(() => useMediaQuery('(max-width: 767px)'));

    expect(result.current).toBe(true);
  });

  it('returns false when the query does not match', () => {
    mockMql = createMockMediaQueryList(false, '(max-width: 767px)');
    window.matchMedia = vi
      .fn()
      .mockReturnValue(mockMql) as unknown as typeof window.matchMedia;

    const { result } = renderHook(() => useMediaQuery('(max-width: 767px)'));

    expect(result.current).toBe(false);
  });

  it('updates when the MediaQueryList change event fires', () => {
    mockMql = createMockMediaQueryList(false, '(max-width: 767px)');
    window.matchMedia = vi
      .fn()
      .mockReturnValue(mockMql) as unknown as typeof window.matchMedia;

    const { result } = renderHook(() => useMediaQuery('(max-width: 767px)'));
    expect(result.current).toBe(false);

    act(() => {
      mockMql._trigger(true);
    });

    expect(result.current).toBe(true);
  });

  it('removes the listener on unmount', () => {
    mockMql = createMockMediaQueryList(false, '(max-width: 767px)');
    window.matchMedia = vi
      .fn()
      .mockReturnValue(mockMql) as unknown as typeof window.matchMedia;

    const { unmount } = renderHook(() => useMediaQuery('(max-width: 767px)'));
    expect(mockMql.addEventListener).toHaveBeenCalledTimes(1);

    unmount();

    expect(mockMql.removeEventListener).toHaveBeenCalledTimes(1);
  });

  it('re-subscribes when the query changes', () => {
    const mqlA = createMockMediaQueryList(false, '(max-width: 767px)');
    const mqlB = createMockMediaQueryList(true, '(min-width: 1024px)');
    // The hook calls matchMedia in useState's lazy initializer AND inside the
    // useEffect on mount — so the first two calls receive the same query.
    // After rerender with a new query, the effect calls matchMedia once more.
    const matchMediaMock = vi.fn().mockImplementation((q: string) => {
      if (q === '(max-width: 767px)') return mqlA;
      if (q === '(min-width: 1024px)') return mqlB;
      throw new Error(`Unexpected query: ${q}`);
    });
    window.matchMedia = matchMediaMock as unknown as typeof window.matchMedia;

    const { result, rerender } = renderHook(({ q }: { q: string }) => useMediaQuery(q), {
      initialProps: { q: '(max-width: 767px)' },
    });

    expect(result.current).toBe(false);
    expect(mqlA.addEventListener).toHaveBeenCalledTimes(1);

    rerender({ q: '(min-width: 1024px)' });

    expect(mqlA.removeEventListener).toHaveBeenCalledTimes(1);
    expect(result.current).toBe(true);
  });
});
