import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { type ComponentPropsWithoutRef, type ElementRef, forwardRef } from "react";

import { cn } from "@/lib/utils";

export const TooltipProvider = TooltipPrimitive.Provider;
export const Tooltip = TooltipPrimitive.Root;
export const TooltipTrigger = TooltipPrimitive.Trigger;

export const TooltipContent = forwardRef<
  ElementRef<typeof TooltipPrimitive.Content>,
  ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(({ className, sideOffset = 4, ...props }, ref) => (
  <TooltipPrimitive.Content
    ref={ref}
    sideOffset={sideOffset}
    className={cn(
      "z-50 overflow-hidden rounded-md border border-border bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-card-lg data-[state=delayed-open]:animate-fade-in",
      className,
    )}
    {...props}
  />
));
TooltipContent.displayName = TooltipPrimitive.Content.displayName;
