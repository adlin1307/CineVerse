# CineVerse Setup Guide

## Initial Setup

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
.\venv\Scripts\Activate.ps1  # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# (Optional) Add your TMDB API key and Gemini API key to .env:
# - TMDB API key: https://www.themoviedb.org/settings/api
# - Gemini API key: https://aistudio.google.com/
# Note: If no keys are provided, CineVerse automatically runs in offline
# mock mode for TMDB and deterministic rule-based mode for Scout AI.
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# The default configuration points to http://localhost:8000
# which is correct for local development
```

## Running the Application

### Start Backend (Terminal 1)

```bash
cd backend
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
python main.py
```

- Backend will run on: `http://localhost:8000`
- API Documentation (Swagger UI): `http://localhost:8000/docs`
- Scout Health Status: `http://localhost:8000/api/scout/health`

### Start Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

- Frontend will run on: `http://localhost:5173`

---

## Configuration & API Modes

### TMDB API Configuration
- **Without API Key (Mock Mode)**: The application works completely offline with built-in mock services providing rich mock movies, TV series, full person biographies, credits, search, and genre filtering.
- **With API Key (Real Data)**: Add your `TMDB_API_KEY` to `backend/.env`. The application automatically switches between mock and real data.

### Scout AI Assistant Configuration
- **Without Gemini API Key (Deterministic Fallback Mode)**: Scout functions deterministically using regex intent extraction, hard constraint parsing, regional Indian cinema recognition, runtime categorization, and direct TMDB recommendation scoring.
- **With Gemini API Key (AI Mode)**: Add `GEMINI_API_KEY=your_key` and `GEMINI_MODEL=gemini-2.5-flash` to `backend/.env`. Scout uses Gemini 2.5 Flash for nuanced natural language reasoning, conversational sentiment, and query parsing while keeping recommendations 100% grounded in verified catalog data.

---

## Running the Test Suite

CineVerse includes comprehensive test coverage across routing, recommendation engines, state machines, and Scout conversational accuracy:

```bash
cd backend

# Run the entire test suite (396 tests)
python -m pytest

# Run the 65-test Scout Accuracy Evaluation Suite specifically
python -m pytest tests/test_scout_accuracy_eval.py -v
```

---

## Project Structure

```
CineVerse/
├── backend/
│   ├── main.py              # FastAPI application entry point with Starlette lifespan
│   ├── config.py            # Configuration with dynamic CORS parsing
│   ├── compat.py            # Starlette 1.8+ / FastAPI compatibility layer
│   ├── routers/             # API route handlers
│   │   ├── movies.py
│   │   ├── series.py
│   │   ├── search.py
│   │   ├── people.py
│   │   ├── recommendations.py
│   │   └── scout.py         # Conversational discovery endpoint
│   ├── services/            # Business logic
│   │   ├── tmdb_service.py           # TMDB API integration
│   │   ├── mock_service.py           # Offline mock data provider
│   │   ├── recommendation_service.py # Core recommendation candidate search
│   │   ├── recommendation_engine.py  # Emotional mood ranking & scoring
│   │   ├── scout_service.py          # Scout conversational orchestrator
│   │   ├── intent_parser.py          # Hybrid LLM / rule-based intent extraction
│   │   └── conversation_state.py     # Multi-turn conversational state machine
│   ├── tests/               # 396+ automated unit & integration tests
│   │   └── test_scout_accuracy_eval.py # 65-test Scout accuracy benchmark
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable React components
│   │   │   ├── Navigation/
│   │   │   ├── PosterCard/  # Reactive watchlist cards
│   │   │   ├── PosterRow/
│   │   │   ├── Scout/       # Chatbot drawer with skeletons & retry
│   │   │   └── TrailerModal/
│   │   ├── pages/           # Page components
│   │   │   ├── HomePage/
│   │   │   ├── MoviesPage/
│   │   │   ├── SeriesPage/
│   │   │   ├── DetailPage/  # SPA cast navigation
│   │   │   ├── PersonPage/  # Actor/director filmography
│   │   │   ├── SearchPage/
│   │   │   └── WatchlistPage/
│   │   ├── services/        # API and client storage services
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── public/
│   │   └── favicon.svg      # CineVerse logo favicon
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
│
├── README.md
├── SETUP.md
└── DEPLOYMENT_CHECKLIST.md
```

---

## Production Build

To test or generate the frontend production assets:

```bash
cd frontend
npm run build
```

Bundle outputs are placed in `frontend/dist/`.
