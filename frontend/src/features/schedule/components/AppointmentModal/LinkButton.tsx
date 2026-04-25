import { type ReactNode } from 'react';
import { cn } from '@/shared/utils/cn';

type LinkButtonVariant = 'default' | 'active' | 'destructive';

interface LinkButtonProps {
  children: ReactNode;
  onClick?: () => void;
  icon?: ReactNode;
  variant?: LinkButtonVariant;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
  'aria-label'?: string;
  title?: string;
  className?: string;
}

const variantStyles: Record<LinkButtonVariant, string> = {
  default:
    'bg-white border-[#E5E7EB] text-[#374151] hover:bg-gray-50 hover:border-gray-300',
  active: 'bg-[#EDE9FE] border-[#6D28D9] text-[#6D28D9]',
  destructive: 'bg-white border-[#FCA5A5] text-[#B91C1C] hover:bg-red-50',
};

export function LinkButton({
  children,
  onClick,
  icon,
  variant = 'default',
  disabled,
  type = 'button',
  'aria-label': ariaLabel,
  title,
  className,
}: LinkButtonProps) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      title={title}
      className={cn(
        'inline-flex items-center justify-center gap-[6px] min-h-[44px] px-3',
        'rounded-[12px] border-[1.5px] text-[14px] font-bold',
        'transition-colors duration-150',
        variantStyles[variant],
        disabled && 'opacity-50 cursor-not-allowed',
        className
      )}
    >
      {icon && (
        <span className="w-4 h-4 flex items-center justify-center flex-shrink-0 [&>svg]:w-4 [&>svg]:h-4 [&>svg]:stroke-[2.2]">
          {icon}
        </span>
      )}
      {children}
    </button>
  );
}
