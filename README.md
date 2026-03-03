# CtrlZ-The-ADCB

A full-stack web application with **React (Vite + TypeScript)** frontend and **Python (FastAPI)** backend, using **Clerk** for authentication.

---

## 📁 Project Structure

```
CtrlZ-The-ADCB/
├── .env.example          # Environment variables template
├── .env                  # Your local env (not committed)
├── .gitignore
├── README.md
│
├── frontend/             # React + Vite + TypeScript
│   ├── src/
│   │   ├── main.tsx          # Entry point (ClerkProvider + Router)
│   │   ├── App.tsx           # Route definitions
│   │   ├── index.css         # Global styles (Tailwind v4 + Vercel theme)
│   │   ├── lib/utils.ts      # Shadcn utility (cn function)
│   │   └── pages/
│   │       ├── LoginPage.tsx      # Clerk sign-in page
│   │       └── DashboardPage.tsx  # Protected dashboard
│   ├── components.json      # Shadcn UI config
│   ├── vite.config.ts       # Vite config (reads root .env)
│   ├── package.json
│   └── tsconfig.json
│
└── backend/              # Python + FastAPI
    ├── app/
    │   ├── __init__.py
    │   ├── config.py         # Loads root .env
    │   ├── auth.py           # Clerk JWT verification middleware
    │   ├── main.py           # FastAPI app + routes
    │   └── pillar2/          # Pillar 2: Liability Shield (invoice pre-vet, AHTN)
    │       ├── ahtn_search.py, ahtn_hints.py, query_expansion.py
    │       ├── invoice_prevet.py, schemas.py
    │       └── __init__.py
    ├── data/
    │   └── pillar2/          # AHTN vector DB + demo invoices
    │       ├── ahtn_embeddings.npy, ahtn_metadata.json
    │       ├── demo_invoice.json
    │       └── demo_invoices/
    ├── scripts/
    │   └── pillar2/          # Build & test scripts for Pillar 2
    │       ├── build_ahtn_vector_db.py
    │       ├── test_ahtn.py, test_prevet.py
    │       └── __init__.py
    └── requirements.txt
```

---

## 🚀 Getting Started

### Prerequisites

- **Node.js** v20+ and **npm** v10+
- **Python** 3.11+
- A **Clerk** account ([sign up here](https://clerk.com))

### 1. Clone the Repository

```bash
git clone https://github.com/DennisHengShuYi/CtrlZ-The-ADCB.git
cd CtrlZ-The-ADCB
```

### 2. Set Up Environment Variables

```bash
cp .env.example .env
```

Open `.env` and fill in your Clerk credentials from the [Clerk Dashboard → API Keys](https://dashboard.clerk.com/last-active?path=api-keys):

```env
VITE_CLERK_PUBLISHABLE_KEY=pk_test_your_key_here
CLERK_SECRET_KEY=sk_test_your_key_here
CLERK_JWKS_URL=https://your-instance.clerk.accounts.dev/.well-known/jwks.json
PORT=8000
```

### 3. Install & Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will start at **http://localhost:5173**.

### 4. Install & Run the Backend

Open a **new terminal** and run:

```bash
cd backend
python3 -m venv venv
```

Activate the virtual environment:

| Shell | Command |
|-------|---------|
| bash / zsh | `source venv/bin/activate` |
| csh / tcsh | `source venv/bin/activate.csh` |
| fish | `source venv/bin/activate.fish` |
| Windows (cmd) | `venv\Scripts\activate.bat` |
| Windows (PowerShell) | `venv\Scripts\Activate.ps1` |

Then install dependencies and run:

```bash
pip install -r requirements.txt
python3 -m app.main
```

The backend will start at **http://localhost:8000**.

> **Tip:** You can also skip activation and run directly:
> ```bash
> ./venv/bin/python -m app.main
> ```

---

## 🔑 API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/` | Public | Health check |
| `GET` | `/api/protected` | Bearer JWT | Returns authenticated user ID |
| `POST` | `/api/invoice/pre-vet` | Public | Pre-vet invoice (AHTN RAG + LLM + tariff + HITL flags) |
| `GET` | `/docs` | Public | FastAPI auto-generated docs (Swagger) |

---

## 🧪 Quick Verification

Once both servers are running:

1. Open **http://localhost:5173** — you should see the login page
2. Sign in with your Clerk credentials
3. You'll be redirected to the dashboard
4. Click **Invoice Pre-vet** to upload a JSON invoice and get AHTN classification
5. Test the backend: `curl http://localhost:8000/` → `{"message":"Backend server is running!"}`
6. View API docs: **http://localhost:8000/docs**

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19, TypeScript, Vite 7, Tailwind CSS v4, Shadcn UI |
| **Backend** | Python 3.11+, FastAPI, Uvicorn, PyJWT |
| **Auth** | Clerk (React SDK + JWT verification) |
| **Styling** | Vercel-inspired theme (Geist font, white background) |

---

## 📦 AHTN Vector Database (RAG)

To build the vector DB from the AHTN Excel for HS code classification:

1. Add `OPENAI_API_KEY` to `.env`
2. Run:

```bash
cd backend
pip install -r requirements.txt
python -m scripts.pillar2.build_ahtn_vector_db
```

This produces `backend/data/pillar2/ahtn_embeddings.npy` and `backend/data/pillar2/ahtn_metadata.json`. Use `app.pillar2.ahtn_search.search_ahtn(query)` to retrieve matching AHTN codes.

**To improve Sim (similarity) scores:** The build script enriches AHTN text with chapter keywords (e.g. Ch 85 → "electrical phone smartphone"). Rebuild after changing `CHAPTER_KEYWORDS` in `build_ahtn_vector_db.py`. Query expansion in `query_expansion.py` also adds synonyms before search.

### Invoice pre-vet (Liability Shield)

Pre-vet an invoice against AHTN for HS code classification, tariff calculation, and HITL routing:

```bash
# Test with default demo invoice
python -m scripts.pillar2.test_prevet

# Test all demo invoices (food, electronics, medical, textiles, mixed)
python -m scripts.pillar2.test_prevet --all

# Test specific invoice
python -m scripts.pillar2.test_prevet demo_invoices/invoice_food_beverages.json

# Or POST to API
curl -X POST http://localhost:8000/api/invoice/pre-vet \
  -H "Content-Type: application/json" \
  -d @backend/data/pillar2/demo_invoice.json
```

**Demo invoices** in `backend/data/pillar2/demo_invoices/`:
- `invoice_food_beverages.json` — sugar, coffee, canned fruit (buyer: Indonesia → Halal flags)
- `invoice_electronics.json` — smartphone, headphones, cables
- `invoice_medical_supplies.json` — nitrile gloves, masks, paracetamol
- `invoice_mixed_goods.json` — knives, ceramic mugs, plastic containers, bamboo board
- `invoice_textiles.json` — blouses, jeans, blankets

**Comprehensive hints** in `app/pillar2/ahtn_hints.py` — 400+ product keywords mapped to HS chapters (01–97).

Flow: Schema validation → RAG (AHTN) → hints or LLM refiner → tariff calc → flags (e.g. Halal for Indonesia) → items with confidence < 75% flagged for Human-in-the-Loop.

---

## 📝 Notes

- The single `.env` file at the project root is shared by both frontend and backend.
  - Vite reads it via `envDir: '../'` in `vite.config.ts`.
  - FastAPI reads it via `python-dotenv` in `config.py`.
- The `.env` file is **gitignored** — never commit real keys. Use `.env.example` as a template.
- The Clerk `Development mode` banner is normal during local development.
