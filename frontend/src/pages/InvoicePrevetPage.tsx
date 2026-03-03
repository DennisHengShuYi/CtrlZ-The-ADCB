import { useState, useCallback } from "react";
import { UserButton } from "@clerk/clerk-react";
import { Link } from "react-router-dom";

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

export default function InvoicePrevetPage() {
  const [file, setFile] = useState<File | null>(null);
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
      setResult(null);
      setError(null);
    }
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!file) {
      setError("Please select a JSON file first");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const text = await file.text();
      const invoice = JSON.parse(text);
      const res = await fetch(`${API_BASE}/api/invoice/pre-vet`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(invoice),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Request failed: ${res.status}`);
      }
      const data: PreVetResult = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }, [file]);

  const handleReset = useCallback(() => {
    setFile(null);
    setResult(null);
    setError(null);
  }, []);

  return (
    <div className="invoice-prevet-page">
      <header className="dashboard-header">
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <Link to="/dashboard" className="text-sm text-muted-foreground hover:text-foreground">
            ← Dashboard
          </Link>
          <span style={{ color: "oklch(0.8 0 0)" }}>/</span>
          <h1>Invoice Pre-vet</h1>
        </div>
        <div className="header-actions">
          <UserButton afterSignOutUrl="/" />
        </div>
      </header>

      <main className="dashboard-main">
        <div>
          <h2 className="dashboard-section-title">Upload Invoice JSON</h2>
          <p className="dashboard-section-subtitle">
            Upload a JSON file matching the invoice schema. The system will classify line items against AHTN, calculate tariffs, and flag items for human review.
          </p>
        </div>

        <div className="prevet-upload-card">
          <div className="prevet-upload-zone">
            <input
              type="file"
              accept=".json,application/json"
              onChange={handleFileChange}
              id="invoice-file"
              className="prevet-file-input"
            />
            <label htmlFor="invoice-file" className="prevet-file-label">
              {file ? file.name : "Choose JSON file or drag and drop"}
            </label>
          </div>

          <div className="prevet-actions">
            <button
              onClick={handleSubmit}
              disabled={!file || loading}
              className="prevet-submit-btn"
            >
              {loading ? "Processing…" : "Pre-vet Invoice"}
            </button>
            {(file || result) && (
              <button onClick={handleReset} className="prevet-reset-btn">
                Reset
              </button>
            )}
          </div>

          {error && (
            <div className="prevet-error">
              ⚠ {error}
            </div>
          )}
        </div>

        {result && (
          <div className="prevet-result">
            <h3 className="prevet-result-title">Results</h3>
            <div className="prevet-summary">
              <span>Invoice: <strong>{result.invoice_id}</strong></span>
              <span>Total tariff: <strong>{result.total_tariff.toFixed(2)}</strong></span>
              <span>
                HITL required:{" "}
                <strong className={result.any_requires_hitl ? "text-amber-600" : "text-green-600"}>
                  {result.any_requires_hitl ? "Yes" : "No"}
                </strong>
              </span>
            </div>
            {result.all_flags.length > 0 && (
              <div className="prevet-flags">
                <strong>Flags:</strong>
                <ul>
                  {result.all_flags.map((f, i) => (
                    <li key={i}>⚠ {f}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="prevet-line-items">
              <h4>Line items</h4>
              <table className="prevet-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Description</th>
                    <th>AHTN Code</th>
                    <th>Rate</th>
                    <th>Tariff</th>
                    <th>Sim</th>
                    <th>HITL</th>
                  </tr>
                </thead>
                <tbody>
                  {result.line_items.map((item) => (
                    <tr key={item.item_id} className={item.requires_hitl ? "requires-hitl" : ""}>
                      <td>{item.item_id}</td>
                      <td>
                        <span className="desc-text">{item.description}</span>
                        {item.flags.length > 0 && (
                          <ul className="item-flags">
                            {item.flags.map((f, i) => (
                              <li key={i}>⚠ {f}</li>
                            ))}
                          </ul>
                        )}
                      </td>
                      <td>
                        <code>{item.ahtn_code}</code>
                        {item.ahtn_description && (
                          <span className="ahtn-desc">
                            {item.ahtn_description.length > 40
                              ? `${item.ahtn_description.slice(0, 40)}…`
                              : item.ahtn_description}
                          </span>
                        )}
                      </td>
                      <td>{item.tariff_rate}</td>
                      <td>{item.tariff_amount.toFixed(2)}</td>
                      <td>{(item.similarity * 100).toFixed(0)}%</td>
                      <td>{item.requires_hitl ? "Yes" : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
