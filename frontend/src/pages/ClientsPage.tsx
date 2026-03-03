import { useState, useEffect } from "react";
import { useApiFetch } from "../hooks/useApiFetch";
import { Users, Plus, Trash2, X, Edit3 } from "lucide-react";

interface Client {
  id: string;
  company_id: string;
  name: string;
  contact_info: string | null;
  business_reg: string | null;
  person_in_charge: string | null;
  type: string | null;
  created_at: string;
}

const EMPTY_FORM = {
  name: "",
  contact_info: "",
  business_reg: "",
  person_in_charge: "",
  type: "customer" as string,
};

export default function ClientsPage() {
  const apiFetch = useApiFetch();
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState({ ...EMPTY_FORM });

  useEffect(() => {
    loadClients();
  }, []);

  async function loadClients() {
    setLoading(true);
    try {
      const res = await apiFetch("/api/clients/");
      setClients(res?.clients || []);
    } catch {
      /* empty */
    }
    setLoading(false);
  }

  function openCreate() {
    setEditId(null);
    setForm({ ...EMPTY_FORM });
    setShowModal(true);
  }

  function openEdit(c: Client) {
    setEditId(c.id);
    setForm({
      name: c.name,
      contact_info: c.contact_info || "",
      business_reg: c.business_reg || "",
      person_in_charge: c.person_in_charge || "",
      type: c.type || "customer",
    });
    setShowModal(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      if (editId) {
        await apiFetch(`/api/clients/${editId}`, {
          method: "PUT",
          body: JSON.stringify({ ...form, company_id: "" }),
        });
      } else {
        await apiFetch("/api/clients/", {
          method: "POST",
          body: JSON.stringify({ ...form, company_id: "" }),
        });
      }
      setShowModal(false);
      loadClients();
    } catch (err: Error | any) {
      alert(err.message);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this client and all their invoices?")) return;
    await apiFetch(`/api/clients/${id}`, { method: "DELETE" });
    loadClients();
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Clients</h1>
          <p className="page-subtitle">Manage your customers and suppliers.</p>
        </div>
        <button className="btn-primary" onClick={openCreate}>
          <Plus size={16} />
          Add Client
        </button>
      </div>

      <div className="table-container" style={{ animationDelay: "100ms" }}>
        {loading ? (
          <div className="table-empty">
            <div className="spinner" />
            <p>Loading clients…</p>
          </div>
        ) : clients.length === 0 ? (
          <div className="table-empty">
            <Users size={40} strokeWidth={1} className="empty-icon" />
            <p>No clients yet</p>
            <span>Add your first client to start creating invoices.</span>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Contact</th>
                <th>Person in Charge</th>
                <th>Reg. No.</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {clients.map((c, i) => (
                <tr key={c.id} style={{ animationDelay: `${i * 40}ms` }}>
                  <td className="cell-bold">{c.name}</td>
                  <td>
                    <span
                      className={`type-badge ${c.type === "supplier" ? "badge-info" : "badge-default"}`}
                    >
                      {c.type || "customer"}
                    </span>
                  </td>
                  <td>{c.contact_info || "—"}</td>
                  <td>{c.person_in_charge || "—"}</td>
                  <td className="cell-mono">{c.business_reg || "—"}</td>
                  <td>
                    <div className="action-buttons">
                      <button
                        className="btn-icon"
                        title="Edit"
                        onClick={() => openEdit(c)}
                      >
                        <Edit3 size={14} />
                      </button>
                      <button
                        className="btn-icon btn-icon-danger"
                        title="Delete"
                        onClick={() => handleDelete(c.id)}
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

      {/* Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editId ? "Edit Client" : "Add Client"}</h2>
              <button className="btn-icon" onClick={() => setShowModal(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-grid">
                <div className="form-field full-width">
                  <label>Client Name</label>
                  <input
                    required
                    placeholder="ABC Corporation"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                  />
                </div>
                <div className="form-field">
                  <label>Type</label>
                  <select
                    value={form.type}
                    onChange={(e) => setForm({ ...form, type: e.target.value })}
                  >
                    <option value="customer">Customer</option>
                    <option value="supplier">Supplier</option>
                  </select>
                </div>
                <div className="form-field">
                  <label>Contact Info</label>
                  <input
                    placeholder="email@example.com"
                    value={form.contact_info}
                    onChange={(e) =>
                      setForm({ ...form, contact_info: e.target.value })
                    }
                  />
                </div>
                <div className="form-field">
                  <label>Person in Charge</label>
                  <input
                    placeholder="John Doe"
                    value={form.person_in_charge}
                    onChange={(e) =>
                      setForm({ ...form, person_in_charge: e.target.value })
                    }
                  />
                </div>
                <div className="form-field">
                  <label>Business Registration</label>
                  <input
                    placeholder="REG-12345"
                    value={form.business_reg}
                    onChange={(e) =>
                      setForm({ ...form, business_reg: e.target.value })
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
                <button type="submit" className="btn-primary">
                  {editId ? "Save Changes" : "Add Client"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
