import { useState, useRef } from "react";
import { useApiFetch } from "../hooks/useApiFetch";
import { Send, Bot, User, Loader2, Paperclip, X, FileText, RefreshCw, Code } from "lucide-react";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  data?: any;
  type?: "action" | "text";
  attachmentName?: string;
  client_response_json?: any;
  system_action_json?: any;
}

export default function WhatsAppPage() {
  const apiFetch = useApiFetch();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "👋 Hi! I'm your AI invoice assistant. Send me a message like:\n\n\"Order 5 Curry Puffs\"\n\nor attach a receipt/supplier invoice for autonomous processing!",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [isAnalyzingMedia, setIsAnalyzingMedia] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [activeJsonIndex, setActiveJsonIndex] = useState<number | null>(null);

  async function handleResetSession() {
    if (!window.confirm("Are you sure you want to reset the AI memory for this session?")) return;
    try {
      await apiFetch("/api/whatsapp/unified/session?sender_phone=web-ui-unified", {
        method: "DELETE"
      });
      setMessages([
        {
          role: "assistant",
          content: "🔄 Session memory cleared! How can I help you today?",
        },
      ]);
      setActiveJsonIndex(null);
    } catch (err: any) {
      alert("Failed to reset session: " + err.message);
    }
  }

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

      const clientJson = {
        status: res.status,
        reply: reply
      };

      const systemJson = { ...res };
      delete systemJson.reply;
      delete systemJson.status;

      const newMessageIndex = messages.length + 1; // +1 because we just added the user message optimistically

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: reply,
          data: res,
          type: res.action_type || "text",
          client_response_json: clientJson,
          system_action_json: systemJson
        },
      ]);

      setActiveJsonIndex(newMessageIndex);

    } catch (err: Error | any) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `❌ Error: ${err.message}` },
      ]);
    }
    setLoading(false);
    setIsAnalyzingMedia(false);
  }

  const activeJsonData = activeJsonIndex !== null && messages[activeJsonIndex] ? {
    client_response_json: messages[activeJsonIndex].client_response_json,
    system_action_json: messages[activeJsonIndex].system_action_json
  } : null;

  return (
    <div className="page-container flex flex-col h-[calc(100vh-80px)] overflow-hidden bg-[#0A0A0A]">
      <div className="page-header flex-shrink-0">
        <div>
          <h1 className="page-title">WhatsApp Simulator</h1>
          <p className="page-subtitle">
            "The Sandbox": Test workflows and inspect internal AI payload decisions safely.
          </p>
        </div>
        <button className="btn-secondary text-red-400 hover:text-red-300 border-red-900 hover:bg-red-950" onClick={handleResetSession}>
          <RefreshCw size={14} />
          Reset Session
        </button>
      </div>

      <div className="flex-1 min-h-0 flex gap-6 mt-4">
        {/* LEFT PANE: Chat */}
        <div className="chat-container flex flex-col flex-1 min-w-0 border border-white/10 rounded-xl overflow-hidden bg-[#111]">
          <div className="p-3 border-b border-white/10 bg-[#161616] flex items-center gap-2">
            <Bot size={16} className="text-[#0070f3]" />
            <span className="text-sm font-medium">WhatsApp Interface</span>
          </div>

          <div className="chat-messages flex-1 overflow-y-auto p-4">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`chat-message ${msg.role}`}
              >
                <div className="chat-avatar">
                  {msg.role === "assistant" ? (
                    <Bot size={16} />
                  ) : (
                    <User size={16} />
                  )}
                </div>
                <div
                  className={`chat-bubble cursor-pointer transition-colors ${activeJsonIndex === i ? 'ring-2 ring-[#0070f3] bg-[#1a1a1a]' : ''}`}
                  onClick={() => {
                    if (msg.role === "assistant" && msg.client_response_json) {
                      setActiveJsonIndex(i);
                    }
                  }}
                >
                  {msg.attachmentName && (
                    <div className="chat-attachment-preview mb-2 p-2 bg-black/50 rounded flex items-center gap-2">
                      <FileText size={16} />
                      <span className="text-sm truncate opacity-80">{msg.attachmentName}</span>
                    </div>
                  )}
                  {msg.content && <pre className="chat-text whitespace-pre-wrap font-sans text-sm">{msg.content}</pre>}

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
                  <span className="chat-typing text-sm">
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
                  className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-0.5 shadow-md"
                  onClick={() => setSelectedFile(null)}
                >
                  <X size={12} />
                </button>
              </div>
              <span className="text-sm text-gray-300 truncate max-w-[200px]">{selectedFile.name}</span>
            </div>
          )}

          <form className="chat-input-bar relative flex items-center p-3 border-t border-white/10 bg-[#111]" onSubmit={handleSend}>
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
              className="p-2 text-gray-400 hover:text-white transition-colors flex-shrink-0"
              onClick={() => fileInputRef.current?.click()}
              disabled={loading}
            >
              <Paperclip size={20} />
            </button>

            <input
              className="chat-input ml-2 flex-1 text-gray-900"
              placeholder="Type a message or attach a receipt/invoice…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
            />
            <button
              type="submit"
              className="w-8 h-8 rounded-full bg-[#0070f3] flex items-center justify-center text-white ml-2 flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#0060df] transition-colors"
              disabled={loading || (!input.trim() && !selectedFile)}
            >
              <Send size={14} className="ml-0.5" />
            </button>
          </form>
        </div>

        {/* RIGHT PANE: JSON Inspector */}
        <div className="flex-1 min-w-0 border border-white/10 rounded-xl overflow-hidden bg-[#111] flex flex-col">
          <div className="p-3 border-b border-white/10 bg-[#161616] flex items-center gap-2">
            <Code size={16} className="text-gray-400" />
            <span className="text-sm font-medium">JSON Payload Inspector</span>
          </div>
          <div className="flex-1 overflow-y-auto p-4 bg-[#0d0d0d]">
            {activeJsonData ? (
              <div className="space-y-6">
                <div>
                  <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">1. client_response_json</h3>
                  <pre className="text-xs text-[#56b6c2] bg-black p-4 rounded-md overflow-x-auto border border-white/5 font-mono shadow-inner">
                    {JSON.stringify(activeJsonData.client_response_json, null, 2)}
                  </pre>
                </div>
                <div>
                  <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">2. system_action_json</h3>
                  <pre className="text-xs text-[#98c379] bg-black p-4 rounded-md overflow-x-auto border border-white/5 font-mono shadow-inner">
                    {JSON.stringify(activeJsonData.system_action_json, null, 2)}
                  </pre>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-gray-500 opacity-50 space-y-3">
                <Code size={32} />
                <p className="text-sm">Click an AI response bubble to inspect its payload.</p>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
