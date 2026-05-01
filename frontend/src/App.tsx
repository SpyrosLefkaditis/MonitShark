import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { RootLayout } from "@/components/layout/RootLayout";
import { AuditPage } from "@/pages/AuditPage";
import { CronPage } from "@/pages/CronPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { LogsPage } from "@/pages/LogsPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { ServicesPage } from "@/pages/ServicesPage";
import { ThemeProvider } from "@/theme/provider";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 5_000, refetchOnWindowFocus: false },
  },
});

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider delayDuration={300}>
          <BrowserRouter>
            <Routes>
              <Route element={<RootLayout />}>
                <Route index element={<DashboardPage />} />
                <Route path="/services" element={<ServicesPage />} />
                <Route path="/cron" element={<CronPage />} />
                <Route path="/audit" element={<AuditPage />} />
                <Route path="/logs" element={<LogsPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Route>
            </Routes>
          </BrowserRouter>
          <Toaster />
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
