import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { AuthGate } from "@/auth/AuthGate";
import { AuthProvider } from "@/auth/AuthProvider";
import { ChatProvider } from "@/chat/ChatProvider";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { RootLayout } from "@/components/layout/RootLayout";
import { AuditPage } from "@/pages/AuditPage";
import { CronPage } from "@/pages/CronPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { LoginPage } from "@/pages/LoginPage";
import { LogsPage } from "@/pages/LogsPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { ServicesPage } from "@/pages/ServicesPage";
import { ThemeProvider } from "@/theme/provider";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 5_000, refetchOnWindowFocus: false, retry: 1 },
  },
});

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider delayDuration={300}>
          <BrowserRouter>
            <AuthProvider>
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route
                  element={
                    <AuthGate>
                      <ChatProvider>
                        <RootLayout />
                      </ChatProvider>
                    </AuthGate>
                  }
                >
                  <Route index element={<DashboardPage />} />
                  <Route path="/services" element={<ServicesPage />} />
                  <Route path="/cron" element={<CronPage />} />
                  <Route path="/audit" element={<AuditPage />} />
                  <Route path="/logs" element={<LogsPage />} />
                  <Route path="*" element={<NotFoundPage />} />
                </Route>
              </Routes>
            </AuthProvider>
          </BrowserRouter>
          <Toaster />
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
