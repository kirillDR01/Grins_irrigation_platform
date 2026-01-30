import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/shared/utils/cn"

const badgeVariants = cva(
  "inline-flex items-center px-3 py-1 rounded-full text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-slate-100 text-slate-700",
        // Status color variants
        success: "bg-emerald-100 text-emerald-700",
        warning: "bg-amber-100 text-amber-700",
        error: "bg-red-100 text-red-700",
        info: "bg-blue-100 text-blue-700",
        scheduled: "bg-violet-100 text-violet-700",
        teal: "bg-teal-50 text-teal-600",
        orange: "bg-orange-100 text-orange-700",
        // Outline variants
        "success-outline": "bg-emerald-50 text-emerald-600 border border-emerald-100",
        "warning-outline": "bg-amber-50 text-amber-600 border border-amber-100",
        "info-outline": "bg-blue-50 text-blue-600 border border-blue-100",
        "rose-outline": "bg-rose-50 text-rose-600 border border-rose-100",
        // Secondary/muted
        secondary: "bg-slate-100 text-slate-500",
        // Destructive
        destructive: "bg-red-100 text-red-700",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
