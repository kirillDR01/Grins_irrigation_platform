// Minimal stub for select component
import type { ReactNode } from 'react';

interface SelectProps {
  children: ReactNode;
  value?: string;
  onValueChange?: (value: string) => void;
}

interface SelectContentProps {
  children: ReactNode;
}

interface SelectItemProps {
  children: ReactNode;
  value: string;
  [key: string]: unknown;
}

interface SelectTriggerProps {
  children: ReactNode;
  className?: string;
}

interface SelectValueProps {
  placeholder?: string;
}

export function Select({ children, value }: SelectProps) {
  return (
    <div data-value={value} data-component="select">
      {children}
    </div>
  );
}

export function SelectContent({ children }: SelectContentProps) {
  return <div data-component="select-content">{children}</div>;
}

export function SelectItem({ children, value, ...props }: SelectItemProps) {
  return (
    <div role="option" data-value={value} {...props}>
      {children}
    </div>
  );
}

export function SelectTrigger({ children, className }: SelectTriggerProps) {
  return (
    <div role="combobox" className={className}>
      {children}
    </div>
  );
}

export function SelectValue({ placeholder }: SelectValueProps) {
  return <span>{placeholder}</span>;
}
