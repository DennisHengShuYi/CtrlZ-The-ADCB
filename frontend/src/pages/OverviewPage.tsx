import { useUser } from "@clerk/clerk-react";
import { useEffect, useState } from "react";
import { useApiFetch } from "../hooks/useApiFetch";
import {
  FileText,
  Users,
  CreditCard,
  TrendingUp,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
} from "lucide-react";

interface StatCardProps {
  icon: React.ElementType;
  label: string;
  value: string;
  change: string;
  positive?: boolean;
  delay?: number;
}

function StatCard({
  icon: Icon,
  label,
  value,
  change,
  positive = true,
  delay = 0,
}: StatCardProps) {
  return (
    <div
      className="overview-stat-card"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="stat-card-header">
        <span className="stat-icon-wrapper">
          <Icon size={18} strokeWidth={1.5} />
        </span>
        <span className={`stat-trend ${positive ? "positive" : "negative"}`}>
          {positive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
          {change}
        </span>
      </div>
      <div className="stat-card-body">
        <span className="stat-value">{value}</span>
        <span className="stat-label">{label}</span>
      </div>
    </div>
  );
}

function RecentActivity() {
  const activities = [
    {
      id: 1,
      type: "invoice",
      text: "Invoice INV-4A8C2D1E created for ABC Corp",
      time: "2 minutes ago",
    },
    {
      id: 2,
      type: "payment",
      text: "Payment of $2,500 received from XYZ Ltd",
      time: "1 hour ago",
    },
    {
      id: 3,
      type: "client",
      text: "New client 'Acme Industries' added",
      time: "3 hours ago",
    },
    {
      id: 4,
      type: "invoice",
      text: "Invoice INV-9F3B7A2C marked as paid",
      time: "5 hours ago",
    },
    {
      id: 5,
      type: "payment",
      text: "Payment of $800 received from Beta Co.",
      time: "Yesterday",
    },
  ];

  const getIcon = (type: string) => {
    switch (type) {
      case "invoice":
        return <FileText size={14} />;
      case "payment":
        return <CreditCard size={14} />;
      case "client":
        return <Users size={14} />;
      default:
        return <Clock size={14} />;
    }
  };

  return (
    <div className="activity-card">
      <div className="activity-header">
        <h3>Recent Activity</h3>
        <span className="activity-badge">Live</span>
      </div>
      <div className="activity-list">
        {activities.map((a, i) => (
          <div
            key={a.id}
            className="activity-item"
            style={{ animationDelay: `${(i + 4) * 80}ms` }}
          >
            <span className="activity-icon">{getIcon(a.type)}</span>
            <div className="activity-info">
              <p className="activity-text">{a.text}</p>
              <span className="activity-time">{a.time}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function QuickActions() {
  const actions = [
    { label: "New Invoice", icon: FileText, href: "/dashboard/invoices" },
    { label: "Add Client", icon: Users, href: "/dashboard/clients" },
    { label: "Record Payment", icon: CreditCard, href: "/dashboard/payments" },
    { label: "WhatsApp Bot", icon: TrendingUp, href: "/dashboard/whatsapp" },
  ];

  return (
    <div className="quick-actions-card">
      <h3>Quick Actions</h3>
      <div className="quick-actions-grid">
        {actions.map((a) => (
          <a key={a.label} href={a.href} className="quick-action-item">
            <a.icon size={20} strokeWidth={1.5} />
            <span>{a.label}</span>
          </a>
        ))}
      </div>
    </div>
  );
}

export default function OverviewPage() {
  const { user } = useUser();
  const apiFetch = useApiFetch();
  const [stats, setStats] = useState({
    invoices: 0,
    clients: 0,
    payments: 0,
    outstanding: "$0",
  });

  const displayName =
    user?.firstName ??
    user?.emailAddresses[0]?.emailAddress?.split("@")[0] ??
    "there";

  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  useEffect(() => {
    async function load() {
      try {
        const [invRes, clientRes, payRes] = await Promise.all([
          apiFetch("/api/invoices/").catch(() => ({ invoices: [] })),
          apiFetch("/api/clients/").catch(() => ({ clients: [] })),
          apiFetch("/api/payments/").catch(() => ({ payments: [] })),
        ]);

        const invoices = invRes?.invoices || [];
        const unpaidTotal = invoices
          .filter((i: any) => i.status === "unpaid")
          .reduce(
            (sum: number, i: any) => sum + parseFloat(i.total_amount || 0),
            0,
          );

        setStats({
          invoices: invoices.length,
          clients: (clientRes?.clients || []).length,
          payments: (payRes?.payments || []).length,
          outstanding: `$${unpaidTotal.toLocaleString("en-US", { minimumFractionDigits: 2 })}`,
        });
      } catch {
        // Keep defaults
      }
    }
    load();
  }, [apiFetch]);

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">
            {greeting}, {displayName} 👋
          </h1>
          <p className="page-subtitle">
            Here's what's happening with your invoices today.
          </p>
        </div>
      </div>

      <div className="overview-stats-grid">
        <StatCard
          icon={FileText}
          label="Total Invoices"
          value={String(stats.invoices)}
          change="12%"
          positive
          delay={0}
        />
        <StatCard
          icon={Users}
          label="Active Clients"
          value={String(stats.clients)}
          change="4.6%"
          positive
          delay={80}
        />
        <StatCard
          icon={CreditCard}
          label="Payments Received"
          value={String(stats.payments)}
          change="8%"
          positive
          delay={160}
        />
        <StatCard
          icon={TrendingUp}
          label="Outstanding"
          value={stats.outstanding}
          change="2.1%"
          positive={false}
          delay={240}
        />
      </div>

      <div className="overview-bottom-grid">
        <RecentActivity />
        <QuickActions />
      </div>
    </div>
  );
}
