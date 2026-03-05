import { useState, useRef } from "react";
import { useApiFetch } from "../hooks/useApiFetch";
import { Send, Bot, User, Loader2, Paperclip, X, FileText } from "lucide-react";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  data?: any;
  type?: "action" | "text";
  attachmentName?: string;
}

export default function WhatsAppPage() {
  const apiFetch = useApiFetch();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "👋 Hi! I'm your AI invoice assistant. Send me a message like:\n\n\"Create an invoice for ABC Corp for 5 laptops at $1,000 each\"\n\nand I'll extract the details and create it for you!",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [isAnalyzingMedia, setIsAnalyzingMedia] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if ((!input.trim() && !selectedFile) || loading) return;

    const userMsg = input.trim();
    const fileToSend = selectedFile;

    setInput("");
    setSelectedFile(null);
    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        content: userMsg,
        type: "text",
        attachmentName: fileToSend?.name
      },
    ]);
    setLoading(true);
    setIsAnalyzingMedia(!!fileToSend);

    try {
      const formData = new FormData();
      formData.append("message", userMsg);
      formData.append("sender_phone", "web-ui-unified");
      if (fileToSend) {
        formData.append("file", fileToSend);
      }

      const res = await apiFetch("/api/whatsapp/unified", {
        method: "POST",
        body: formData,
      });

      let reply = res.reply || "";
      if (res.status === "incomplete") {
        reply = `🔍 I need a bit more info:\n\n${(res.questions || []).map((q: string, i: number) => `${i + 1}. ${q}`).join("\n")}`;
      } else if (res.status === "client_not_found") {
        reply = `⚠️ ${res.message}`;
      } else if (res.status === "error") {
        reply = `❌ ${res.message || "Something went wrong."}`;
      }

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: reply, data: res, type: res.action_type || "text" },
      ]);
    } catch (err: Error | any) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `❌ Error: ${err.message}` },
      ]);
    }
    setLoading(false);
    setIsAnalyzingMedia(false);
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">WhatsApp Bot</h1>
          <p className="page-subtitle">
            Test the AI invoice assistant. Simulates the WhatsApp conversational
            flow.
          </p>
        </div>
      </div>

      <div className="chat-container">
        <div className="chat-messages">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`chat-message ${msg.role}`}
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <div className="chat-avatar">
                {msg.role === "assistant" ? (
                  <Bot size={16} />
                ) : (
                  <User size={16} />
                )}
              </div>
              <div className="chat-bubble">
                {msg.attachmentName && (
                  <div className="chat-attachment-preview mb-2 p-2 bg-black/10 rounded flex items-center gap-2">
                    <FileText size={16} />
                    <span className="text-sm truncate opacity-80">{msg.attachmentName}</span>
                  </div>
                )}
                {msg.content && <pre className="chat-text">{msg.content}</pre>}
                {msg.data && msg.data.action_type === "supplier_invoice_approved" && (
                  <div className="mt-2 p-3 bg-green-500/20 text-green-100 rounded-md border border-green-500/40">
                    <p className="text-sm font-bold">✅ Auto-Paid</p>
                    <p className="text-xs opacity-90 mt-1">Transaction Match: {msg.data.invoice_number}</p>
                  </div>
                )}
                {msg.data && msg.data.action_type === "supplier_invoice_negotiate" && (
                  <div className="mt-2 p-3 bg-yellow-500/20 text-yellow-100 rounded-md border border-yellow-500/40">
                    <p className="text-sm font-bold">⚠️ Budget Limit Reached</p>
                    <p className="text-xs opacity-90 mt-1">Sending counter-offer to Supplier...</p>
                  </div>
                )}
                {msg.data && msg.data.action_type === "receipt_matched" && (
                  <div className="mt-2 p-3 bg-green-500/20 text-green-100 rounded-md border border-green-500/40">
                    <p className="text-sm font-bold">✅ Receipt Matched</p>
                    <p className="text-xs opacity-90 mt-1">Invoice: {msg.data.invoice_number} Paid</p>
                  </div>
                )}
                {/* Legacy backward compatibility if needed */}
                {msg.data && msg.data.invoice_number && !msg.data.action_type && (
                  <div className="mt-2 p-3 bg-white/10 rounded-md border border-white/20">
                    <p className="text-sm font-semibold opacity-90">Transaction Match: {msg.data.invoice_number}</p>
                    <p className="text-xs opacity-75 mt-1">Status: Processed automatically ⚡</p>
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="chat-message assistant">
              <div className="chat-avatar">
                <Bot size={16} />
              </div>
              <div className="chat-bubble">
                <Loader2 size={16} className="chat-spinner" />
                <span className="chat-typing">
                  {isAnalyzingMedia ? "AI is analyzing supplier invoice... Matching with Cash Flow..." : "Thinking…"}
                </span>
              </div>
            </div>
          )}
        </div>

        {selectedFile && (
          <div className="px-4 py-2 border-t border-white/10 bg-[#161616] flex items-center gap-3">
            <div className="relative">
              <div className="w-12 h-12 bg-[#2a2a2a] rounded overflow-hidden flex items-center justify-center">
                {selectedFile.type.startsWith("image/") ? (
                  <img src={URL.createObjectURL(selectedFile)} alt="preview" className="w-full h-full object-cover" />
                ) : (
                  <FileText size={20} className="text-gray-400" />
                )}
              </div>
              <button
                type="button"
                className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-0.5"
                onClick={() => setSelectedFile(null)}
              >
                <X size={12} />
              </button>
            </div>
            <span className="text-sm text-gray-300 truncate max-w-[200px]">{selectedFile.name}</span>
          </div>
        )}

        <form className="chat-input-bar relative" onSubmit={handleSend}>
          <input
            type="file"
            className="hidden"
            ref={fileInputRef}
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                setSelectedFile(e.target.files[0]);
              }
            }}
          />
          <button
            type="button"
            className="p-2 text-gray-400 hover:text-white transition-colors"
            onClick={() => fileInputRef.current?.click()}
            disabled={loading}
          >
            <Paperclip size={20} />
          </button>

          <input
            className="chat-input ml-2"
            placeholder="Type a message or attach a receipt/invoice…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            className="btn-primary chat-send-btn ml-2"
            disabled={loading || (!input.trim() && !selectedFile)}
          >
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
}
