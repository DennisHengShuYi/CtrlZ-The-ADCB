import { useUser } from "@clerk/clerk-react";
import { useEffect, useState } from "react";
import { useApiFetch } from "../hooks/useApiFetch";
import {
    FileText,
    Users,
    CreditCard,
    ArrowUpRight,
    ArrowDownRight,
    AlertCircle,
    Scan,
    Wallet,
    Landmark,
    PiggyBank,
} from "lucide-react";
import { Link } from "react-router-dom";

interface StatCardProps {
    icon: React.ElementType;
    label: string;
    value: string;
    change?: string;
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
                {change && (
                    <span className={`stat-trend ${positive ? "positive" : "negative"}`}>
                        {positive ? (
                            <ArrowUpRight size={14} />
                        ) : (
                            <ArrowDownRight size={14} />
                        )}
                        {change}
                    </span>
                )}
            </div>
            <div className="stat-card-body">
                <span className="stat-value">{value}</span>
                <span className="stat-label">{label}</span>
            </div>
        </div>
    );
}

function AlertCard({
    title,
    items,
    isSupplier = false,
    baseCurrency = "MYR",
}: {
    title: string;
    items: any[];
    isSupplier?: boolean;
    baseCurrency?: string;
}) {
    if (items.length === 0) {
        return (
            <div className="p-4 custom-bg custom-border rounded-lg text-sm text-gray-500">
                No pending items for {title.toLowerCase()}.
            </div>
        );
    }

    const total = items.reduce(
        (sum, item) => sum + parseFloat(item.total_amount || 0),
        0,
    );

    return (
        <div className="p-4 bg-white border border-[oklch(0.92_0_0)] rounded-lg shadow-sm">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <AlertCircle
                        className={`w-5 h-5 ${isSupplier ? "text-amber-500" : "text-red-500"}`}
                    />
                    <h3 className="font-medium text-gray-900">{title}</h3>
                </div>
                <span className="font-semibold text-gray-900">
                    {new Intl.NumberFormat("en-US", { style: "currency", currency: baseCurrency || "MYR" }).format(total)}
                </span>
            </div>
            <div className="space-y-3">
                {items.slice(0, 3).map((inv: any) => (
                    <div
                        key={inv.id}
                        className="flex items-center justify-between text-sm"
                    >
                        <span className="text-gray-600 truncate mr-2">
                            {inv.clients?.name || "Unknown"} - {inv.invoice_number}
                        </span>
                        <div className="flex flex-col items-end">
                            <span className="font-medium">
                                {new Intl.NumberFormat("en-US", { style: "currency", currency: inv.currency || "MYR" }).format(parseFloat(inv.total_amount))}
                            </span>
                            {(inv.currency && inv.currency !== baseCurrency) && (
                                <span className="text-[10px] text-gray-400">
                                    {new Intl.NumberFormat("en-US", { style: "currency", currency: baseCurrency || "MYR" }).format(parseFloat(inv.total_amount) * parseFloat(inv.exchange_rate || 1))}
                                </span>
                            )}
                        </div>
                    </div>
                ))}
                {items.length > 3 && (
                    <div className="text-sm text-gray-500 pt-2 border-t">
                        + {items.length - 3} more
                    </div>
                )}
            </div>
        </div>
    );
}

function QuickActions() {
    const actions = [
        { label: "New Invoice", icon: FileText, href: "/dashboard/invoices" },
        { label: "Add Client", icon: Users, href: "/dashboard/clients" },
        { label: "Record Payment", icon: CreditCard, href: "/dashboard/payments" },
        { label: "Scan Receipt", icon: Scan, href: "/dashboard/scan-receipt" },
    ];

    return (
        <div className="quick-actions-card">
            <h3>Quick Actions</h3>
            <div className="quick-actions-grid gap-3 grid grid-cols-2 mt-4">
                {actions.map((a) => (
                    <Link
                        key={a.label}
                        to={a.href}
                        className="flex items-center gap-2 p-3 text-sm font-medium hover:bg-gray-50 text-gray-700 bg-white border border-[oklch(0.92_0_0)] rounded-lg transition-colors"
                    >
                        <a.icon size={16} className="text-black" />
                        {a.label}
                    </Link>
                ))}
            </div>
        </div>
    );
}

export default function OverviewPage() {
    const { user } = useUser();
    const apiFetch = useApiFetch();

    const [summary, setSummary] = useState({
        cash_on_hand: 0,
        total_assets: 0,
        available_for_expenses: 0,
        base_currency: "MYR",
        client_pending: [],
        supplier_pending: [],
    });

    const [loading, setLoading] = useState(true);

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
                const res = await apiFetch("/api/companies/financial-summary");
                if (res && typeof res.cash_on_hand !== "undefined") {
                    setSummary(res);
                }
            } catch (err) {
                console.error("Failed to load financial summary", err);
            } finally {
                setLoading(false);
            }
        }
        load();
    }, [apiFetch]);

    if (loading) {
        return <div className="p-8">Loading dashboard...</div>;
    }

    // Calculate percentages for the simple bar chart
    // (just a mock visual calculation for the demo based on available money vs pending)
    const totalReceivable = summary.client_pending.reduce(
        (sum, item: any) => sum + parseFloat(item.total_amount || 0),
        0,
    );
    const totalPayable = summary.supplier_pending.reduce(
        (sum, item: any) => sum + parseFloat(item.total_amount || 0),
        0,
    );

    const totalVolume = summary.cash_on_hand + totalReceivable + totalPayable;
    const cashPercent =
        totalVolume === 0 ? 0 : (summary.cash_on_hand / totalVolume) * 100;
    const receivablePercent =
        totalVolume === 0 ? 0 : (totalReceivable / totalVolume) * 100;
    const payablePercent =
        totalVolume === 0 ? 0 : (totalPayable / totalVolume) * 100;

    return (
        <div className="page-container animate-in fade-in duration-500">
            <div className="page-header">
                <div>
                    <h1 className="page-title">
                        {greeting}, {displayName} 👋
                    </h1>
                    <p className="page-subtitle">
                        Here's what's happening with your finances today.
                    </p>
                </div>
            </div>

            <div className="overview-stats-grid grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <StatCard
                    icon={Wallet}
                    label="Cash on Hand"
                    value={new Intl.NumberFormat("en-US", { style: "currency", currency: summary.base_currency }).format(summary.cash_on_hand)}
                    positive
                    delay={0}
                />
                <StatCard
                    icon={PiggyBank}
                    label="Available for Expenses"
                    value={new Intl.NumberFormat("en-US", { style: "currency", currency: summary.base_currency }).format(summary.available_for_expenses)}
                    positive={summary.available_for_expenses >= 0}
                    delay={80}
                />
                <StatCard
                    icon={Landmark}
                    label="Total Assets"
                    value={new Intl.NumberFormat("en-US", { style: "currency", currency: summary.base_currency }).format(summary.total_assets)}
                    positive
                    delay={160}
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                <div className="lg:col-span-2 space-y-6">
                    <div className="card">
                        <h3 className="card-header pb-4 font-semibold text-lg border-b mb-4">
                            Financial Flow
                        </h3>
                        <div className="space-y-4">
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-500 flex items-center gap-2">
                                    <div className="w-3 h-3 bg-black rounded-full"></div> Cash on
                                    Hand
                                </span>
                                <span className="font-medium">
                                    {new Intl.NumberFormat("en-US", { style: "currency", currency: summary.base_currency }).format(summary.cash_on_hand)}
                                </span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-500 flex items-center gap-2">
                                    <div className="w-3 h-3 bg-gray-300 rounded-full"></div>{" "}
                                    Expected Revenue
                                </span>
                                <span className="font-medium">
                                    {new Intl.NumberFormat("en-US", { style: "currency", currency: summary.base_currency }).format(totalReceivable)}
                                </span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-500 flex items-center gap-2">
                                    <div className="w-3 h-3 bg-red-400 rounded-full"></div>{" "}
                                    Upcoming Bills
                                </span>
                                <span className="font-medium">
                                    {new Intl.NumberFormat("en-US", { style: "currency", currency: summary.base_currency }).format(totalPayable)}
                                </span>
                            </div>

                            {/* Simple Bar Chart */}
                            <div className="h-4 w-full flex rounded-full overflow-hidden mt-6 bg-gray-100">
                                {cashPercent > 0 && (
                                    <div
                                        style={{ width: `${cashPercent}%` }}
                                        className="bg-black"
                                        title="Cash"
                                    ></div>
                                )}
                                {receivablePercent > 0 && (
                                    <div
                                        style={{ width: `${receivablePercent}%` }}
                                        className="bg-gray-300"
                                        title="Receivables"
                                    ></div>
                                )}
                                {payablePercent > 0 && (
                                    <div
                                        style={{ width: `${payablePercent}%` }}
                                        className="bg-red-400"
                                        title="Payables"
                                    ></div>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <AlertCard
                            title="Expected Revenue"
                            items={summary.client_pending}
                            baseCurrency={summary.base_currency}
                        />
                        <AlertCard
                            title="Upcoming Bills"
                            items={summary.supplier_pending}
                            isSupplier={true}
                            baseCurrency={summary.base_currency}
                        />
                    </div>
                </div>

                <div className="space-y-6">
                    <QuickActions />
                </div>
            </div>
        </div>
    );
}
