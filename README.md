# FinanceFlow (Ctrl-Z) — SME Financial & Compliance Ecosystem

## 1. General Description

### What our project does
FinanceFlow is an AI‑driven orchestration layer built on four pillars that transform how ASEAN's MSMEs interact with finance and trade. The Automated Performance Ledger captures sales and market interest directly from WhatsApp, Instagram, and payment platforms using Google Gemini for NLP, powering AI‑driven customer conversations that auto‑reply based on database records, with product details automatically extracted from Instagram captions to keep responses accurate and up‑to‑date. The Liability Shield combines Retrieval-Augmented Generation (RAG) with the official ASEAN Harmonized Tariff Nomenclature (AHTN) database and a Human-in-the-Loop (HITL) review system to ensure accurate cross‑border compliance. The Digital Formalization Bridge automates business registration with SSM and NIB once revenue thresholds are met. The Regional Capability Passport aggregates verified data into a Digital Maturity Index (DMI), a trust score recognised by ASEAN central banks that signals loan readiness, compliance health, and global trade capability to financial institutions. Powered by Google Gemini, OpenAI, and Supabase, FinanceFlow turns previously invisible businesses into verifiable, bankable entities ready for regional growth.

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

### Database Setup
FinanceFlow supports two modes: **Full Cloud (Supabase)** .

#### Supabase (Recommended for Production)
1. Create a new project on [Supabase](https://supabase.com/).
2. Open the **SQL Editor** in your Supabase dashboard.
3. Copy the content of `backend/supabase_full_setup.sql`.
4. Paste it into the SQL Editor and click **Run**.
5. Update your `.env` with your Supabase URL and Service Role Key.
6. Set `USE_SUPABASE=true`.



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
    - Log in to see the **Finance Dashboard & Social Media Dashboard**. 
    - Observe the **Cash on Hand**, **Expected Revenue**, and **Upcoming Bills** calculated automaticcaly from the ledger.
    - Social Media Dashboard will observe activities from Instagram and WhatsApp to predict what is the most welcomed product in the store
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
