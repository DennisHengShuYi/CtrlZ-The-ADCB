import React, { useState } from "react";
import { useApiFetch } from "../hooks/useApiFetch";
import { useAuth } from "@clerk/clerk-react";
import { UploadCloud, CheckCircle, FileText, XCircle, Eye } from "lucide-react";

export default function ReceiptScanPage() {
  const [file, setFile] = useState<File | null>(null);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [success, setSuccess] = useState(false);
  const [paymentId, setPaymentId] = useState<string | null>(null);
  const [verifiedInvoiceId, setVerifiedInvoiceId] = useState<string | null>(null);
  const { getToken } = useAuth();

  // Use raw fetch since we need to send multipart/form-data
  const authFetch = useApiFetch();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setResult(null);
      setError(null);
      setSuccess(false);
      setPaymentId(null);
      setVerifiedInvoiceId(null);
    }
  };

  const handleScan = async () => {
    if (!file) return;

    setScanning(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      // Wait 1 sec for UX
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // apiFetch already parses JSON and throws on non-ok responses
      const data = await authFetch("/api/payments/scan-receipt", {
        method: "POST",
        body: formData,
      });

      setResult(data);
    } catch (err: Error | any) {
      setError(err.message || "Failed to scan receipt. Please try again.");
    } finally {
      setScanning(false);
    }
  };

  const handleVerify = async (
    invoiceId: string,
    clientId: string,
    amount: string,
  ) => {
    setVerifying(true);
    setError(null);
    try {
      const payload = {
        invoice_id: invoiceId,
        client_id: clientId,
        amount: parseFloat(amount),
        date:
          result?.extracted_data?.transaction_date ||
          new Date().toISOString().split("T")[0],
        method: "Bank Transfer via AI OCR",
        currency: result?.extracted_data?.currency || "MYR",
        exchange_rate: 1.0,
      };

      // apiFetch already parses JSON and throws on non-ok responses
      const data = await authFetch("/api/payments/verify", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setPaymentId(data.payment.id);
      setVerifiedInvoiceId(invoiceId);
      setSuccess(true);
    } catch (err: Error | any) {
      setError(err.message || "Failed to verify transaction");
    } finally {
      setVerifying(false);
    }
  };

  async function handleDownloadReceipt() {
    if (!paymentId || !verifiedInvoiceId) return;
    const token = await getToken();
    const res = await fetch(`http://localhost:8000/api/payments/${paymentId}/pdf?invoice_id=${verifiedInvoiceId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return alert("Failed to download receipt.");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `receipt_${paymentId.substring(0, 8)}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleViewReceipt() {
    if (!paymentId || !verifiedInvoiceId) return;
    const token = await getToken();
    const res = await fetch(`http://localhost:8000/api/payments/${paymentId}/pdf?invoice_id=${verifiedInvoiceId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return alert("Failed to open receipt PDF.");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Receipt Scanner</h1>
        <p className="text-gray-500 mt-2">
          Upload a bank transfer or payment receipt to automatically match and
          clear invoices.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Column: Upload */}
        <div className="space-y-6">
          <div className="card text-center p-12 custom-border border-dashed">
            <UploadCloud className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium mb-2">Upload Receipt</h3>
            <p className="text-sm text-gray-500 mb-6">
              Drag and drop an image or click to browse
            </p>
            <input
              type="file"
              accept="image/*,application/pdf"
              className="hidden"
              id="receipt-upload"
              onChange={handleFileChange}
            />
            <label
              htmlFor="receipt-upload"
              className="btn btn-secondary cursor-pointer inline-flex items-center"
            >
              Select Image
            </label>

            {file && (
              <div className="mt-6 border border-[oklch(0.92_0_0)] rounded-lg overflow-hidden bg-gray-50 aspect-[3/4] flex items-center justify-center p-2 relative">
                {file.type === "application/pdf" ? (
                  <div className="flex flex-col items-center text-gray-500">
                    <FileText className="w-16 h-16 mb-2" />
                    <span className="text-sm font-medium">{file.name}</span>
                  </div>
                ) : (
                  <img
                    src={URL.createObjectURL(file)}
                    alt="Receipt Preview"
                    className="max-h-full max-w-full object-contain"
                  />
                )}
              </div>
            )}


          </div>

          <button
            onClick={handleScan}
            disabled={!file || scanning}
            className="btn btn-primary w-full py-3 h-auto"
          >
            {scanning ? "Scanning with AI..." : "Scan Receipt"}
          </button>

          {error && (
            <div className="p-4 bg-red-50 text-red-600 rounded-lg custom-border border-red-200 flex items-start gap-3">
              <XCircle className="w-5 h-5 shrink-0" />
              <p className="text-sm">{error}</p>
            </div>
          )}

          {success && (
            <div className="p-4 bg-green-50 text-green-700 rounded-lg custom-border border-green-200 flex items-start gap-3">
              <CheckCircle className="w-5 h-5 shrink-0" />
              <div>
                <p className="font-medium">Payment Verified Successfully</p>
                <p className="text-sm mt-1">
                  The invoice has been marked as paid.
                </p>
                <button
                  onClick={() => {
                    setFile(null);
                    setResult(null);
                    setSuccess(false);
                  }}
                  className="btn btn-secondary mt-4 text-sm mr-3"
                >
                  Scan Another
                </button>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleViewReceipt}
                    className="btn btn-secondary mt-4 text-sm flex items-center gap-2"
                  >
                    <Eye size={16} /> View
                  </button>
                  <button
                    onClick={handleDownloadReceipt}
                    className="btn btn-primary mt-4 text-sm"
                  >
                    Download Receipt
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Results */}
        <div className="space-y-6">
          {result && (
            <>
              {/* Extracted Data */}
              <div className="card">
                <h3 className="card-header pb-2 font-semibold flexItemsCenter gap-2 border-b mb-4">
                  <FileText className="w-4 h-4 text-gray-400" />
                  Extracted Information
                </h3>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Amount:</span>
                    <span className="font-medium font-mono">
                      {result.extracted_data.amount
                        ? `${result.extracted_data.currency || "MYR"} ${result.extracted_data.amount}`
                        : "N/A"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Reference:</span>
                    <span className="font-medium font-mono">
                      {result.extracted_data.reference_number || "N/A"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Date:</span>
                    <span className="font-medium">
                      {result.extracted_data.transaction_date || "N/A"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Sender:</span>
                    <span className="font-medium">
                      {result.extracted_data.sender_name || "N/A"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Suggestions */}
              <div className="card">
                <h3 className="card-header pb-2 font-semibold">
                  Suggested Matches
                </h3>
                <div className="mt-4 space-y-4">
                  {result.suggested_matches &&
                    result.suggested_matches.length > 0 ? (
                    result.suggested_matches.map((inv: any) => (
                      <div
                        key={inv.id}
                        className="p-4 custom-bg custom-border rounded-lg flex items-center justify-between"
                      >
                        <div>
                          <p className="font-medium text-gray-900">
                            {inv.invoice_number}
                          </p>
                          <p className="text-sm text-gray-500">
                            Balance: {inv.currency || "MYR"} {inv.total_amount} | Status: {inv.status}
                          </p>
                        </div>
                        <button
                          onClick={() =>
                            handleVerify(
                              inv.id,
                              inv.client_id,
                              result.extracted_data.amount || inv.total_amount,
                            )
                          }
                          disabled={verifying || success}
                          className="btn btn-primary text-sm px-4"
                        >
                          {verifying ? "Processing..." : "Verify Match"}
                        </button>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-gray-500 p-4 text-center border-dashed custom-border rounded-lg">
                      No matching unpaid invoices found.
                    </p>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
