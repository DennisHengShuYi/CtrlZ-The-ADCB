import { Routes, Route, Navigate } from "react-router-dom";
import { SignedIn, SignedOut } from "@clerk/clerk-react";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import InvoicePrevetPage from "./pages/InvoicePrevetPage";

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

      {/* Protected dashboard route */}
      <Route
        path="/dashboard"
        element={
          <>
            <SignedIn>
              <DashboardPage />
            </SignedIn>
            <SignedOut>
              <Navigate to="/" replace />
            </SignedOut>
          </>
        }
      />

      {/* Invoice Pre-vet (Liability Shield) */}
      <Route
        path="/invoice-prevet"
        element={
          <>
            <SignedIn>
              <InvoicePrevetPage />
            </SignedIn>
            <SignedOut>
              <Navigate to="/" replace />
            </SignedOut>
          </>
        }
      />
    </Routes>
  );
}
