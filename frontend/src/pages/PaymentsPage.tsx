import { useState, useEffect } from "react";
import { useApiFetch } from "../hooks/useApiFetch";
import { CreditCard, Plus, Trash2, X } from "lucide-react";

interface Payment {
  id: string;
  client_id: string;
  client_name?: string;
  amount: number;
  date: string;
  method: string | null;
  notes: string | null;
  currency?: string;
  exchange_rate?: string | number;
  created_at: string;
}

interface Client {
  id: string;
  name: string;
}

export default function PaymentsPage() {
  const apiFetch = useApiFetch();
  const [payments, setPayments] = useState<Payment[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [baseCurrency, setBaseCurrency] = useState("MYR");
  const [form, setForm] = useState({
    client_id: "",
    amount: "",
    date: new Date().toISOString().split("T")[0],
    method: "",
    notes: "",
    currency: "MYR",
    exchange_rate: 1.0,
  });

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [payRes, cliRes, compRes] = await Promise.all([
        apiFetch("/api/payments/").catch(() => ({ payments: [] })),
        apiFetch("/api/clients/").catch(() => ({ clients: [] })),
        apiFetch("/api/companies/me").catch(() => ({ company: null })),
      ]);
      setPayments(payRes?.payments || []);
      setClients(cliRes?.clients || []);
      if (compRes?.company?.base_currency) {
        setBaseCurrency(compRes.company.base_currency);
      }
    } catch (err: any) {
      alert(err.message || "Failed to load payments data");
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

  const [isCreating, setIsCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setIsCreating(true);
    try {
      await apiFetch("/api/payments/", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          amount: parseFloat(form.amount),
        }),
      });
      setShowModal(false);
      setForm({
        client_id: "",
        amount: "",
        date: new Date().toISOString().split("T")[0],
        method: "",
        notes: "",
        currency: "MYR",
        exchange_rate: 1.0,
      });
      loadData();
    } catch (err: Error | any) {
      alert(err.message);
    } finally {
      setIsCreating(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this payment?")) return;
    setDeletingId(id);
    try {
      await apiFetch(`/api/payments/${id}`, { method: "DELETE" });
      setPayments(prev => prev.filter(p => p.id !== id));
    } catch (err: any) {
      alert(err.message || "Failed to delete payment.");
    } finally {
      setDeletingId(null);
    }
  }

  const totalPaid = payments.reduce(
    (sum, p) => sum + parseFloat(String(p.amount || 0)) * parseFloat(String(p.exchange_rate || 1)),
    0,
  );

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Payments</h1>
          <p className="page-subtitle">Track all received payments.</p>
        </div>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={16} />
          Record Payment
        </button>
      </div>

      {/* Summary cards */}
      <div className="payment-summary">
        <div className="summary-card">
          <span className="summary-label">Total Payments</span>
          <span className="summary-value">{payments.length}</span>
        </div>
        <div className="summary-card">
          <span className="summary-label">Total Collected (Est. Base Value)</span>
          <span className="summary-value">
            {new Intl.NumberFormat("en-US", { style: "currency", currency: baseCurrency }).format(totalPaid)}
          </span>
        </div>
      </div>

      <div className="table-container" style={{ animationDelay: "100ms" }}>
        {loading ? (
          <div className="table-empty">
            <div className="spinner" />
            <p>Loading payments…</p>
          </div>
        ) : payments.length === 0 ? (
          <div className="table-empty">
            <CreditCard size={40} strokeWidth={1} className="empty-icon" />
            <p>No payments recorded</p>
            <span>Record your first payment to start tracking.</span>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Client</th>
                <th>Amount</th>
                <th>Date</th>
                <th>Method</th>
                <th>Notes</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {payments.map((p, i) => (
                <tr key={p.id} style={{ animationDelay: `${i * 40}ms` }}>
                  <td className="cell-bold">{p.client_name || "—"}</td>
                  <td className="cell-amount cell-positive">
                    {new Intl.NumberFormat("en-US", { style: "currency", currency: p.currency || "USD" }).format(parseFloat(String(p.amount)))}
                  </td>
                  <td>{p.date}</td>
                  <td>{p.method || "—"}</td>
                  <td className="cell-truncate">{p.notes || "—"}</td>
                  <td>
                    <button
                      className={`btn-icon btn-icon-danger ${deletingId === p.id ? 'opacity-50 cursor-not-allowed' : ''}`}
                      title="Delete"
                      disabled={deletingId === p.id}
                      onClick={() => handleDelete(p.id)}
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Record Payment</h2>
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
                    <option value="">Select client…</option>
                    {clients.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-field">
                  <label>Amount</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    required
                    placeholder="0.00"
                    value={form.amount}
                    onChange={(e) =>
                      setForm({ ...form, amount: e.target.value })
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
                  <label>Method</label>
                  <select
                    value={form.method}
                    onChange={(e) => setForm({ ...form, method: e.target.value })}
                  >
                    <option value="">Select method…</option>
                    <option value="bank_transfer">Bank Transfer</option>
                    <option value="cash">Cash</option>
                    <option value="check">Check</option>
                    <option value="card">Card</option>
                    <option value="other">Other</option>
                  </select>
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
                    <p className="text-xs text-gray-500 mt-1">Est. base value: {new Intl.NumberFormat("en-US", { style: "currency", currency: baseCurrency }).format((parseFloat(form.amount) || 0) * (form.exchange_rate as number))}</p>
                  )}
                </div>
                <div className="form-field full-width">
                  <label>Notes</label>
                  <textarea
                    placeholder="Optional notes…"
                    value={form.notes}
                    onChange={(e) =>
                      setForm({ ...form, notes: e.target.value })
                    }
                  />
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
                  {isCreating ? "Recording…" : "Record Payment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
