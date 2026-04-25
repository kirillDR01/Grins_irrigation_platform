/**
 * TanStack Query key factory for passkey-related queries.
 */

export const passkeyKeys = {
  all: ['passkeys'] as const,
  lists: () => [...passkeyKeys.all, 'list'] as const,
  list: () => [...passkeyKeys.lists()] as const,
  detail: (id: string) => [...passkeyKeys.all, 'detail', id] as const,
};
