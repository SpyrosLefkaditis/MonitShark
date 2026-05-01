import { Toaster as SonnerToaster, type ToasterProps } from "sonner";

import { useTheme } from "@/theme/provider";

export function Toaster(props: ToasterProps) {
  const { theme } = useTheme();
  return (
    <SonnerToaster
      theme={theme}
      richColors
      closeButton
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-card group-[.toaster]:text-card-foreground group-[.toaster]:border-border group-[.toaster]:shadow-card",
          description: "group-[.toast]:text-muted-foreground",
          actionButton: "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground",
          cancelButton: "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground",
        },
      }}
      {...props}
    />
  );
}
