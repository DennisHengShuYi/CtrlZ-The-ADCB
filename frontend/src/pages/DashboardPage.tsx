import { UserButton, useUser } from "@clerk/clerk-react";

// Vercel triangle logo (small)
function VercelLogo() {
    return (
        <svg
            width="20"
            height="18"
            viewBox="0 0 74 64"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
        >
            <path d="M37.0001 0L74.0001 64H0L37.0001 0Z" fill="black" />
        </svg>
    );
}

// Stat card component
function StatCard({
    label,
    value,
    change,
    positive = true,
}: {
    label: string;
    value: string;
    change: string;
    positive?: boolean;
}) {
    return (
        <div className="stat-card">
            <span className="stat-label">{label}</span>
            <span className="stat-value">{value}</span>
            <span className={`stat-change ${positive ? "positive" : ""}`}>
                {change}
            </span>
        </div>
    );
}

export default function DashboardPage() {
    const { user } = useUser();

    const displayName =
        user?.firstName ??
        user?.emailAddresses[0]?.emailAddress ??
        "there";

    return (
        <div className="dashboard-page">
            {/* Top Navigation */}
            <header className="dashboard-header">
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                    <VercelLogo />
                    <span
                        style={{
                            color: "oklch(0.8 0 0)",
                            fontSize: "1.1rem",
                            fontWeight: 300,
                        }}
                    >
                        /
                    </span>
                    <h1>Dashboard</h1>
                </div>

                <div className="header-actions">
                    <span className="user-greeting">
                        {user?.emailAddresses[0]?.emailAddress}
                    </span>
                    <UserButton afterSignOutUrl="/" />
                </div>
            </header>

            {/* Main Content */}
            <main className="dashboard-main">
                {/* Page heading */}
                <div>
                    <h2 className="dashboard-section-title">
                        Good morning, {displayName} 👋
                    </h2>
                    <p className="dashboard-section-subtitle">
                        Here's what's happening with your project today.
                    </p>
                </div>

                {/* Stats Grid */}
                <div className="dashboard-content">
                    <StatCard
                        label="Total Deployments"
                        value="1,284"
                        change="+12% from last month"
                        positive
                    />
                    <StatCard
                        label="Active Users"
                        value="8,492"
                        change="+4.6% from last week"
                        positive
                    />
                    <StatCard
                        label="Bandwidth Used"
                        value="94.2 GB"
                        change="↑ 18 GB since yesterday"
                        positive={false}
                    />
                    <StatCard
                        label="Uptime"
                        value="99.99%"
                        change="All systems operational"
                        positive
                    />
                </div>
            </main>
        </div>
    );
}
