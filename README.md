# CineVerse — AI-Powered Movie & Series Discovery Platform

A modern movie and television series discovery platform combining the browsing experience of streaming services with grounded recommendations and an intelligent AI assistant, **Scout**.

---

## Highlights

- **Intelligent Movie Assistant (Scout)**: Natural language conversational assistant powered by Google Gemini 2.5 Flash with deterministic fallback mode. Preserves 100% negative constraint compliance (*"no horror"*, *"skip comedy"*), parses regional Indian cinema (Tamil, Telugu, Malayalam, Hindi), supports semantic similarity (*"films like Parasite"*), and answers creator/director queries directly.
- **Grounding & Provenance**: Zero hallucinated titles. Every recommendation is scored and validated against TMDB catalog data, featuring structured selection analysis, TMDB rating consensus, and active constraints.
- **Offline Mock Engine**: Seamless local development without API keys. Built-in mock data for movies, TV series, search, genres, and cast/crew profiles.
- **Fast & Responsive Frontend**: Built with React 18 and Vite. Features reactive watchlist synchronization, Single Page Application routing, shimmer loading skeletons, interactive query retry, and contextual refinement pills.
- **Automated Verification**: Comprehensive test suite of **396 automated tests** (100% passing), including a dedicated 65-scenario Scout accuracy evaluation suite.

---

## Tech Stack

### Frontend
- **Framework**: React 18 + Vite
- **Routing**: React Router v6 (SPA client-side navigation)
- **Styling**: CSS Modules and Design Tokens (Charcoal & Champagne Gold palette)
- **State**: React Hooks + LocalStorage reactive event bus (`watchlistUpdated`)

### Backend
- **Framework**: FastAPI + Starlette (with compatibility layer for Starlette 1.8+)
- **Validation**: Pydantic v2
- **AI/LLM**: Google Gemini 2.5 Flash (`google-genai` SDK) with robust fallback
- **HTTP Client**: HTTPX with resilient connection timeouts and error sanitization
- **Catalog Integration**: TMDB API v3

---

## Quick Start

### 1. Backend Setup
```bash
cd backend
python -m venv venv
# Linux/macOS:
source venv/bin/activate
# Windows PowerShell:
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env
python main.py
```
Backend runs at `http://localhost:8000`. Interactive Swagger docs at `http://localhost:8000/docs`.

### 2. Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
Frontend runs at `http://localhost:5173`.

---

## Configuration (`backend/.env`)

```env
# TMDB API Configuration (Optional: mock data used if omitted)
TMDB_API_KEY=your_tmdb_api_key_here
TMDB_BASE_URL=https://api.themoviedb.org/3

# Gemini API Configuration (Optional: deterministic fallback used if omitted)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Server Settings
HOST=0.0.0.0
PORT=8000
```

---

## Testing & Quality Assurance

Run the test suite from the `backend/` directory:

```bash
# Run all 396 tests
python -m pytest

# Run the 65-test Scout Accuracy Benchmark
python -m pytest tests/test_scout_accuracy_eval.py -v
```

To build the frontend for production:

```bash
cd frontend
npm run build
```

---

## Project Structure

```
CineVerse/
├── backend/
│   ├── main.py              # Application entry point with Starlette lifespan
│   ├── config.py            # Configuration with dynamic CORS parsing
│   ├── compat.py            # Starlette 1.8+ / FastAPI compatibility layer
│   ├── routers/             # API routes (movies, series, search, people, scout)
│   ├── services/            # Intent parsing, state machine, TMDB, mock services
│   ├── tests/               # 396 automated pytest unit & integration tests
│   └── requirements.txt
├── frontend/
│   ├── src/                 # React components, pages, services, design system
│   ├── public/              # SVG favicon & static assets
│   ├── package.json
│   └── vite.config.js
├── README.md
├── SETUP.md
└── DEPLOYMENT_CHECKLIST.md
```
