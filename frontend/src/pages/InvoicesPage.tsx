import { useState, useEffect } from "react";
import { useApiFetch } from "../hooks/useApiFetch";
import { FileText, Plus, Download, Trash2, X, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
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
import { Skeleton } from "@/components/ui/skeleton";

interface InvoiceItem {
  description: string;
  price: number;
  quantity: number;
}

interface Invoice {
  id: string;
  invoice_number: string;
  client_id: string;
  client_name?: string;
  date: string;
  month: string;
  status: string;
  total_amount: number;
  currency?: string;
  type?: "issuing" | "receiving";
  ai_auto_paid_reason?: string;
  tariff?: number;
  items?: InvoiceItem[];
  hitl_status?: "pending_review" | "approved";
}

interface Client {
  id: string;
  name: string;
}

export default function InvoicesPage() {
  const apiFetch = useApiFetch();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [baseCurrency, setBaseCurrency] = useState("MYR");

  // Form state
  const [form, setForm] = useState({
    client_id: "",
    invoice_number: "",
    date: new Date().toISOString().split("T")[0],
    month: new Date().toISOString().slice(0, 7),
    type: "issuing",
    currency: "MYR",
    exchange_rate: 1.0,
    tariff: 0,
  });
  const [isCreating, setIsCreating] = useState(false);
  const [items, setItems] = useState<InvoiceItem[]>([
    { description: "", price: 0, quantity: 1 },
  ]);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [invRes, cliRes, compRes] = await Promise.all([
        apiFetch("/api/invoices/").catch(() => ({ invoices: [] })),
        apiFetch("/api/clients/").catch(() => ({ clients: [] })),
        apiFetch("/api/companies/me").catch(() => ({ company: null })),
      ]);
      setInvoices(invRes?.invoices || []);
      setClients(cliRes?.clients || []);
      if (compRes?.company?.base_currency) {
        setBaseCurrency(compRes.company.base_currency);
      }
    } catch (err: any) {
      alert(err.message || "Failed to load data.");
    }
    setLoading(false);
  }

  useEffect(() => {
    let active = true;
    async function updateRate() {
      if (form.currency === baseCurrency) {
        setForm(f => ({ ...f, exchange_rate: 1.0 }));
        return;
      }
      try {
        const data = await apiFetch(`/api/currency/rate?from=${form.currency}&to=${baseCurrency}`);
        if (active && data.rate) {
          setForm(f => ({ ...f, exchange_rate: data.rate }));
        }
      } catch (e) {
        // ignore
      }
    }
    updateRate();
    return () => { active = false; };
  }, [form.currency, baseCurrency]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setIsCreating(true);
    try {
      await apiFetch("/api/invoices/", {
        method: "POST",
        body: JSON.stringify({ ...form, items }),
      });
      setShowModal(false);
      setForm({
        client_id: "",
        invoice_number: "",
        date: new Date().toISOString().split("T")[0],
        month: new Date().toISOString().slice(0, 7),
        type: "issuing",
        currency: "MYR",
        exchange_rate: 1.0,
        tariff: 0,
      });
      setItems([{ description: "", price: 0, quantity: 1 }]);
      loadData();
    } catch (err: Error | any) {
      alert(err.message);
    } finally {
      setIsCreating(false);
    }
  }

  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleDelete(id: string) {
    if (!window.confirm("Delete this invoice?")) return;
    setDeletingId(id);
    try {
      await apiFetch(`/api/invoices/${id}`, { method: "DELETE" });
      setInvoices(prev => prev.filter(inv => inv.id !== id));
    } catch (err: any) {
      alert(err.message);
    } finally {
      setDeletingId(null);
    }
  }

  async function handleStatusChange(id: string, status: string) {
    await apiFetch(`/api/invoices/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    loadData();
  }

  async function handleDownloadPdf(id: string, number: string) {
    try {
      const blob = await apiFetch(`/api/invoices/${id}/pdf`);
      if (!blob) return alert("Failed to download");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `invoice_${number}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(err.message || "Failed to download PDF");
    }
  }

  async function handleViewPdf(id: string) {
    try {
      const blob = await apiFetch(`/api/invoices/${id}/pdf`);
      if (!blob) return alert("Failed to open PDF");
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank");
    } catch (err: any) {
      alert(err.message || "Failed to view PDF");
    }
  }

  function addItem() {
    setItems([...items, { description: "", price: 0, quantity: 1 }]);
  }

  function removeItem(idx: number) {
    setItems(items.filter((_, i) => i !== idx));
  }

  function updateItem(
    idx: number,
    field: keyof InvoiceItem,
    value: string | number,
  ) {
    setItems(
      items.map((item, i) =>
        i === idx
          ? {
            ...item,
            [field]: field === "description" ? value : Number(value),
          }
          : item,
      ),
    );
  }

  const totalAmount = items.reduce((sum, i) => sum + i.price * i.quantity, 0);

  // Use a single transaction feed, no filtering by activeTab
  const filteredInvoices = invoices;

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Invoices</h1>
          <p className="page-subtitle">Manage and track all your invoices.</p>
        </div>
        <Button onClick={() => { setForm({ ...form, type: "issuing" }); setShowModal(true); }}>
          <Plus size={16} />
          New Invoice
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16 gap-4">
              <Skeleton className="h-8 w-8 rounded-full" />
              <p className="text-sm text-muted-foreground">Loading invoices…</p>
            </div>
          ) : filteredInvoices.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 gap-2">
              <FileText size={40} strokeWidth={1} className="text-muted-foreground" />
              <p className="font-medium">No invoices yet</p>
              <span className="text-sm text-muted-foreground">Create your first invoice to get started.</span>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Invoice #</TableHead>
                  <TableHead>Client</TableHead>
                  <TableHead>Direction</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Tariff</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredInvoices.map((inv) => (
                  <TableRow key={inv.id}>
                    <TableCell className="font-mono text-sm">{inv.invoice_number}</TableCell>
                    <TableCell>{inv.client_name || "—"}</TableCell>
                    <TableCell>
                      {inv.type === "receiving" ? (
                        <Badge variant="destructive" className="text-xs">Outbound</Badge>
                      ) : (
                        <Badge variant="secondary" className="text-xs bg-green-100 text-green-800 border-green-200">Inbound</Badge>
                      )}
                    </TableCell>
                    <TableCell>{inv.date}</TableCell>
                    <TableCell className="font-medium tabular-nums text-muted-foreground">
                      {new Intl.NumberFormat("en-US", { style: "currency", currency: inv.currency || "USD" }).format(inv.tariff || 0)}
                    </TableCell>
                    <TableCell className={`font-medium tabular-nums ${inv.type === "receiving" ? "text-red-600" : "text-green-600"}`}>
                      {inv.type === "receiving" ? "-" : "+"}
                      {new Intl.NumberFormat("en-US", { style: "currency", currency: inv.currency || "USD" }).format(parseFloat(String(inv.total_amount)))}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <select
                          className={`h-8 rounded-md border border-input bg-background px-2 text-sm ${inv.hitl_status === 'pending_review' ? 'opacity-50 cursor-not-allowed bg-muted' : ''}`}
                          value={inv.status}
                          disabled={inv.hitl_status === 'pending_review'}
                          onChange={(e) => handleStatusChange(inv.id, e.target.value)}
                          title={inv.hitl_status === 'pending_review' ? "Disabled: Awaiting HITL/Tariff Approval" : ""}
                        >
                          <option value="unpaid">Unpaid</option>
                          <option value="paid">Paid</option>
                          <option value="partially_paid">Partial</option>
                        </select>
                        {inv.hitl_status === 'pending_review' && (
                          <Badge variant="outline" className="text-[10px] uppercase border-amber-200 text-amber-600 bg-amber-50">
                            HITL Pending
                          </Badge>
                        )}
                        {inv.ai_auto_paid_reason && (
                          <Badge variant="secondary" className="text-xs bg-blue-50 text-blue-700 border-blue-200 cursor-help" title={inv.ai_auto_paid_reason}>
                            🤖 AI Auto-Paid
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8" title="View PDF" onClick={() => handleViewPdf(inv.id)}>
                          <Eye size={14} />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8" title="Download PDF" onClick={() => handleDownloadPdf(inv.id, inv.invoice_number)}>
                          <Download size={14} />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive hover:text-destructive" title="Delete" disabled={deletingId === inv.id} onClick={() => handleDelete(inv.id)}>
                          <Trash2 size={14} />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create Invoice</DialogTitle>
            <DialogDescription>Add a new invoice with line items.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="client">Client</Label>
                <select
                  id="client"
                  required
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                  value={form.client_id}
                  onChange={(e) => setForm({ ...form, client_id: e.target.value })}
                >
                  <option value="">Select a client…</option>
                  {clients.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="type">Type</Label>
                <select
                  id="type"
                  required
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                  value={form.type}
                  onChange={(e) => setForm({ ...form, type: e.target.value as "issuing" | "receiving" })}
                >
                  <option value="issuing">Issuing (Receivable)</option>
                  <option value="receiving">Receiving (Payable Bill)</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="invoice_number">Invoice Number</Label>
                <Input id="invoice_number" required placeholder="INV-001" value={form.invoice_number} onChange={(e) => setForm({ ...form, invoice_number: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="date">Date</Label>
                <Input id="date" type="date" required value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="month">Month (YYYY-MM)</Label>
                <Input id="month" required placeholder="2024-03" value={form.month} onChange={(e) => setForm({ ...form, month: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="currency">Currency</Label>
                <select
                  id="currency"
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                  value={form.currency}
                  onChange={(e) => setForm({ ...form, currency: e.target.value })}
                >
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="MYR">MYR (RM)</option>
                  <option value="SGD">SGD (S$)</option>
                  <option value="IDR">IDR (Rp)</option>
                  <option value="PHP">PHP (₱)</option>
                  <option value="THB">THB (฿)</option>
                  <option value="VND">VND (₫)</option>
                  <option value="AED">AED</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="exchange_rate">Exchange Rate</Label>
                <Input id="exchange_rate" type="number" step="0.000001" min={0} required value={form.exchange_rate} onChange={(e) => setForm({ ...form, exchange_rate: parseFloat(e.target.value) || 1.0 })} />
                {form.currency !== baseCurrency && (
                  <p className="text-xs text-muted-foreground">Est. base: {new Intl.NumberFormat("en-US", { style: "currency", currency: baseCurrency }).format((totalAmount + (form.tariff || 0)) * form.exchange_rate)}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="tariff">Customs Tariff / Duty</Label>
                <Input id="tariff" type="number" step="0.01" min={0} value={form.tariff} onChange={(e) => setForm({ ...form, tariff: parseFloat(e.target.value) || 0 })} />
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium">Line Items</h3>
                <Button type="button" variant="outline" size="sm" onClick={addItem}>
                  <Plus size={14} /> Add Item
                </Button>
              </div>
              {items.map((item, idx) => (
                <div key={idx} className="flex gap-2 items-center">
                  <Input className="flex-2" placeholder="Description" required value={item.description} onChange={(e) => updateItem(idx, "description", e.target.value)} />
                  <Input className="w-24" type="number" step="0.01" min={0} placeholder="Price" required value={item.price || ""} onChange={(e) => updateItem(idx, "price", e.target.value)} />
                  <Input className="w-20" type="number" min={1} placeholder="Qty" required value={item.quantity || ""} onChange={(e) => updateItem(idx, "quantity", e.target.value)} />
                  {items.length > 1 && (
                    <Button type="button" variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => removeItem(idx)}>
                      <X size={14} />
                    </Button>
                  )}
                </div>
              ))}
              <div className="flex justify-end gap-4 pt-2 border-t font-semibold">
                <span>Grand Total:</span>
                <span>{new Intl.NumberFormat("en-US", { style: "currency", currency: form.currency || "USD" }).format(totalAmount + (form.tariff || 0))}</span>
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowModal(false)}>Cancel</Button>
              <Button type="submit" disabled={isCreating}>{isCreating ? "Creating…" : "Create Invoice"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
