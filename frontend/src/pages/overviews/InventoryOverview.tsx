import { useUser } from "@clerk/clerk-react";

export default function InventoryOverview() {
    const { user } = useUser();

    const displayName =
        user?.firstName ??
        user?.emailAddresses[0]?.emailAddress?.split("@")[0] ??
        "there";

    const hour = new Date().getHours();
    const greeting =
        hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

    return (
        <div className="page-container flex flex-col gap-5"> {/* Consistent padding layout */}
            <div className="page-header">
                <div>
                    <h1 className="page-title">
                        {greeting}, {displayName} 👋
                    </h1>
                    <p className="page-subtitle">
                        Here's what's happening with your inventory today.
                    </p>
                </div>
            </div>

            <div className="p-4 bg-white rounded-lg shadow-sm border border-border mt-4">
                <h2 className="text-xl font-semibold mb-4 text-foreground">Inventory Features</h2>
                <p className="text-muted-foreground">Inventory metrics and data will be displayed here soon.</p>
            </div>
        </div>
    );
}
