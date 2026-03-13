# FinanceFlow (Ctrl-Z) — SME Financial & Compliance Ecosystem

## 1. General Description

### What our project does
**FinanceFlow** is an advanced financial operating system designed for Small and Medium Enterprises (SMEs). It bridges the gap between daily operations and financial readiness by automating:
- **Smart Invoicing**: AI-powered classification and tracking of issuing/receiving invoices.
- **Fintech OS**: Real-time analytics for loan readiness, AI-generated CTOS credit reports, and automated business registration (SSM).
- **Compliance & Customs**: A specialized **Human-in-the-Loop (HITL)** system for precise Harmonized System (AHTN) tariff classification, ensuring cross-border trade compliance.
- **AI Integration**: Leverages Google Gemini for deep financial analysis and vector databases for high-speed tariff matching.

### SDG Addressed
- **Goal 8: Decent Work and Economic Growth** — FinanceFlow empowers SMEs (the backbone of the economy) by providing them with the financial transparency and creditworthiness data needed to access capital and grow sustainably.
- **Goal 9: Industry, Innovation and Infrastructure** — By modernizing financial reporting and regulatory compliance through AI, we contribute to a more resilient and inclusive industrial infrastructure.

### Target Users
- **SME Owners**: Business leaders looking to automate their back-office and improve their chances of securing funding.
- **Accounting & Compliance Teams**: Professionals who need high-accuracy tools for tax and tariff management.
- **Financial Institutions**: Banks and lenders looking for verified, AI-analyzed business performance data.

---

## 2. Setup Instructions

### Prerequisites
- **Node.js** v18+
- **Python** 3.10+
- **Supabase** (Database) & **Clerk** (Authentication)
- **Gemini API Key** (for AI analysis)

### Environment Configuration
Create a `.env` file in the root directory (refer to `.env.example`):
```env
# Clerk
VITE_CLERK_PUBLISHABLE_KEY=your_key
CLERK_SECRET_KEY=your_key

# Supabase
USE_SUPABASE=true
SUPABASE_URL=your_url
SUPABASE_SERVICE_ROLE_KEY=your_key

# AI
GEMINI_API_KEY=your_key
```

### Backend Setup
```bash
cd backend
python3 -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1 | macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python3 -m scripts.pillar2.build_ahtn_vector_db  # One-time tariff DB build
python3 -m app.main
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 3. How to Interact with Prototype

### Step-by-Step Guide for Judges

1.  **Dashboard Overview**: 
    - Log in to see the **Finance Dashboard**. 
    - Observe the **Cash on Hand**, **Expected Revenue**, and **Upcoming Bills** calculated dynamically from the ledger.
2.  **Fintech OS (The Core)**:
    - Navigate to **Fintech OS**.
    - **Readiness**: Adjust the "Proposed Loan" amount; watch the **Loan Readiness Score** update in real-time based on your debt-to-income ratios.
    - **AI CTOS**: Generate an AI-powered credit report that analyzes your business health using Gemini.
    - **Registry & Compliance**: View pre-filled SSM forms and tax compliance status (LHDN/EPF/SOCSO).
3.  **Cross-Border Compliance (HITL)**:
    - Go to **Invoice Pre-vet**.
    - Upload/Scan an invoice. The system uses a vector search to guess the HS/AHTN tariff codes.
    - If confidence is low, the item moves to the **HITL Review Center**.
    - Open the Review Center, verify the classification for flagged items, and **Approve** the record to update the financial ledger.
4.  **Bot Automation**:
    - Trigger the **WhatsApp Bot** (demonstration via backend logs or `/whatsapp` endpoint) to see how invoices can be submitted via chat.

### Test Cases
- **Scenario: Tariff Discrepancy**
    - **Action**: Upload an invoice with "Industrial Electronics".
    - **Expected Result**: System identifies it as high-risk/low-similarity; flags it for HITL.
    - **Follow-up**: User corrects the code in the Review Center; grand total updates with new duty rates.
- **Scenario: Loan Eligibility**
    - **Action**: Set proposed loan to RM 1,000,000.
    - **Expected Result**: Readiness score drops to "Red" (Unlikely), providing actionable insights on how to improve.
