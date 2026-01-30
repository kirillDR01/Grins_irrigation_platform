import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-teal-100 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive",
  {
    variants: {
      variant: {
        default: "bg-teal-500 hover:bg-teal-600 text-white rounded-lg shadow-sm shadow-teal-200 dark:shadow-teal-900/30",
        destructive:
          "bg-red-500 hover:bg-red-600 text-white rounded-lg focus-visible:ring-red-100 dark:focus-visible:ring-red-900/40",
        outline:
          "border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-lg dark:border-slate-700 dark:hover:bg-slate-800 dark:text-slate-200",
        secondary:
          "bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 rounded-lg dark:bg-slate-800 dark:hover:bg-slate-700 dark:border-slate-700 dark:text-slate-200",
        ghost:
          "hover:bg-slate-100 text-slate-600 rounded-lg dark:hover:bg-slate-800 dark:text-slate-300",
        link: "text-teal-600 underline-offset-4 hover:underline hover:text-teal-700 dark:text-teal-400 dark:hover:text-teal-300",
      },
      size: {
        default: "h-10 px-5 py-2.5 has-[>svg]:px-4",
        sm: "h-8 rounded-lg gap-1.5 px-3 has-[>svg]:px-2.5",
        lg: "h-11 rounded-lg px-6 has-[>svg]:px-5",
        icon: "size-10 rounded-lg",
        "icon-sm": "size-8 rounded-lg",
        "icon-lg": "size-11 rounded-lg",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
