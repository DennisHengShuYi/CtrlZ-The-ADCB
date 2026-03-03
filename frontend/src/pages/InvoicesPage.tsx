import { useState, useEffect } from "react";
import { useApiFetch } from "../hooks/useApiFetch";
import {
  FileText,
  Plus,
  Download,
  Trash2,
  X,
  CheckCircle2,
  Clock,
  AlertCircle,
} from "lucide-react";

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
  items?: InvoiceItem[];
}

interface Client {
  id: string;
  name: string;
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<
    string,
    { icon: React.ElementType; cls: string; label: string }
  > = {
    paid: { icon: CheckCircle2, cls: "badge-success", label: "Paid" },
    unpaid: { icon: Clock, cls: "badge-warning", label: "Unpaid" },
    partially_paid: { icon: AlertCircle, cls: "badge-info", label: "Partial" },
  };
  const c = config[status] || config.unpaid;
  return (
    <span className={`status-badge ${c.cls}`}>
      <c.icon size={12} />
      {c.label}
    </span>
  );
}

export default function InvoicesPage() {
  const apiFetch = useApiFetch();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  // Form state
  const [form, setForm] = useState({
    client_id: "",
    invoice_number: "",
    date: new Date().toISOString().split("T")[0],
    month: new Date().toISOString().slice(0, 7),
  });
  const [items, setItems] = useState<InvoiceItem[]>([
    { description: "", price: 0, quantity: 1 },
  ]);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [invRes, cliRes] = await Promise.all([
        apiFetch("/api/invoices/").catch(() => ({ invoices: [] })),
        apiFetch("/api/clients/").catch(() => ({ clients: [] })),
      ]);
      setInvoices(invRes?.invoices || []);
      setClients(cliRes?.clients || []);
    } catch {
      /* empty */
    }
    setLoading(false);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
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
      });
      setItems([{ description: "", price: 0, quantity: 1 }]);
      loadData();
    } catch (err: Error | any) {
      alert(err.message);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this invoice?")) return;
    await apiFetch(`/api/invoices/${id}`, { method: "DELETE" });
    loadData();
  }

  async function handleStatusChange(id: string, status: string) {
    await apiFetch(`/api/invoices/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    loadData();
  }

  async function handleDownloadPdf(id: string, number: string) {
    const token = await (window as any).__clerk_token_getter?.();
    const res = await fetch(`http://localhost:8000/api/invoices/${id}/pdf`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return alert("Failed to download");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `invoice_${number}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
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

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Invoices</h1>
          <p className="page-subtitle">Manage and track all your invoices.</p>
        </div>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={16} />
          New Invoice
        </button>
      </div>

      {/* Invoice Table */}
      <div className="table-container" style={{ animationDelay: "100ms" }}>
        {loading ? (
          <div className="table-empty">
            <div className="spinner" />
            <p>Loading invoices…</p>
          </div>
        ) : invoices.length === 0 ? (
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
                <th>Date</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv, i) => (
                <tr key={inv.id} style={{ animationDelay: `${i * 40}ms` }}>
                  <td className="cell-mono">{inv.invoice_number}</td>
                  <td>{inv.client_name || "—"}</td>
                  <td>{inv.date}</td>
                  <td className="cell-amount">
                    $
                    {parseFloat(String(inv.total_amount)).toLocaleString(
                      "en-US",
                      { minimumFractionDigits: 2 },
                    )}
                  </td>
                  <td>
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
                  </td>
                  <td>
                    <div className="action-buttons">
                      <button
                        className="btn-icon"
                        title="Download PDF"
                        onClick={() =>
                          handleDownloadPdf(inv.id, inv.invoice_number)
                        }
                      >
                        <Download size={14} />
                      </button>
                      <button
                        className="btn-icon btn-icon-danger"
                        title="Delete"
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
                    onChange={(e) =>
                      setForm({ ...form, month: e.target.value })
                    }
                  />
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
                    $
                    {totalAmount.toLocaleString("en-US", {
                      minimumFractionDigits: 2,
                    })}
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
                <button type="submit" className="btn-primary">
                  Create Invoice
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
