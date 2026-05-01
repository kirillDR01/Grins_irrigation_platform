import type { ReactNode } from 'react';
import { useMediaQuery } from '@/shared/hooks/useMediaQuery';
import { OpenOnPhoneLanding } from './OpenOnPhoneLanding';

export function PhoneOnlyGate({ children }: { children: ReactNode }) {
  const isPhone = useMediaQuery('(max-width: 639px)');
  return isPhone ? <>{children}</> : <OpenOnPhoneLanding />;
}
