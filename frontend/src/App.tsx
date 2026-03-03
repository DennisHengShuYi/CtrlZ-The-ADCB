import { Routes, Route, Navigate } from "react-router-dom";
import { SignedIn, SignedOut } from "@clerk/clerk-react";
import LoginPage from "./pages/LoginPage";
import DashboardLayout from "./components/DashboardLayout";
import OverviewPage from "./pages/OverviewPage";
import InvoicesPage from "./pages/InvoicesPage";
import ClientsPage from "./pages/ClientsPage";
import PaymentsPage from "./pages/PaymentsPage";
import WhatsAppPage from "./pages/WhatsAppPage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <Routes>
      {/* Public route — redirects to dashboard if already signed in */}
      <Route
        path="/"
        element={
          <>
            <SignedIn>
              <Navigate to="/dashboard" replace />
            </SignedIn>
            <SignedOut>
              <LoginPage />
            </SignedOut>
          </>
        }
      />

      {/* Protected dashboard routes with sidebar layout */}
      <Route
        path="/dashboard"
        element={
          <>
            <SignedIn>
              <DashboardLayout />
            </SignedIn>
            <SignedOut>
              <Navigate to="/" replace />
            </SignedOut>
          </>
        }
      >
        <Route index element={<OverviewPage />} />
        <Route path="invoices" element={<InvoicesPage />} />
        <Route path="clients" element={<ClientsPage />} />
        <Route path="payments" element={<PaymentsPage />} />
        <Route path="whatsapp" element={<WhatsAppPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
