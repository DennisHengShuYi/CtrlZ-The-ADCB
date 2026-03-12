import { useState, useCallback, useEffect } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
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
import { Upload, Database, FileJson, ArrowRight, RotateCcw, ShieldCheck, AlertTriangle, Sparkles, CheckCircle2 } from "lucide-react";

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
  currency: string;
  any_requires_hitl: boolean;
  all_flags: string[];
}

interface SavedInvoiceOption {
  id: string;
  source_file: string;
  invoice: unknown;
  created_at?: string;
}

export default function InvoicePrevetPage() {
  const [file, setFile] = useState<File | null>(null);
  const [sourceType, setSourceType] = useState<"upload" | "supabase">("upload");
  const [savedInvoices, setSavedInvoices] = useState<SavedInvoiceOption[]>([]);
  const [selectedSavedInvoiceId, setSelectedSavedInvoiceId] = useState<string>("");
  const [loadingSavedInvoices, setLoadingSavedInvoices] = useState(false);
  const [result, setResult] = useState<PreVetResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      if (!f.name.endsWith(".json")) {
        setError("Please upload a JSON file");
        setFile(null);
        return;
      }
      setFile(f);
      setSelectedSavedInvoiceId("");
      setResult(null);
      setError(null);
    }
  }, []);

  const fetchSavedInvoices = useCallback(async () => {
    setLoadingSavedInvoices(true);
    try {
      const res = await fetch(`${API_BASE}/api/invoice/hitl-queue`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Failed to load saved invoices");
      }
      const data = await res.json();
      const options = (data.items || []).map((item: {
        id?: string;
        source_file?: string;
        invoice?: unknown;
        created_at?: string;
      }) => ({
        id: item.id || `${item.source_file || "invoice"}-${Math.random()}`,
        source_file: item.source_file || "Supabase invoice JSON",
        invoice: item.invoice || {},
        created_at: item.created_at,
      }));
      setSavedInvoices(options);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load saved invoices");
    } finally {
      setLoadingSavedInvoices(false);
    }
  }, []);

  useEffect(() => {
    if (sourceType === "supabase" && savedInvoices.length === 0 && !loadingSavedInvoices) {
      fetchSavedInvoices();
    }
  }, [fetchSavedInvoices, loadingSavedInvoices, savedInvoices.length, sourceType]);

  const handleSubmit = useCallback(async () => {
    if (sourceType === "upload" && !file) {
      setError("Please select a JSON file first");
      return;
    }
    if (sourceType === "supabase" && !selectedSavedInvoiceId) {
      setError("Please choose a saved JSON from Supabase first");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    try {
      let invoice: unknown;
      let sourceFile = "";
      if (sourceType === "upload") {
        const text = await file!.text();
        invoice = JSON.parse(text);
        sourceFile = file?.name || "";
      } else {
        const selected = savedInvoices.find((s) => s.id === selectedSavedInvoiceId);
        if (!selected) throw new Error("Selected saved JSON was not found");
        invoice = selected.invoice;
        sourceFile = selected.source_file;
      }

      const url = new URL(`${API_BASE}/api/invoice/pre-vet`);
      if (sourceFile) url.searchParams.set("source_file", sourceFile);
      const res = await fetch(url.toString(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(invoice),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        const detail = err.detail;
        let message: string;
        if (Array.isArray(detail) && detail.length > 0) {
          message = detail
            .map((d: { loc?: unknown[]; msg?: string }) => {
              const loc = Array.isArray(d.loc) ? d.loc.filter((x) => x !== "body").join(".") : "";
              return loc ? `${loc}: ${d.msg ?? "validation error"}` : (d.msg ?? "validation error");
            })
            .join("; ");
        } else {
          message = typeof detail === "string" ? detail : `Request failed: ${res.status}`;
        }
        throw new Error(message);
      }
      const data: PreVetResult = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }, [file, savedInvoices, selectedSavedInvoiceId, sourceType]);

  const handleReset = useCallback(() => {
    setFile(null);
    setSelectedSavedInvoiceId("");
    setResult(null);
    setError(null);
  }, []);

  return (
    <div className="page-container" style={{ maxWidth: "1400px", width: "100%" }}>
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="page-header items-center mb-8">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-primary/10 text-primary">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h1 className="page-title">Invoice Pre-vet</h1>
            <p className="page-subtitle">AHTN classification and tariff estimation</p>
          </div>
        </div>
        <Link to="/dashboard/hitl-review">
          <Button variant="outline" className="premium-card px-5 py-2.5 h-auto shadow-sm hover:shadow-md transition-all flex items-center gap-2 font-semibold">
            HITL Review <ArrowRight className="w-4 h-4" />
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* ── Left Panel ─────────────────────────────────────────────── */}
        <div className="lg:col-span-4 space-y-5">

          {/* Source Type Selector */}
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3 px-1">Invoice Source</p>
            {/* Pill toggle row */}
            <div className="flex rounded-2xl border border-border bg-muted/30 p-1 gap-1">
              {[
                { type: "upload" as const, icon: <Upload size={15} />, label: "Upload JSON", sub: "Local file" },
                { type: "supabase" as const, icon: <Database size={15} />, label: "OCR Queue", sub: "Supabase" },
              ].map(({ type, icon, label, sub }) => (
                <button
                  key={type}
                  onClick={() => { setSourceType(type); setError(null); if (type === "supabase") fetchSavedInvoices(); if (type === "upload") setFile(null); }}
                  className={`flex-1 flex items-center justify-center gap-2.5 py-3 px-3 rounded-xl transition-all duration-200 active:scale-95 ${
                    sourceType === type
                      ? "bg-white dark:bg-card shadow-md text-primary font-bold border border-primary/20"
                      : "text-muted-foreground hover:text-foreground hover:bg-white/50 dark:hover:bg-card/50"
                  }`}
                >
                  <span className={`shrink-0 p-1 rounded-lg ${
                    sourceType === type ? "bg-primary/10 text-primary" : "text-muted-foreground/60"
                  }`}>{icon}</span>
                  <span className="text-left">
                    <p className="text-xs font-bold leading-tight">{label}</p>
                    <p className="text-[9px] opacity-50 leading-none mt-0.5">{sub}</p>
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Input Area Card */}
          <Card className="premium-card shadow-sm">
            <CardContent className="p-5 space-y-4">
              {sourceType === "upload" ? (
                <div>
                  <input
                    id="invoice-file"
                    type="file"
                    accept=".json,application/json"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <label
                    htmlFor="invoice-file"
                    className={`flex flex-col items-center gap-3 p-8 rounded-xl border-2 border-dashed cursor-pointer transition-all hover:border-primary/40 hover:bg-primary/2 ${
                      file ? "border-green-400 bg-green-50/20" : "border-muted-foreground/20 bg-muted/20"
                    }`}
                  >
                    <div className={`p-3 rounded-full ${file ? "bg-green-100 text-green-600" : "bg-primary/10 text-primary"}`}>
                      {file ? <CheckCircle2 size={24} /> : <FileJson size={24} />}
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-semibold">{file ? file.name : "Click to select invoice JSON"}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{file ? `${(file.size / 1024).toFixed(1)} KB` : "Supports .json files"}</p>
                    </div>
                  </label>
                </div>
              ) : (
                <div className="space-y-3">
                  <Label htmlFor="saved-json-select" className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                    Target Invoice
                  </Label>
                  <div className="flex gap-2">
                    <select
                      id="saved-json-select"
                      value={selectedSavedInvoiceId}
                      onChange={(e) => { setSelectedSavedInvoiceId(e.target.value); setResult(null); setError(null); }}
                      className="h-10 flex-1 rounded-lg border border-input bg-background px-3 text-sm focus:ring-2 focus:ring-primary/20 transition-all outline-none"
                      disabled={loadingSavedInvoices}
                    >
                      <option value="">{loadingSavedInvoices ? "Loading..." : "Select from Supabase"}</option>
                      {savedInvoices.map((inv) => (
                        <option key={inv.id} value={inv.id}>
                          {inv.source_file.replace(/^invoices\//, "").replace(/\.json$/, "")}
                        </option>
                      ))}
                    </select>
                    <Button variant="outline" size="icon" onClick={fetchSavedInvoices} disabled={loadingSavedInvoices} className="h-10 w-10 shrink-0">
                      <RotateCcw className={`w-4 h-4 ${loadingSavedInvoices ? "animate-spin" : ""}`} />
                    </Button>
                  </div>
                </div>
              )}

              <div className="space-y-2 pt-1">
                <button
                  onClick={handleSubmit}
                  disabled={loading || (sourceType === "upload" && !file) || (sourceType === "supabase" && !selectedSavedInvoiceId)}
                  className={`w-full h-12 rounded-2xl font-bold text-sm transition-all duration-200 flex items-center justify-center gap-2.5 ${
                    loading || (sourceType === "upload" && !file) || (sourceType === "supabase" && !selectedSavedInvoiceId)
                      ? "bg-muted text-muted-foreground cursor-not-allowed"
                      : "bg-gradient-to-r from-indigo-500 via-primary to-violet-500 text-white shadow-lg shadow-primary/30 hover:shadow-primary/50 hover:scale-[1.02] active:scale-95"
                  }`}
                >
                  {loading ? (
                    <><RotateCcw className="w-4 h-4 animate-spin" /> Analyzing...</>
                  ) : (
                    <><Sparkles className="w-4 h-4" /> Analyze &amp; Pre-vet</>
                  )}
                </button>
                {(file || selectedSavedInvoiceId || result) && (
                  <button onClick={handleReset} className="w-full text-xs text-muted-foreground hover:text-destructive py-1.5 transition-colors">
                    Clear Selection
                  </button>
                )}
              </div>

              {error && (
                <Alert variant="destructive" className="bg-destructive/5 text-destructive border-destructive/20">
                  <AlertDescription className="flex items-center gap-2 text-xs">
                    <AlertTriangle size={13} /> {error}
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* Info hint */}
          {!result && (
            <p className="text-center text-xs text-muted-foreground/60 px-2">
              Upload a JSON file or pick from the HITL queue to classify AHTN codes and estimate tariffs.
            </p>
          )}
        </div>

        {/* ── Right Panel ────────────────────────────────────────────── */}
        <div className="lg:col-span-8">
          {result ? (
            <div className="space-y-5">
              {/* KPI Row */}
              <div className="grid grid-cols-3 gap-4">
                <Card className="premium-card shadow-sm">
                  <CardContent className="p-5">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Est. Total Tariff</p>
                    <p className="text-2xl font-bold mt-2 tabular-nums">
                      {result.currency} {result.total_tariff.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </p>
                  </CardContent>
                </Card>
                <Card className={`premium-card shadow-sm ${result.any_requires_hitl ? "border-amber-300 bg-amber-50/20" : "border-green-300 bg-green-50/20"}`}>
                  <CardContent className="p-5">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">HITL Status</p>
                    <div className="flex items-center gap-2 mt-2">
                      <p className={`text-lg font-bold leading-tight ${result.any_requires_hitl ? "text-amber-700" : "text-green-700"}`}>
                        {result.any_requires_hitl ? "Review Required" : "Auto-Approved"}
                      </p>
                      <Badge className={result.any_requires_hitl ? "bg-amber-100 text-amber-800 border-amber-200" : "bg-green-100 text-green-800 border-green-200"}>
                        {result.any_requires_hitl ? "Action" : "Pass"}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
                <Card className="premium-card shadow-sm">
                  <CardContent className="p-5">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Line Items</p>
                    <p className="text-2xl font-bold mt-2 tabular-nums">{result.line_items.length} <span className="text-sm font-normal text-muted-foreground">items</span></p>
                  </CardContent>
                </Card>
              </div>

              {/* Flags */}
              {result.all_flags.length > 0 && (
                <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 shadow-sm">
                  <div className="flex items-center gap-2 font-bold text-amber-900 text-sm mb-2">
                    <AlertTriangle size={15} /> Compliance & Classification Flags
                  </div>
                  <ul className="space-y-1 ml-6 list-disc">
                    {result.all_flags.map((f, i) => (
                      <li key={i} className="text-xs text-amber-800">{f}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* AHTN Table */}
              <Card className="premium-card shadow-md overflow-hidden">
                <CardHeader className="border-b bg-muted/20 py-4 px-6">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-bold">AHTN Classification Details</CardTitle>
                    <span className="text-xs text-muted-foreground bg-muted/50 px-2.5 py-1 rounded-full font-mono">#{result.invoice_id}</span>
                  </div>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader className="bg-muted/20">
                        <TableRow>
                          <TableHead className="w-[44px] pl-6 text-[10px] uppercase font-bold">#</TableHead>
                          <TableHead className="text-[10px] uppercase font-bold min-w-[200px]">Product Description</TableHead>
                          <TableHead className="text-[10px] uppercase font-bold min-w-[140px]">AHTN Code</TableHead>
                          <TableHead className="text-[10px] uppercase font-bold text-right">Tax Rate</TableHead>
                          <TableHead className="text-[10px] uppercase font-bold text-right">Duty ({result.currency})</TableHead>
                          <TableHead className="text-[10px] uppercase font-bold text-center">Confidence</TableHead>
                          <TableHead className="text-[10px] uppercase font-bold pr-6 text-center">HITL</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {result.line_items.map((item) => (
                          <TableRow key={item.item_id} className={`transition-colors ${item.requires_hitl ? "bg-amber-50/50 hover:bg-amber-50/70" : "hover:bg-muted/20"}`}>
                            <TableCell className="pl-6 font-mono text-xs text-muted-foreground/60 font-bold">{item.item_id}</TableCell>
                            <TableCell>
                              <div className="space-y-1.5 py-2">
                                <span className="font-semibold text-sm block">{item.description}</span>
                                {item.flags.length > 0 && (
                                  <div className="flex flex-wrap gap-1">
                                    {item.flags.map((f, i) => (
                                      <span key={i} className="text-[9px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 border border-amber-200 font-bold flex items-center gap-1">
                                        <AlertTriangle size={7} /> {f}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className="flex flex-col gap-1 py-1">
                                <code className="text-[10px] font-mono font-bold bg-primary/5 text-primary border border-primary/20 px-2 py-0.5 rounded-md w-fit">{item.ahtn_code}</code>
                                <span className="text-[9px] text-muted-foreground max-w-[150px] truncate" title={item.ahtn_description}>{item.ahtn_description}</span>
                              </div>
                            </TableCell>
                            <TableCell className="text-right font-semibold text-xs">{item.tariff_rate}</TableCell>
                            <TableCell className="text-right font-bold tabular-nums text-sm">{item.tariff_amount.toFixed(2)}</TableCell>
                            <TableCell>
                              <div className="flex flex-col items-center gap-1">
                                <span className={`text-xs font-bold ${(item.similarity * 100) < 60 ? "text-amber-600" : "text-green-600"}`}>
                                  {(item.similarity * 100).toFixed(0)}%
                                </span>
                                <div className="w-14 h-1.5 bg-muted rounded-full overflow-hidden">
                                  <div
                                    className={`h-full rounded-full transition-all ${item.similarity > 0.8 ? "bg-green-500" : item.similarity > 0.6 ? "bg-amber-500" : "bg-red-500"}`}
                                    style={{ width: `${item.similarity * 100}%` }}
                                  />
                                </div>
                              </div>
                            </TableCell>
                            <TableCell className="pr-6 text-center">
                              {item.requires_hitl ? (
                                <Badge className="bg-amber-100 text-amber-800 border-amber-200 text-[9px] px-2 py-0 font-bold">REVIEW</Badge>
                              ) : (
                                <CheckCircle2 size={15} className="text-green-500 mx-auto" />
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            /* Empty State */
            <div className="h-full min-h-[480px] flex flex-col items-center justify-center text-center p-10 bg-card rounded-2xl border-2 border-dashed border-muted-foreground/20">
              <div className="relative mb-6">
                <div className="w-20 h-20 rounded-3xl bg-muted/30 flex items-center justify-center">
                  <FileJson size={36} className="text-muted-foreground/30" />
                </div>
                <div className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
                  <ShieldCheck size={12} className="text-primary" />
                </div>
              </div>
              <h3 className="text-lg font-bold text-foreground">Ready for Analysis</h3>
              <p className="max-w-[280px] mt-2 text-sm text-muted-foreground leading-relaxed">
                Select an invoice source on the left to begin the AHTN pre-vetting process.
              </p>
              <div className="mt-8 flex flex-col gap-2 text-xs text-muted-foreground/50">
                <div className="flex items-center gap-2"><ShieldCheck size={12} /> AHTN code classification</div>
                <div className="flex items-center gap-2"><CheckCircle2 size={12} /> Tariff rate estimation</div>
                <div className="flex items-center gap-2"><AlertTriangle size={12} /> Compliance flag detection</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
