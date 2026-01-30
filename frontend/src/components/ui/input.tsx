import * as React from "react"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        // Base styling
        "h-9 w-full min-w-0 rounded-lg border border-slate-200 bg-white px-3 py-1 text-sm text-slate-700",
        "placeholder:text-slate-400",
        "transition-all duration-200 outline-none",
        // Focus state - teal focus ring
        "focus:border-teal-500 focus:ring-2 focus:ring-teal-100",
        // Disabled state
        "disabled:bg-slate-100 disabled:text-slate-400 disabled:cursor-not-allowed disabled:opacity-50",
        // File input styling
        "file:text-foreground file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium",
        // Selection styling
        "selection:bg-primary selection:text-primary-foreground",
        // Dark mode
        "dark:bg-slate-800 dark:border-slate-700 dark:text-slate-200 dark:placeholder:text-slate-500",
        "dark:focus:border-teal-400 dark:focus:ring-teal-900",
        // Invalid state
        "aria-invalid:ring-red-100 aria-invalid:border-red-500 dark:aria-invalid:ring-red-900 dark:aria-invalid:border-red-400",
        className
      )}
      {...props}
    />
  )
}

export { Input }
