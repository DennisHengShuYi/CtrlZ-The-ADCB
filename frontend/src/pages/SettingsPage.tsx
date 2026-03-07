import { useState, useEffect } from "react";
import { useApiFetch } from "../hooks/useApiFetch";
import { Save, Building2, CheckCircle } from "lucide-react";

export default function SettingsPage() {
  const apiFetch = useApiFetch();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [form, setForm] = useState({
    name: "",
    address: "",
    business_reg: "",
    logo_url: "",
    base_currency: "MYR",
  });
  const [hasCompany, setHasCompany] = useState(false);

  useEffect(() => {
    loadCompany();
  }, []);

  async function loadCompany() {
    setLoading(true);
    try {
      const res = await apiFetch("/api/companies/me");
      if (res?.company) {
        setForm({
          name: res.company.name || "",
          address: res.company.address || "",
          business_reg: res.company.business_reg || "",
          logo_url: res.company.logo_url || "",
          base_currency: res.company.base_currency || "MYR",
        });
        setHasCompany(true);
      }
    } catch (err: any) {
      alert(err.message || "Failed to load company settings.");
    }
    setLoading(false);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaved(false);
    try {
      if (hasCompany) {
        await apiFetch("/api/companies/me", {
          method: "PUT",
          body: JSON.stringify(form),
        });
      } else {
        await apiFetch("/api/companies/", {
          method: "POST",
          body: JSON.stringify(form),
        });
        setHasCompany(true);
      }
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err: Error | any) {
      alert(err.message);
    }
    setSaving(false);
  }

  if (loading) {
    return (
      <div className="page-container">
        <div className="table-empty">
          <div className="spinner" />
          <p>Loading settings…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">
            Configure your company profile. This info appears on your invoices.
          </p>
        </div>
      </div>

      <div className="settings-card">
        <div className="settings-card-header">
          <Building2 size={20} strokeWidth={1.5} />
          <h2>Company Profile</h2>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-grid settings-form">
            <div className="form-field full-width">
              <label>Company Name</label>
              <input
                required
                placeholder="Your Company Sdn Bhd"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div className="form-field full-width">
              <label>Address</label>
              <textarea
                rows={3}
                placeholder="123 Main Street, Kuala Lumpur, Malaysia"
                value={form.address}
                onChange={(e) => setForm({ ...form, address: e.target.value })}
              />
            </div>
            <div className="form-field">
              <label>Business Registration No.</label>
              <input
                placeholder="202301012345"
                value={form.business_reg}
                onChange={(e) =>
                  setForm({ ...form, business_reg: e.target.value })
                }
              />
            </div>
            <div className="form-field">
              <label>Logo URL</label>
              <input
                placeholder="https://example.com/logo.png"
                value={form.logo_url}
                onChange={(e) => setForm({ ...form, logo_url: e.target.value })}
              />
            </div>
            <div className="form-field full-width">
              <label>Company Base Currency</label>
              <select
                value={form.base_currency}
                onChange={(e) => setForm({ ...form, base_currency: e.target.value })}
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
              <p className="text-xs text-gray-500 mt-1">This defines how the dashboard calculates your total net values.</p>
            </div>
          </div>

          <div className="settings-footer">
            {saved && (
              <span className="save-success">
                <CheckCircle size={14} />
                Saved successfully
              </span>
            )}
            <button type="submit" className="btn-primary" disabled={saving}>
              <Save size={16} />
              {saving
                ? "Saving…"
                : hasCompany
                  ? "Save Changes"
                  : "Create Company"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
