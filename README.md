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
    │   └── main.py           # FastAPI app + routes
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
| `GET` | `/docs` | Public | FastAPI auto-generated docs (Swagger) |

---

## 🧪 Quick Verification

Once both servers are running:

1. Open **http://localhost:5173** — you should see the login page
2. Sign in with your Clerk credentials
3. You'll be redirected to the dashboard
4. Test the backend: `curl http://localhost:8000/` → `{"message":"Backend server is running!"}`
5. View API docs: **http://localhost:8000/docs**

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19, TypeScript, Vite 7, Tailwind CSS v4, Shadcn UI |
| **Backend** | Python 3.11+, FastAPI, Uvicorn, PyJWT |
| **Auth** | Clerk (React SDK + JWT verification) |
| **Styling** | Vercel-inspired theme (Geist font, white background) |

---

## 📝 Notes

- The single `.env` file at the project root is shared by both frontend and backend.
  - Vite reads it via `envDir: '../'` in `vite.config.ts`.
  - FastAPI reads it via `python-dotenv` in `config.py`.
- The `.env` file is **gitignored** — never commit real keys. Use `.env.example` as a template.
- The Clerk `Development mode` banner is normal during local development.
