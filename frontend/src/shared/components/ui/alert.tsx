import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/shared/utils/cn"

const alertVariants = cva(
  "bg-white p-4 rounded-xl shadow-sm border-l-4 relative",
  {
    variants: {
      variant: {
        default: "border-slate-400",
        warning: "border-amber-400",
        error: "border-red-400",
        success: "border-emerald-400",
        info: "border-blue-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

const iconContainerVariants = cva(
  "p-2 rounded-full inline-flex items-center justify-center",
  {
    variants: {
      variant: {
        default: "bg-slate-100 text-slate-600",
        warning: "bg-amber-100 text-amber-600",
        error: "bg-red-100 text-red-600",
        success: "bg-emerald-100 text-emerald-600",
        info: "bg-blue-100 text-blue-600",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

const actionButtonVariants = cva(
  "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "text-slate-600 bg-slate-50 hover:bg-slate-100",
        warning: "text-amber-600 bg-amber-50 hover:bg-amber-100",
        error: "text-red-600 bg-red-50 hover:bg-red-100",
        success: "text-emerald-600 bg-emerald-50 hover:bg-emerald-100",
        info: "text-blue-600 bg-blue-50 hover:bg-blue-100",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {}

const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant, ...props }, ref) => (
    <div
      ref={ref}
      role="alert"
      className={cn(alertVariants({ variant }), className)}
      data-testid="alert"
      {...props}
    />
  )
)
Alert.displayName = "Alert"

interface AlertIconProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof iconContainerVariants> {}

const AlertIcon = React.forwardRef<HTMLDivElement, AlertIconProps>(
  ({ className, variant, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(iconContainerVariants({ variant }), className)}
      {...props}
    />
  )
)
AlertIcon.displayName = "AlertIcon"

const AlertTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h5
    ref={ref}
    className={cn("text-slate-800 font-medium", className)}
    {...props}
  />
))
AlertTitle.displayName = "AlertTitle"

const AlertDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-slate-500 text-sm", className)}
    {...props}
  />
))
AlertDescription.displayName = "AlertDescription"

interface AlertActionProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof actionButtonVariants> {}

const AlertAction = React.forwardRef<HTMLButtonElement, AlertActionProps>(
  ({ className, variant, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(actionButtonVariants({ variant }), className)}
      {...props}
    />
  )
)
AlertAction.displayName = "AlertAction"

export { Alert, AlertIcon, AlertTitle, AlertDescription, AlertAction }
