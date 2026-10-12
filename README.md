# CineVerse — AI-Powered Movie & Series Discovery Platform

A visually stunning, modern movie and television series discovery platform combining the browsing experience of streaming services with detailed information and an intelligent AI companion.

## Project Structure

```
MOVIEE/
├── frontend/          # React + Vite frontend
├── backend/           # Python + FastAPI backend
└── README.md
```

## Tech Stack

### Frontend
- React 18
- Vite
- React Router
- CSS Modules

### Backend
- Python 3.9+
- FastAPI
- TMDB API integration
- SQLite (development)

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.9+
- TMDB API Key (get from https://www.themoviedb.org/settings/api)

### Setup

1. **Backend Setup**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
cp .env.example .env
# Add your TMDB API key to .env
python main.py
```

Backend runs on http://localhost:8000

2. **Frontend Setup**
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend runs on http://localhost:5173

## Environment Variables

### Backend (.env)
```
TMDB_API_KEY=your_api_key_here
TMDB_BASE_URL=https://api.themoviedb.org/3
DATABASE_URL=sqlite:///./cineverse.db
```

### Frontend (.env)
```
VITE_API_BASE_URL=http://localhost:8000
```

## Development Workflow

Build features end-to-end:
1. Create backend endpoint
2. Build frontend component
3. Connect and test
4. Iterate

## Features

### Phase 1 (Current)
- [x] Project structure
- [x] Backend health check
- [x] TMDB integration service (ready, needs API key)
- [x] Homepage with featured content
- [x] Movies/Series browsing
- [x] Search and filters
- [x] Search results page
- [x] Detail pages
- [x] Watchlist
- [ ] AI chat interface foundation

### Phase 2 (Future)
- Story Universe connections
- Hidden-Gem Detective
- Group Movie Picker
- Personal Cinema Journal
- Advanced recommendation engine

## API Attribution

This project uses the TMDB API but is not endorsed or certified by TMDB.
