# CineVerse Production Deployment & Verification Checklist

## Pre-Deployment Verification ✅

- [x] **Backend test suite**: 396 tests passing across all test files (0 failures, 2 skipped)
- [x] **Scout Accuracy Evaluation Suite**: 65/65 passing (100% hard-constraint compliance, multi-genre, regional cinema, conversational context)
- [x] **Frontend production build**: Vite compilation clean (`✓ built in ~1.85s`, 0 errors)
- [x] **API key & sensitive data security**: Zero sensitive keys in Git or client bundles; sanitized 500 error handlers
- [x] **Gemini model verified**: Standardized on Google `gemini-2.5-flash` with deterministic rule-based fallback
- [x] **Cross-platform compatibility**: Clean imports without OS-specific paths; Starlette/FastAPI compatibility shim active

---

## Changes & Architectural Improvements Summary

### 1. Stability & Compatibility Layer
- **Starlette / FastAPI Compatibility (`backend/compat.py`)**: Shimmed `Router.__init__` for `on_startup` keyword arguments and normalized `Starlette.max_body_size = None` to ensure zero startup crashes on modern Starlette 1.8.0 / FastAPI 0.115.0 stacks.
- **Dynamic CORS Parsing (`backend/config.py`)**: Automatic parsing of comma-separated or JSON list environment variables for `ALLOWED_ORIGINS`.
- **Sanitized Exception Handlers**: Hardened `/api/movies/`, `/api/series/`, `/api/search/`, and `/api/recommendations/` to prevent external API key leakage or internal tracebacks on HTTP 500.

### 2. Scout Conversational AI & Recommendation Pipeline
- **Deterministic Offline Fallback**: Fully functional intent parser and rule-based candidate filtering when `GEMINI_API_KEY` is unset or rate-limited.
- **Strict Negative Constraints**: Zero-tolerance hard constraint enforcement (`never`, `no horror`, `skip comedy`, `without gore`).
- **Regional Indian Cinema Support**: Direct extraction and filtering for Tamil (`ta`), Telugu (`te`), Malayalam (`ml`), Hindi (`hi`), Korean (`ko`), Japanese (`ja`), Spanish (`es`), French (`fr`).
- **Creator & Director Recognition**: Direct factual routing for director/creator queries (e.g., "who directed Oppenheimer" -> Christopher Nolan) with zero hallucinated recommendations.
- **Catalog Grounding & Provenance**: TMDB vote count, average rating, and story quotes displayed in selection analysis panels.
- **Similar Title Mapping**: Semantic mapping for queries like *"films like Parasite"* or *"movies like Interstellar"*.

### 3. Frontend UX & Reactivity
- **Watchlist Reactivity**: `PosterCard` and `HomePage` Hero CTA reactively reflect local storage changes via `watchlistUpdated` events.
- **Single Page Application Navigation**: Cast cards on `DetailPage` use React Router `<Link>` components instead of full-page reloads.
- **Scout UI Polishing**:
  - Live engine status pill ("AI Active" vs "Deterministic Mode").
  - Shimmer loading skeletons during recommendation retrieval.
  - Interactive retry button for failed queries.
  - Contextual quick-refinement pills (*"Under 2 hours"*, *"No horror"*, *"Try again"*, *"Surprise me"*).
- **Brand Assets**: Custom SVG favicon (`frontend/public/favicon.svg`) resolving 404 console errors.

---

## Deployment Steps

### 1. Backend Deployment

```bash
# Navigate to backend directory
cd backend

# Create and activate Python virtual environment
python -m venv venv
# On Linux/macOS:
source venv/bin/activate
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Install required dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env to set TMDB_API_KEY and GEMINI_API_KEY (optional, fallback mode works offline)

# Run full automated test suite to verify stability
python -m pytest

# Run Scout accuracy evaluation suite specifically
python -m pytest tests/test_scout_accuracy_eval.py -v

# Start production server (example with Uvicorn)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 2. Frontend Deployment

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Build optimized production bundle
npm run build

# Deploy the generated dist/ folder to your hosting provider:
# - Vercel / Netlify / Cloudflare Pages
# - Nginx / Apache web root: cp -r dist/* /var/www/html/
# - Docker / Node static server: npx serve -s dist -p 5173
```

---

## Post-Deployment Verification

### 1. Backend Health Check
```bash
curl http://localhost:8000/health
# Verify {"status": "healthy"}

curl http://localhost:8000/api/scout/health
# Verify Scout status and configured Gemini model (gemini-2.5-flash)
```

### 2. Frontend & Chatbot Verification in Browser
- [ ] Open application at configured URL; verify favicon displays in tab bar.
- [ ] Verify trending, popular movies, and series rows populate.
- [ ] Test Watchlist: Click "+ Watchlist" on Hero banner and on Poster cards; verify counter and button state sync instantly.
- [ ] Click a cast member card on any Movie/Series detail page; verify instantaneous client-side navigation to `/person/:id` without full page reload.
- [ ] Open Scout drawer ("Ask Scout"):
  - [ ] Check engine status pill in the drawer header ("AI Active" or "Deterministic Mode").
  - [ ] Click a conversation starter pill (e.g., *"Find something fun for tonight"*).
  - [ ] Verify loading skeletons appear while recommendations are fetched.
  - [ ] Verify recommendations appear with "View Analysis" accordion detailing TMDB consensus, story focus, and active constraints.
  - [ ] Click a quick refinement pill (e.g., *"Under 2 hours"* or *"No horror"*) and confirm negative constraint filtering.
