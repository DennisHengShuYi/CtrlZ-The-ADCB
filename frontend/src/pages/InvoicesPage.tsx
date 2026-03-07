import { useState, useEffect } from "react";
import { useApiFetch } from "../hooks/useApiFetch";
import { FileText, Plus, Download, Trash2, X, Eye } from "lucide-react";

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
  items?: InvoiceItem[];
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
        <button className="btn-primary" onClick={() => {
          setForm({ ...form, type: "issuing" }); // default type when creating manually
          setShowModal(true);
        }}>
          <Plus size={16} />
          New Invoice
        </button>
      </div>

      {/* Removed Tabs for Unified Feed */}

      {/* Invoice Table */}
      <div className="table-container" style={{ animationDelay: "100ms" }}>
        {loading ? (
          <div className="table-empty">
            <div className="spinner" />
            <p>Loading invoices…</p>
          </div>
        ) : filteredInvoices.length === 0 ? (
          <div className="table-empty">
            <FileText size={40} strokeWidth={1} className="empty-icon" />
            <p>No invoices yet</p>
            <span>Create your first invoice to get started.</span>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Invoice #</th>
                <th>Client</th>
                <th>Direction</th>
                <th>Date</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredInvoices.map((inv, i) => (
                <tr key={inv.id} style={{ animationDelay: `${i * 40}ms` }}>
                  <td className="cell-mono">{inv.invoice_number}</td>
                  <td>{inv.client_name || "—"}</td>
                  <td>
                    {inv.type === "receiving" ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                        Outbound
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                        Inbound
                      </span>
                    )}
                  </td>
                  <td>{inv.date}</td>
                  <td className={`font-medium ${inv.type === "receiving" ? "text-red-600" : "text-green-600"}`}>
                    {inv.type === "receiving" ? "-" : "+"}
                    {new Intl.NumberFormat("en-US", {
                      style: "currency",
                      currency: inv.currency || "USD",
                    }).format(parseFloat(String(inv.total_amount)))}
                  </td>
                  <td>
                    <div className="flex items-center gap-2">
                      <select
                        className="status-select"
                        value={inv.status}
                        onChange={(e) =>
                          handleStatusChange(inv.id, e.target.value)
                        }
                      >
                        <option value="unpaid">Unpaid</option>
                        <option value="paid">Paid</option>
                        <option value="partially_paid">Partial</option>
                      </select>
                      {inv.ai_auto_paid_reason && (
                        <span
                          className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 cursor-help"
                          title={inv.ai_auto_paid_reason}
                        >
                          🤖 AI Auto-Paid
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    <div className="action-buttons">
                      <button
                        className="btn-icon cursor-pointer"
                        title="View PDF"
                        onClick={() => handleViewPdf(inv.id)}
                      >
                        <Eye size={14} />
                      </button>
                      <button
                        className="btn-icon cursor-pointer"
                        title="Download PDF"
                        onClick={() => handleDownloadPdf(inv.id, inv.invoice_number)}
                      >
                        <Download size={14} />
                      </button>
                      <button
                        className={`btn-icon btn-icon-danger cursor-pointer ${deletingId === inv.id ? "opacity-50 cursor-not-allowed" : ""}`}
                        title="Delete"
                        disabled={deletingId === inv.id}
                        onClick={() => handleDelete(inv.id)}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Create Invoice Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Create Invoice</h2>
              <button className="btn-icon" onClick={() => setShowModal(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleCreate}>
              <div className="form-grid">
                <div className="form-field">
                  <label>Client</label>
                  <select
                    required
                    value={form.client_id}
                    onChange={(e) =>
                      setForm({ ...form, client_id: e.target.value })
                    }
                  >
                    <option value="">Select a client…</option>
                    {clients.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-field">
                  <label>Type</label>
                  <select
                    required
                    value={form.type}
                    onChange={(e) =>
                      setForm({ ...form, type: e.target.value as "issuing" | "receiving" })
                    }
                  >
                    <option value="issuing">Issuing (Receivable)</option>
                    <option value="receiving">Receiving (Payable Bill)</option>
                  </select>
                </div>
                <div className="form-field">
                  <label>Invoice Number</label>
                  <input
                    required
                    placeholder="INV-001"
                    value={form.invoice_number}
                    onChange={(e) =>
                      setForm({ ...form, invoice_number: e.target.value })
                    }
                  />
                </div>
                <div className="form-field">
                  <label>Date</label>
                  <input
                    type="date"
                    required
                    value={form.date}
                    onChange={(e) => setForm({ ...form, date: e.target.value })}
                  />
                </div>
                <div className="form-field">
                  <label>Month (YYYY-MM)</label>
                  <input
                    required
                    placeholder="2024-03"
                    value={form.month}
                    onChange={(e) => setForm({ ...form, month: e.target.value })}
                  />
                </div>
                <div className="form-field">
                  <label>Currency</label>
                  <select
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
                <div className="form-field">
                  <label>Exchange Rate</label>
                  <input
                    type="number"
                    step="0.000001"
                    min="0"
                    required
                    value={form.exchange_rate}
                    onChange={(e) => setForm({ ...form, exchange_rate: parseFloat(e.target.value) || 1.0 })}
                  />
                  {form.currency !== baseCurrency && (
                    <p className="text-xs text-gray-500 mt-1">Est. base value: {new Intl.NumberFormat("en-US", { style: "currency", currency: baseCurrency }).format(totalAmount * form.exchange_rate)}</p>
                  )}
                </div>
              </div>

              <div className="form-section">
                <div className="form-section-header">
                  <h3>Line Items</h3>
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    onClick={addItem}
                  >
                    <Plus size={14} /> Add Item
                  </button>
                </div>
                {items.map((item, idx) => (
                  <div key={idx} className="line-item-row">
                    <input
                      className="line-item-desc"
                      placeholder="Description"
                      required
                      value={item.description}
                      onChange={(e) =>
                        updateItem(idx, "description", e.target.value)
                      }
                    />
                    <input
                      className="line-item-num"
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="Price"
                      required
                      value={item.price || ""}
                      onChange={(e) => updateItem(idx, "price", e.target.value)}
                    />
                    <input
                      className="line-item-num"
                      type="number"
                      min="1"
                      placeholder="Qty"
                      required
                      value={item.quantity || ""}
                      onChange={(e) =>
                        updateItem(idx, "quantity", e.target.value)
                      }
                    />
                    {items.length > 1 && (
                      <button
                        type="button"
                        className="btn-icon btn-icon-danger"
                        onClick={() => removeItem(idx)}
                      >
                        <X size={14} />
                      </button>
                    )}
                  </div>
                ))}
                <div className="line-item-total">
                  <span>Total:</span>
                  <span className="cell-amount">
                    {new Intl.NumberFormat("en-US", {
                      style: "currency",
                      currency: form.currency || "USD",
                    }).format(totalAmount)}
                  </span>
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={isCreating}>
                  {isCreating ? "Creating…" : "Create Invoice"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
