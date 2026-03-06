// frontend/src/pages/OverviewPage.tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import FinanceOverview from "./overviews/FinanceOverview";
import SocialMediaOverview from "./overviews/SocialMediaOverview";
import InventoryOverview from "./overviews/InventoryOverview";

export default function OverviewPage() {
    return (
        <div className="page-container animate-in fade-in duration-500">
            <Tabs defaultValue="finance" className="w-full">
                <div className="flex justify-center sm:justify-start w-full mb-8">
                    <TabsList className="h-10 gap-4 inline-flex w-full sm:w-auto items-center justify-start sm:justify-center p-3 bg-muted/50 rounded-lg overflow-x-auto border border-border shadow-sm scrollbar-hide">
                        <TabsTrigger value="finance" className="h-full px-4 sm:px-6 text-sm font-medium transition-all rounded-md data-[state=active]:bg-foreground data-[state=active]:text-background data-[state=active]:shadow-sm">
                            Finance
                        </TabsTrigger>
                        <TabsTrigger value="social" className="h-full px-4 sm:px-6 text-sm font-medium transition-all rounded-md data-[state=active]:bg-foreground data-[state=active]:text-background data-[state=active]:shadow-sm">
                            Social Media
                        </TabsTrigger>
                        <TabsTrigger value="inventory" className="h-full px-4 sm:px-6 text-sm font-medium transition-all rounded-md data-[state=active]:bg-foreground data-[state=active]:text-background data-[state=active]:shadow-sm">
                            Inventory
                        </TabsTrigger>
                    </TabsList>
                </div>
                <TabsContent value="finance">
                    <FinanceOverview />
                </TabsContent>
                <TabsContent value="social">
                    <SocialMediaOverview />
                </TabsContent>
                <TabsContent value="inventory">
                    <InventoryOverview />
                </TabsContent>
            </Tabs>
        </div>
    );
}