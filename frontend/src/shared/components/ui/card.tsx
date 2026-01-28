// Minimal stub for card component
import type { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  [key: string]: unknown;
}

export function Card({ children, className, ...props }: CardProps) {
  return <div className={className} {...props}>{children}</div>;
}

export function CardContent({ children, className, ...props }: CardProps) {
  return <div className={className} {...props}>{children}</div>;
}

export function CardHeader({ children, className, ...props }: CardProps) {
  return <div className={className} {...props}>{children}</div>;
}

export function CardTitle({ children, className, ...props }: CardProps) {
  return <h2 className={className} {...props}>{children}</h2>;
}
