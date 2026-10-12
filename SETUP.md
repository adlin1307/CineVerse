# CineVerse Setup Guide

## Initial Setup

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# (Optional) Add your TMDB API key to .env
# Get one from https://www.themoviedb.org/settings/api
# Edit .env and replace 'your_api_key_here' with your actual key
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
source venv/bin/activate
python main.py
```

Backend will run on: http://localhost:8000
API Documentation: http://localhost:8000/docs

### Start Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

Frontend will run on: http://localhost:5173

## TMDB API Configuration

### Without API Key (Mock Data)
The application works perfectly with built-in mock data if you don't have a TMDB API key. The mock service provides:
- 8 diverse movies (various languages and genres)
- 5 diverse TV series
- Complete metadata including cast, crew, and recommendations
- Search functionality
- Genre filtering

### With API Key (Real Data)
To use real TMDB data:

1. Sign up at https://www.themoviedb.org
2. Go to Settings > API
3. Request an API key (free)
4. Add it to `backend/.env`:
   ```
   TMDB_API_KEY=your_actual_api_key_here
   ```
5. Restart the backend server

The application automatically switches between mock and real data based on API key configuration.

## Testing the Backend

### Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "tmdb_configured": false,  // true if API key is set
  "database": "connected"
}
```

### Test Endpoints
```bash
# Get popular movies
curl http://localhost:8000/api/movies/popular

# Get popular series
curl http://localhost:8000/api/series/popular

# Search
curl "http://localhost:8000/api/search/multi?query=seoul"

# Get trending
curl http://localhost:8000/api/search/trending
```

## Project Structure

```
MOVIEE/
├── backend/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration management
│   ├── routers/             # API route handlers
│   │   ├── movies.py
│   │   ├── series.py
│   │   └── search.py
│   ├── services/            # Business logic
│   │   ├── tmdb_service.py  # TMDB API integration
│   │   └── mock_service.py  # Mock data provider
│   ├── requirements.txt
│   ├── .env                 # Environment variables (create from .env.example)
│   └── venv/                # Python virtual environment
│
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable React components
│   │   │   ├── Navigation/
│   │   │   ├── SearchBar/
│   │   │   ├── PosterCard/
│   │   │   └── PosterRow/
│   │   ├── pages/           # Page components
│   │   │   ├── HomePage/
│   │   │   ├── MoviesPage/
│   │   │   ├── SeriesPage/
│   │   │   ├── DetailPage/
│   │   │   └── WatchlistPage/
│   │   ├── services/        # API and data services
│   │   │   ├── api.js       # Backend API client
│   │   │   └── watchlist.js # Watchlist management
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── index.css        # Global styles
│   │   └── App.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── .env                 # Environment variables (create from .env.example)
│   └── node_modules/
│
└── README.md
```

## Features Currently Implemented

### Homepage ✓
- Cinematic hero section with featured content
- Trending content row
- Popular movies row
- Popular series row
- Responsive design

### Movies Page ✓
- Grid view of movies
- Sort by popularity, rating, release date
- Filter by genre
- Load more pagination
- Responsive poster cards with watchlist functionality

### Series Page ✓
- Grid view of TV series
- Sort and filter options
- Same responsive design as movies page

### Detail Pages ✓
- Full movie/series information
- Cast with photos
- Production details
- Recommendations section
- Cinematic backdrop design
- Watchlist toggle

### Watchlist ✓
- Add/remove titles
- Persistent storage (localStorage)
- Empty state design
- Clear watchlist option

### Navigation ✓
- Responsive navigation bar
- Search bar
- Mobile-friendly menu
- Active route highlighting

### Design System ✓
- Deep charcoal/black backgrounds
- Champagne gold accents
- Cream text with hierarchy
- Smooth animations and transitions
- Cinematic aesthetic
- Mobile responsive throughout

## Next Steps

### Phase 1 Remaining
- [ ] Search results page
- [ ] AI chat interface (UI foundation)
- [ ] More robust error handling
- [ ] Loading skeletons

### Phase 2 (Future)
- [ ] User authentication
- [ ] Backend database for watchlist
- [ ] AI movie companion integration
- [ ] Story Universe feature
- [ ] Hidden-Gem Detective
- [ ] Group Movie Picker
- [ ] Personal Cinema Journal
- [ ] Advanced recommendation engine

## Development Tips

### Hot Reload
Both frontend and backend support hot reload:
- Backend: Uvicorn watches for file changes
- Frontend: Vite provides instant HMR

### API Documentation
FastAPI provides interactive API docs at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Debugging
- Backend logs appear in Terminal 1
- Frontend logs appear in browser console
- Network requests visible in browser DevTools

### Common Issues

**Backend won't start**
- Ensure virtual environment is activated
- Check Python version (3.9+)
- Verify all dependencies installed

**Frontend shows connection error**
- Ensure backend is running on port 8000
- Check VITE_API_BASE_URL in frontend/.env
- Verify CORS configuration in backend

**Mock data not showing**
- Check backend console for errors
- Verify health endpoint returns healthy status
- Clear browser cache

## Attribution

This project uses The Movie Database (TMDB) API. When using real TMDB data:
- Include TMDB attribution in your UI
- Follow TMDB's terms of service
- This product uses the TMDB API but is not endorsed or certified by TMDB

## License

This is a college microproject for educational purposes.
