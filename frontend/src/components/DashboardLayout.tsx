import { NavLink, Outlet } from "react-router-dom";
import { UserButton, useUser } from "@clerk/clerk-react";
import {
  LayoutDashboard,
  FileText,
  Users,
  CreditCard,
  Settings,
  MessageSquare,
  Scan,
  Package,
  ChevronRight,
} from "lucide-react";
import { VercelLogo } from "./ui/VercelLogo";

const NAV_ITEMS = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Overview" },
  { to: "/dashboard/invoices", icon: FileText, label: "Invoices" },
  { to: "/dashboard/clients", icon: Users, label: "Clients" },
  { to: "/dashboard/inventory", icon: Package, label: "Inventory" },
  { to: "/dashboard/payments", icon: CreditCard, label: "Payments" },
  { to: "/dashboard/scan-receipt", icon: Scan, label: "Scan Receipt" },
  { to: "/dashboard/whatsapp", icon: MessageSquare, label: "WhatsApp" },
  { to: "/dashboard/settings", icon: Settings, label: "Settings" },
];


export default function DashboardLayout() {
  const { user } = useUser();

  return (
    <div className="layout-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <VercelLogo />
            <span className="sidebar-brand-text">FinanceFlow</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/dashboard"}
              className={({ isActive }) =>
                `sidebar-link ${isActive ? "active" : ""}`
              }
            >
              <item.icon size={16} strokeWidth={1.8} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <UserButton afterSignOutUrl="/" />
            <div className="sidebar-user-info">
              <span className="sidebar-user-name">
                {user?.firstName ||
                  user?.emailAddresses[0]?.emailAddress?.split("@")[0] ||
                  "User"}
              </span>
              <span className="sidebar-user-email">
                {user?.emailAddresses[0]?.emailAddress || ""}
              </span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content area */}
      <div className="main-area">
        {/* Top bar */}
        <header className="topbar">
          <div className="topbar-breadcrumb">
            <VercelLogo />
            <ChevronRight size={14} className="topbar-separator" />
            <span className="topbar-project">FinanceFlow</span>
          </div>
          <div className="topbar-right">
            <span className="topbar-email">
              {user?.emailAddresses[0]?.emailAddress}
            </span>
          </div>
        </header>

        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
