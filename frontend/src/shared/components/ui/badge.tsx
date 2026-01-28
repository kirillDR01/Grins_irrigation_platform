// Minimal stub for badge component
import type { ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  className?: string;
  variant?: string;
  [key: string]: unknown;
}

export function Badge({ children, className, variant, ...props }: BadgeProps) {
  return <span className={className} data-variant={variant} {...props}>{children}</span>;
}
