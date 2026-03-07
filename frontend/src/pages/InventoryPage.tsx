import { useState, useEffect } from "react";
import { useApiFetch } from "../hooks/useApiFetch";
import { Package, Plus, Trash2, X, Edit3 } from "lucide-react";

interface Product {
    id: string;
    name: string;
    inventory: number;
    threshold: number;
    price: number;
    cost_price: number;
    currency: string;
    image: string | null;
}

const EMPTY_FORM = {
    name: "",
    inventory: 0,
    threshold: 10,
    price: 0,
    cost_price: 0,
    currency: "MYR",
    image: "",
};

export default function InventoryPage() {
    const apiFetch = useApiFetch();
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editId, setEditId] = useState<string | null>(null);
    const [form, setForm] = useState({ ...EMPTY_FORM });

    useEffect(() => {
        loadProducts();
    }, []);

    async function loadProducts() {
        setLoading(true);
        try {
            const res = await apiFetch("/api/products");
            setProducts(res || []);
        } catch (err: any) {
            alert(err.message || "Failed to load products.");
        }
        setLoading(false);
    }

    function openCreate() {
        setEditId(null);
        setForm({ ...EMPTY_FORM });
        setShowModal(true);
    }

    function openEdit(p: Product) {
        setEditId(p.id);
        setForm({
            name: p.name,
            inventory: p.inventory,
            threshold: p.threshold,
            price: p.price || 0,
            cost_price: p.cost_price || 0,
            currency: p.currency || "MYR",
            image: p.image || "",
        });
        setShowModal(true);
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setIsSubmitting(true);
        try {
            if (editId) {
                await apiFetch(`/api/products/${editId}`, {
                    method: "PATCH",
                    body: JSON.stringify(form),
                });
            } else {
                await apiFetch("/api/products", {
                    method: "POST",
                    body: JSON.stringify(form),
                });
            }
            setShowModal(false);
            loadProducts();
        } catch (err: Error | any) {
            alert(err.message);
        } finally {
            setIsSubmitting(false);
        }
    }

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    async function handleDelete(id: string) {
        if (!window.confirm("Delete this product from your inventory?")) return;
        setDeletingId(id);
        try {
            await apiFetch(`/api/products/${id}`, { method: "DELETE" });
            setProducts(prev => prev.filter(c => c.id !== id));
        } catch (err: any) {
            alert(err.message);
        } finally {
            setDeletingId(null);
        }
    }

    return (
        <div className="page-container">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Inventory Dashboard</h1>
                    <p className="page-subtitle">Manage your product catalog, prices, and stock levels.</p>
                </div>
                <button className="btn-primary" onClick={openCreate}>
                    <Plus size={16} />
                    Add Product
                </button>
            </div>

            <div className="table-container" style={{ animationDelay: "100ms" }}>
                {loading ? (
                    <div className="table-empty">
                        <div className="spinner" />
                        <p>Loading products…</p>
                    </div>
                ) : products.length === 0 ? (
                    <div className="table-empty">
                        <Package size={40} strokeWidth={1} className="empty-icon" />
                        <p>No products yet</p>
                        <span>Add your first product to start taking orders.</span>
                    </div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Icon</th>
                                <th>Name</th>
                                <th>Selling Price</th>
                                <th>Profit Margin</th>
                                <th>Current Stock</th>
                                <th>Threshold</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {products.map((p, i) => {
                                const profit = p.price - (p.cost_price || 0);
                                const profitMargin = p.price > 0 ? (profit / p.price) * 100 : 0;
                                const isLowStock = p.inventory <= p.threshold;

                                return (
                                    <tr key={p.id} style={{ animationDelay: `${i * 40}ms` }} className={isLowStock ? "bg-red-500/5 text-red-100" : ""}>
                                        <td><span style={{ fontSize: "1.5rem" }}>{p.image || "📦"}</span></td>
                                        <td className="cell-bold">{p.name}</td>
                                        <td>{p.currency} {p.price.toFixed(2)}</td>
                                        <td>
                                            <div className="flex flex-col">
                                                <span className={(profit > 0 ? "text-green-400" : "text-gray-400")}>{p.currency} {profit.toFixed(2)}</span>
                                                <span className="text-xs opacity-60">{profitMargin.toFixed(1)}% margin</span>
                                            </div>
                                        </td>
                                        <td>
                                            <span
                                                className={`type-badge ${isLowStock ? "badge-danger" : "badge-success"}`}
                                            >
                                                {p.inventory}
                                            </span>
                                        </td>
                                        <td className="cell-mono">{p.threshold}</td>
                                        <td>
                                            <div className="action-buttons">
                                                <button
                                                    className="btn-icon cursor-pointer"
                                                    title="Edit"
                                                    onClick={() => openEdit(p)}
                                                >
                                                    <Edit3 size={14} />
                                                </button>
                                                <button
                                                    className={`btn-icon btn-icon-danger cursor-pointer ${deletingId === p.id ? 'opacity-50 cursor-not-allowed' : ''}`}
                                                    title="Delete"
                                                    disabled={deletingId === p.id}
                                                    onClick={() => handleDelete(p.id)}
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Modal */}
            {showModal && (
                <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) setShowModal(false); }}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>{editId ? "Edit Product" : "Add Product"}</h2>
                            <button className="btn-icon" onClick={() => setShowModal(false)}>
                                <X size={18} />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit}>
                            <div className="form-grid">
                                <div className="form-field full-width">
                                    <label>Product Name</label>
                                    <input
                                        required
                                        placeholder="e.g. Curry Puff"
                                        value={form.name}
                                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                                    />
                                </div>
                                <div className="form-field">
                                    <label>Cost Price</label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        required
                                        value={form.cost_price}
                                        onChange={(e) => setForm({ ...form, cost_price: parseFloat(e.target.value) || 0 })}
                                    />
                                </div>
                                <div className="form-field">
                                    <label>Selling Price</label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        required
                                        value={form.price}
                                        onChange={(e) => setForm({ ...form, price: parseFloat(e.target.value) || 0 })}
                                    />
                                </div>
                                <div className="form-field">
                                    <label>Currency</label>
                                    <input
                                        placeholder="MYR"
                                        value={form.currency}
                                        onChange={(e) =>
                                            setForm({ ...form, currency: e.target.value })
                                        }
                                    />
                                </div>
                                <div className="form-field">
                                    <label>Current Stock (Inventory)</label>
                                    <input
                                        type="number"
                                        required
                                        value={form.inventory}
                                        onChange={(e) => setForm({ ...form, inventory: parseInt(e.target.value, 10) || 0 })}
                                    />
                                </div>
                                <div className="form-field">
                                    <label>Low Stock Threshold</label>
                                    <input
                                        type="number"
                                        required
                                        value={form.threshold}
                                        onChange={(e) => setForm({ ...form, threshold: parseInt(e.target.value, 10) || 0 })}
                                    />
                                </div>
                                <div className="form-field">
                                    <label>Emoji Icon</label>
                                    <input
                                        placeholder="🍛"
                                        maxLength={2}
                                        value={form.image}
                                        onChange={(e) => setForm({ ...form, image: e.target.value })}
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
                                <button type="submit" className="btn-primary" disabled={isSubmitting}>
                                    {isSubmitting ? "Saving…" : editId ? "Save Changes" : "Add Product"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
