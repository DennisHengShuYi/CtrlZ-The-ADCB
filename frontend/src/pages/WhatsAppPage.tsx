import { useState } from "react";
import { useApiFetch } from "../hooks/useApiFetch";
import { Send, Bot, User, Loader2 } from "lucide-react";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  data?: any;
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

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);

    try {
      const res = await apiFetch("/api/whatsapp/webhook", {
        method: "POST",
        body: JSON.stringify({ phone_number: "web-ui", message: userMsg }),
      });

      let reply = "";
      if (res.status === "complete") {
        reply = `✅ ${res.message}\n\nInvoice #: ${res.invoice?.invoice_number || "N/A"}\nTotal: $${parseFloat(res.invoice?.total_amount || 0).toFixed(2)}`;
      } else if (res.status === "incomplete") {
        reply = `🔍 I need a bit more info:\n\n${(res.questions || []).map((q: string, i: number) => `${i + 1}. ${q}`).join("\n")}`;
      } else if (res.status === "client_not_found") {
        reply = `⚠️ ${res.message}`;
      } else {
        reply = `❌ ${res.message || "Something went wrong."}`;
      }

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: reply, data: res },
      ]);
    } catch (err: Error | any) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `❌ Error: ${err.message}` },
      ]);
    }
    setLoading(false);
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
                <pre className="chat-text">{msg.content}</pre>
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
                <span className="chat-typing">Thinking…</span>
              </div>
            </div>
          )}
        </div>

        <form className="chat-input-bar" onSubmit={handleSend}>
          <input
            className="chat-input"
            placeholder="Type a message… e.g. 'Invoice ABC Corp 10 widgets at $50'"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            className="btn-primary chat-send-btn"
            disabled={loading || !input.trim()}
          >
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
}
