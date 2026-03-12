import { useState, useCallback, useEffect } from "react";
import { useAuth } from "@clerk/clerk-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Clock,
  FileText,
  RefreshCw,
  Undo2,
  ArrowRight,
  AlertCircle,
  ShieldCheck,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface PreVetLineItem {
  item_id: number;
  description: string;
  quantity: number;
  unit: string;
  unit_price: number;
  amount: number;
  origin_country: string;
  ahtn_code: string;
  ahtn_description: string;
  tariff_rate: string;
  tariff_amount: number;
  similarity: number;
  requires_hitl: boolean;
  flags: string[];
}

interface PreVetResult {
  invoice_id: string;
  line_items: PreVetLineItem[];
  total_tariff: number;
  any_requires_hitl: boolean;
  all_flags: string[];
}

interface Invoice {
  invoice_id: string;
  invoice_date?: string;
  date?: string;
  vendor?: { name: string; address: string; country: string };
  seller?: { name: string; address: string; country: string };
  buyer: { name: string; address: string; country: string };
  line_items: Array<{
    item_id: number;
    description: string;
    quantity: number;
    unit: string;
    unit_price: number;
    amount: number;
    origin_country: string;
  }>;
  subtotal: number;
  currency: string;
  notes?: string;
}

interface HITLQueueItem {
  id: string | null;
  source_file: string;
  invoice: Invoice;
  pre_vet: PreVetResult;
  status: string;
}

export default function HITLReviewPage() {
  const { getToken } = useAuth();
  const [items, setItems] = useState<HITLQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [approvingId, setApprovingId] = useState<string | null>(null);

  const fetchQueue = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/invoice/hitl-queue`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Request failed: ${res.status}`);
      }
      const data = await res.json();
      const list = data.items || [];
      setItems(list);
      if (list.length > 0) {
        const firstPending = list.find((i: HITLQueueItem) => i.status === "pending_review");
        if (firstPending) {
          setExpandedId((prev) => prev || firstPending.invoice?.invoice_id || firstPending.id);
        } else {
          setExpandedId(null);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load HITL queue");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchQueue(); }, [fetchQueue]);

  const handleApprove = useCallback(
    async (recordId: string) => {
      if (!recordId) return;
      setApprovingId(recordId);
      try {
        const token = await getToken();
        const res = await fetch(`${API_BASE}/api/invoice/${recordId}/approve`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }));
          throw new Error(err.detail || "Approve failed");
        }
        setItems((prev) =>
          prev.map((i) => (i.id === recordId ? { ...i, status: "approved" } : i))
        );
        setExpandedId(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Approve failed");
      } finally {
        setApprovingId(null);
      }
    },
    [getToken]
  );

  const totalCount = items.length;
  const pendingCount = items.filter((i) => i.status === "pending_review").length;
  const approvedCount = items.filter((i) => i.status === "approved").length;

  return (
    <div className="page-container" style={{ maxWidth: "1600px", width: "100%" }}>
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-6">
        <div className="flex items-center gap-4">
          <Link to="/dashboard/invoice-prevet">
            <Button variant="ghost" size="sm" className="hover:bg-primary/5 gap-2">
              <Undo2 className="w-4 h-4" /> Back to Pre-vet
            </Button>
          </Link>
          <div className="h-5 w-px bg-border" />
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-600">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h1 className="page-title leading-tight">HITL Review Center</h1>
              <p className="page-subtitle">Human-in-the-loop invoice classification</p>
            </div>
          </div>
        </div>
        <Button
          variant="outline"
          onClick={fetchQueue}
          disabled={loading}
          className="premium-card shadow-sm active:scale-95 gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          {loading ? "Syncing..." : "Sync Queue"}
        </Button>
      </div>
      <div className="space-y-10">
        {/* ── Stats Row ───────────────────────────────────────────── */}
        {!loading && items.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
            {[
              {
                label: "Total Records",
                value: totalCount,
                icon: <FileText size={22} />,
                color: "text-indigo-600",
                iconBg: "bg-indigo-50 text-indigo-500",
                border: "border-l-indigo-500",
                bg: "bg-white"
              },
              {
                label: "Pending Review",
                value: pendingCount,
                icon: <Clock size={22} />,
                color: "text-amber-600",
                iconBg: "bg-amber-50 text-amber-500",
                border: "border-l-amber-500",
                bg: "bg-white"
              },
              {
                label: "Approved",
                value: approvedCount,
                icon: <CheckCircle2 size={22} />,
                color: "text-green-600",
                iconBg: "bg-green-50 text-green-500",
                border: "border-l-green-500",
                bg: "bg-white"
              },
            ].map(({ label, value, icon, color, iconBg, border, bg }) => (
              <div
                key={label}
                className={`${bg} rounded-2xl border border-border border-l-[6px] shadow-sm flex flex-col p-6 transition-all hover:shadow-md hover:-translate-y-1 duration-300 ${border}`}
              >
                <div className="flex justify-between items-center mb-4">
                  <p className="text-[11px] font-bold uppercase tracking-[0.15em] text-muted-foreground/70">{label}</p>
                  <div className={`p-2 rounded-xl ${iconBg}`}>{icon}</div>
                </div>
                <div>
                  <p className={`text-4xl font-extrabold tabular-nums tracking-tighter ${color}`}>{value}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── Error ───────────────────────────────────────────────── */}
        {error && (
          <Alert variant="destructive" className="bg-destructive/5 border-destructive/25">
            <AlertDescription className="flex items-center gap-2 text-sm">
              <AlertCircle size={14} /> {error}
            </AlertDescription>
          </Alert>
        )}

        {/* ── Empty State ─────────────────────────────────────────── */}
        {!loading && items.length === 0 && !error && (
          <Card className="border-dashed border-2 border-muted-foreground/20">
            <CardContent className="py-20 flex flex-col items-center text-center gap-3">
              <div className="w-16 h-16 rounded-3xl bg-muted/30 flex items-center justify-center mb-2">
                <CheckCircle2 size={32} className="text-muted-foreground/30" />
              </div>
              <p className="text-base font-semibold">Queue is Empty</p>
              <p className="text-sm text-muted-foreground max-w-xs">
                All invoices are classified with high confidence, or no invoices have been submitted for review yet.
              </p>
              <Link to="/dashboard/invoice-prevet" className="mt-2">
                <Button variant="outline" size="sm" className="gap-2">
                  Go to Pre-vet <ArrowRight size={14} />
                </Button>
              </Link>
            </CardContent>
          </Card>
        )}

        {/* ── Queue Items ─────────────────────────────────────────── */}
        {items.length > 0 && (
          <div className="flex flex-col gap-8 mt-10">
            {items.map(({ id, invoice, pre_vet, source_file, status }) => {
              const isExpanded = expandedId === invoice.invoice_id || expandedId === id;
              const hitlItems = (pre_vet?.line_items || []).filter((i) => i.requires_hitl);
              const hitlCount = hitlItems.length;
              const isApproved = status === "approved";
              const canApprove = !!id && !isApproved;

              return (
                <Collapsible
                  key={id || invoice.invoice_id}
                  open={isExpanded}
                  onOpenChange={(open) => setExpandedId(open ? (id || invoice.invoice_id) : null)}
                >
                  <Card
                    className={`premium-card transition-all duration-200 ${
                      isApproved
                        ? "opacity-70 border-green-200 bg-green-50/10"
                        : isExpanded
                        ? "border-primary/50 shadow-xl ring-4 ring-primary/5"
                        : "border-border shadow-sm hover:border-muted-foreground/30 hover:shadow-md"
                    }`}
                  >
                    {/* ── Collapsible Trigger / Card Header ─────── */}
                    <CollapsibleTrigger asChild>
                      <CardHeader className="cursor-pointer py-6 px-8 select-none">
                        <div className="flex items-center justify-between w-full gap-4">
                          {/* Left: Icon + Info */}
                          <div className="flex items-center gap-4 min-w-0">
                            <div
                              className={`shrink-0 w-11 h-11 rounded-xl flex items-center justify-center ${
                                isApproved ? "bg-green-100 text-green-600" : "bg-primary/8 text-primary"
                              }`}
                            >
                              <FileText size={20} />
                            </div>
                            <div className="min-w-0">
                              <div className="flex items-center gap-2.5 flex-wrap">
                                <span className="text-sm font-bold tracking-tight">#{invoice.invoice_id}</span>
                                {isApproved ? (
                                  <Badge className="bg-green-100 text-green-700 border-green-200 text-[10px] px-2 py-0.5 gap-1">
                                    <CheckCircle2 size={10} /> Approved
                                  </Badge>
                                ) : (
                                  <Badge className="bg-amber-100 text-amber-700 border-amber-200 text-[10px] px-2 py-0.5 gap-1">
                                    <Clock size={10} /> {hitlCount} Flagged
                                  </Badge>
                                )}
                              </div>
                              <div className="flex items-center gap-1.5 mt-1 text-xs text-muted-foreground">
                                <span className="truncate max-w-[120px]">{(invoice.vendor || invoice.seller)?.name || "Unknown"}</span>
                                <ArrowRight size={9} className="shrink-0 opacity-40" />
                                <span className="truncate max-w-[120px] font-semibold text-foreground/70">{(invoice.buyer || {}).name || "Unknown"}</span>
                                <span className="opacity-30 mx-0.5">•</span>
                                <span className="font-bold text-foreground/60 tabular-nums">{invoice.currency || "MYR"} {(invoice.subtotal || 0).toLocaleString()}</span>
                              </div>
                            </div>
                          </div>

                          {/* Right: Date + Chevron */}
                          <div className="flex items-center gap-4 shrink-0 border-l pl-4 text-muted-foreground">
                            <div className="hidden sm:flex flex-col items-end">
                              <span className="text-[9px] uppercase font-bold tracking-widest opacity-40">Date</span>
                              <span className="text-xs font-semibold">{invoice.invoice_date || invoice.date}</span>
                            </div>
                            {isExpanded
                              ? <ChevronDown size={18} className="text-primary" />
                              : <ChevronRight size={18} />
                            }
                          </div>
                        </div>
                      </CardHeader>
                    </CollapsibleTrigger>

                    {/* ── Expanded Content ───────────────────────── */}
                    <CollapsibleContent>
                      <CardContent className="border-t border-border/70 p-8 lg:p-10 space-y-12 bg-slate-50/30">
                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 xl:gap-16">

                          {/* Sidebar: Details + Approve */}
                          <div className="lg:col-span-4 space-y-6">
                            {/* Details panel */}
                            <div className="rounded-2xl bg-white border p-8 space-y-8 shadow-sm">
                              <div>
                                <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground flex items-center gap-2 mb-6 px-1">
                                  <FileText size={12} className="text-primary/60" /> Invoice Metadata
                                </h4>
                              </div>
                              <div className="space-y-6">
                                <div className="space-y-2 px-1">
                                  <p className="text-[10px] uppercase font-bold text-muted-foreground/60 tracking-widest">Filename</p>
                                  <p className="font-semibold text-xs leading-relaxed break-all text-foreground/80 flex items-center gap-2" title={source_file}>
                                    <FileText size={12} className="shrink-0 opacity-40" />
                                    {source_file?.split(/[\/\\]/).pop()}
                                  </p>
                                </div>
                                <div className="space-y-3 pt-6 border-t border-border/50 px-1">
                                  <p className="text-[10px] uppercase font-bold text-muted-foreground/60 tracking-widest">Base Currency</p>
                                  <div className="flex items-center gap-3">
                                    <Badge variant="outline" className="text-xs px-3 py-1 font-bold bg-primary/5 border-primary/20 text-primary">{invoice.currency || "MYR"}</Badge>
                                  </div>
                                </div>
                                <div className="space-y-4 pt-6 border-t border-border/50 bg-slate-50/50 -mx-8 px-9 py-6 rounded-b-2xl mt-4">
                                  <div className="flex justify-between items-center text-sm">
                                    <span className="text-xs font-medium text-muted-foreground">Estimated Duty</span>
                                    <span className="font-bold text-primary tabular-nums">{invoice.currency || "MYR"} {(pre_vet?.total_tariff || 0).toFixed(2)}</span>
                                  </div>
                                  <div className="flex justify-between items-center text-sm">
                                    <span className="text-xs font-medium text-muted-foreground">Invoice Value</span>
                                    <span className="font-bold tabular-nums">{invoice.currency || "MYR"} {(invoice.subtotal || 0).toLocaleString()}</span>
                                  </div>
                                </div>
                              </div>
                            </div>

                            {/* Approve Button */}
                            {canApprove && (
                              <div className="mt-2">
                                <Button
                                  onClick={() => id && handleApprove(id)}
                                  disabled={approvingId === id}
                                  className="w-full h-14 bg-green-600 hover:bg-green-700 text-white font-bold shadow-lg shadow-green-500/20 gap-2 text-base rounded-2xl"
                                >
                                  {approvingId === id ? (
                                    <><RefreshCw size={16} className="animate-spin" /> Processing...</>
                                  ) : (
                                    <><CheckCircle2 size={16} /> Final Approval</>
                                  )}
                                </Button>
                              </div>
                            )}

                            {isApproved && (
                              <div className="flex items-center gap-2 p-3 rounded-xl bg-green-50 border border-green-200 text-green-700 text-xs font-semibold">
                                <CheckCircle2 size={14} /> Invoice approved
                              </div>
                            )}

                            {/* Flags */}
                            {pre_vet?.all_flags?.length > 0 && (
                              <div className="mt-4 rounded-2xl bg-amber-50/60 border border-amber-200 p-7 space-y-4">
                                <p className="text-xs font-bold uppercase tracking-widest text-amber-800 flex items-center gap-2">
                                  <AlertCircle size={12} /> Active Flags
                                </p>
                                <ul className="space-y-3">
                                  {(pre_vet?.all_flags || []).map((f, i) => (
                                    <li key={i} className="flex gap-2.5 text-xs text-amber-800 font-medium leading-relaxed">
                                      <span className="text-amber-400 shrink-0 mt-0.5">•</span>{f}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>

                          {/* Main: Classification Table */}
                          <div className="lg:col-span-8 space-y-5">
                            <div className="flex items-center justify-between">
                              <h4 className="font-bold flex items-center gap-3">
                                Classification Checklist
                                <Badge variant="secondary" className="bg-muted text-[10px] font-bold px-2.5 py-1">
                                  {(pre_vet?.line_items || []).length} ITEMS
                                </Badge>
                                {hitlCount > 0 && (
                                  <Badge className="bg-amber-100 text-amber-700 border-amber-200 text-[10px] font-bold px-2.5 py-1">
                                    {hitlCount} NEED REVIEW
                                  </Badge>
                                )}
                              </h4>
                            </div>

                            <div className="rounded-2xl border border-border/60 overflow-hidden shadow-md bg-white">
                              <div className="overflow-x-auto">
                                <Table className="w-full min-w-[800px]">
                                  <TableHeader className="bg-slate-50/80">
                                    <TableRow className="hover:bg-transparent border-b border-border/50">
                                      <TableHead className="w-[60px] pl-6 py-5 text-[10px] uppercase font-bold tracking-widest text-muted-foreground/60">Pos</TableHead>
                                      <TableHead className="min-w-[280px] px-4 py-5 text-[10px] uppercase font-bold tracking-widest text-muted-foreground/60">Line Item Description</TableHead>
                                      <TableHead className="w-[100px] px-4 py-5 text-[10px] uppercase font-bold tracking-widest text-muted-foreground/60">Qty / Unit</TableHead>
                                      <TableHead className="w-[240px] px-4 py-5 text-[10px] uppercase font-bold tracking-widest text-muted-foreground/60">HS Code Classification</TableHead>
                                      <TableHead className="w-[80px] text-right px-4 py-5 text-[10px] uppercase font-bold tracking-widest text-muted-foreground/60">Rate</TableHead>
                                      <TableHead className="w-[100px] text-right px-6 py-5 text-[10px] uppercase font-bold tracking-widest text-muted-foreground/60">Duty ({invoice.currency || "MYR"})</TableHead>
                                      <TableHead className="w-[80px] text-center px-4 py-5 text-[10px] uppercase font-bold tracking-widest text-muted-foreground/60">Status</TableHead>
                                    </TableRow>
                                  </TableHeader>
                                  <TableBody>
                                    {(pre_vet?.line_items || []).map((item) => (
                                      <TableRow
                                        key={item.item_id}
                                        className={`group transition-colors border-b border-border/30 last:border-0 ${
                                          item.requires_hitl ? "bg-amber-50/30 hover:bg-amber-50/50" : "hover:bg-muted/5"
                                        }`}
                                      >
                                        <TableCell className="pl-6 pr-2 font-mono text-[10px] text-muted-foreground/40 font-medium align-middle">{item.item_id}</TableCell>
                                        <TableCell className="px-4 py-5">
                                          <div className="space-y-1.5">
                                            <span className="font-semibold text-sm text-foreground/90 block leading-snug">{item.description}</span>
                                            {item.flags.length > 0 && (
                                              <div className="flex flex-wrap gap-1.5 pt-0.5">
                                                {item.flags.map((f, i) => (
                                                  <span key={i} className="text-[9px] px-1.5 py-0.5 bg-amber-50 border border-amber-200/50 text-amber-700 rounded-md font-bold uppercase tracking-tight">
                                                    {f}
                                                  </span>
                                                ))}
                                              </div>
                                            )}
                                          </div>
                                        </TableCell>
                                        <TableCell className="px-4 py-5 text-xs font-medium tabular-nums text-muted-foreground/80 align-middle">
                                          <div className="flex flex-col">
                                            <span>{item.quantity}</span>
                                            <span className="text-[9px] opacity-60 uppercase font-bold">{item.unit}</span>
                                          </div>
                                        </TableCell>
                                        <TableCell className="px-4 py-5 align-middle">
                                          <div className="space-y-1.5">
                                            <div className="flex items-center gap-2">
                                              <span className="text-[10px] font-bold bg-primary text-primary-foreground px-1.5 py-0.5 rounded shadow-sm">HS</span>
                                              <code className="text-xs font-bold text-primary tracking-tight">{item.ahtn_code}</code>
                                            </div>
                                            <p className="text-[10px] text-muted-foreground leading-relaxed line-clamp-2 max-w-[220px]" title={item.ahtn_description}>{item.ahtn_description}</p>
                                          </div>
                                        </TableCell>
                                        <TableCell className="text-right px-4 py-5 text-xs font-semibold tabular-nums align-middle text-muted-foreground">{item.tariff_rate}</TableCell>
                                        <TableCell className="text-right px-6 py-5 font-bold tabular-nums text-sm align-middle text-foreground">
                                          {item.tariff_amount.toFixed(2)}
                                        </TableCell>
                                        <TableCell className="text-center px-4 py-5 align-middle">
                                          {item.requires_hitl ? (
                                            <Badge className="bg-amber-500 hover:bg-amber-600 text-white border-0 text-[10px] font-black h-5 px-2 rounded-full cursor-help shadow-sm" title="Human Review Needed">REVIEW</Badge>
                                          ) : (
                                            <div className="bg-green-500/10 text-green-600 rounded-full h-5 w-5 flex items-center justify-center mx-auto border border-green-500/20 shadow-inner">
                                              <CheckCircle2 size={12} strokeWidth={3} />
                                            </div>
                                          )}
                                        </TableCell>
                                      </TableRow>
                                    ))}
                                  </TableBody>
                                </Table>
                              </div>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </CollapsibleContent>
                  </Card>
                </Collapsible>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
