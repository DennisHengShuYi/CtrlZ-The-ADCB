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
import ReceiptScanPage from "./pages/ReceiptScanPage";
import InventoryPage from "./pages/InventoryPage";

const isMockMode = localStorage.getItem("Mock-Mode") === "true";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (isMockMode) return <>{children}</>;
  return (
    <>
      <SignedIn>{children}</SignedIn>
      <SignedOut>
        <Navigate to="/" replace />
      </SignedOut>
    </>
  );
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  if (isMockMode) return <Navigate to="/dashboard" replace />;
  return (
    <>
      <SignedIn>
        <Navigate to="/dashboard" replace />
      </SignedIn>
      <SignedOut>{children}</SignedOut>
    </>
  );
}

export default function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
      />

      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<OverviewPage />} />
        <Route path="invoices" element={<InvoicesPage />} />
        <Route path="clients" element={<ClientsPage />} />
        <Route path="inventory" element={<InventoryPage />} />
        <Route path="payments" element={<PaymentsPage />} />
        <Route path="scan-receipt" element={<ReceiptScanPage />} />
        <Route path="whatsapp" element={<WhatsAppPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
