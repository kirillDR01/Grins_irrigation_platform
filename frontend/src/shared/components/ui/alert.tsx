// Minimal stub for alert component
import type { ReactNode } from 'react';

interface AlertProps {
  children: ReactNode;
  className?: string;
  variant?: string;
  [key: string]: unknown;
}

interface AlertDescriptionProps {
  children: ReactNode;
  className?: string;
  [key: string]: unknown;
}

export function Alert({ children, className, variant, ...props }: AlertProps) {
  return <div className={className} data-variant={variant} {...props}>{children}</div>;
}

export function AlertDescription({ children, className, ...props }: AlertDescriptionProps) {
  return <div className={className} {...props}>{children}</div>;
}
