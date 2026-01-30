import * as React from "react";
import { cn } from "@/shared/utils/cn";

interface SwitchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
}

const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
  ({ className, checked, onCheckedChange, disabled, ...props }, ref) => {
    return (
      <label className={cn("relative inline-flex items-center cursor-pointer", disabled && "cursor-not-allowed")}>
        <input
          type="checkbox"
          ref={ref}
          checked={checked}
          onChange={(e) => onCheckedChange?.(e.target.checked)}
          disabled={disabled}
          className="sr-only peer"
          {...props}
        />
        {/* Track */}
        <div
          className={cn(
            "relative w-11 h-6 rounded-full bg-slate-200 transition-colors",
            "peer-checked:bg-teal-500",
            "peer-focus:ring-2 peer-focus:ring-teal-100 peer-focus:ring-offset-2",
            "peer-disabled:opacity-50",
            className
          )}
        >
          {/* Thumb */}
          <span
            className={cn(
              "absolute w-5 h-5 rounded-full bg-white shadow-sm transition-transform",
              "top-0.5 left-0.5",
              checked && "translate-x-5"
            )}
          />
        </div>
      </label>
    );
  }
);

Switch.displayName = "Switch";

export { Switch };
