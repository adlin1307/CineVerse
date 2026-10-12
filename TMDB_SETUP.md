# TMDB API Setup Instructions

## Quick Summary
CineVerse currently runs with **mock data** (8 movies, 5 series). To access **thousands of real movies and series with posters, backdrops, and complete metadata**, you need a free TMDB API key.

## Current Status
- ✅ Backend running on http://localhost:8000
- ✅ Frontend running on http://localhost:5173
- ✅ Mock data service active (working perfectly for testing)
- ⚠️ TMDB API: **Not configured** (need API key)

## How to Get a TMDB API Key (Free)

### Step 1: Create TMDB Account
1. Go to https://www.themoviedb.org
2. Click **"Join TMDB"** in the top right
3. Sign up with your email address
4. Check your email and verify your account

### Step 2: Request API Key
1. Log in to your TMDB account
2. Click on your profile icon (top right)
3. Go to **Settings**
4. In the left sidebar, click **API**
5. Click **"Create"** or **"Request an API Key"**
6. Choose **"Developer"** (for non-commercial/educational use)
7. Accept the Terms of Use
8. Fill out the form:
   - **Application Name**: CineVerse (or any name)
   - **Application URL**: http://localhost:5173 (or your deployment URL)
   - **Application Summary**: College microproject for movie discovery
9. Submit the form

### Step 3: Get Your API Key
After submission, you'll see two keys:
- **API Key (v3 auth)**: A 32-character string like `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`
- **API Read Access Token (v4 auth)**: A longer JWT token starting with `eyJ...`

**Important**: For this project, we need the **API Key (v3 auth)** — the 32-character string.

### Step 4: Configure CineVerse Backend

1. Open the backend `.env` file:
   ```bash
   cd /Users/adlin/Desktop/MOVIEE/backend
   open .env  # or use your text editor
   ```

2. Replace the placeholder with your actual API key:
   ```bash
   # Before:
   TMDB_API_KEY=your_api_key_here
   
   # After:
   TMDB_API_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
   ```
   (Use your actual key, not this example!)

3. Save the file

4. Restart the backend server:
   ```bash
   # Stop the current backend (Ctrl+C in the backend terminal)
   # Then restart:
   cd /Users/adlin/Desktop/MOVIEE/backend
   source venv/bin/activate
   python main.py
   ```

### Step 5: Verify Configuration

Test the backend health check:
```bash
curl http://localhost:8000/health
```

You should see:
```json
{
  "status": "healthy",
  "tmdb_configured": true,  ← Should be true now!
  "database": "connected"
}
```

### Step 6: Enjoy Real Data!

1. Refresh your browser at http://localhost:5173
2. You'll now see:
   - Real movie and series posters
   - Thousands of titles from TMDB
   - Complete cast and crew information
   - Trailers (when available)
   - Accurate ratings and popularity
   - Real-time search across all TMDB content

## What Changes When TMDB is Configured?

### Before (Mock Data):
- 8 sample movies
- 5 sample series
- No poster/backdrop images (shows placeholders)
- Limited search results
- Fictional cast and crew

### After (Real TMDB Data):
- 500,000+ movies
- 150,000+ TV series
- High-quality poster and backdrop images
- Comprehensive search
- Real cast, crew, and production information
- Ratings from millions of TMDB users
- Release dates, runtime, genres, and more

## Troubleshooting

### "tmdb_configured": false after adding key

**Check 1**: Ensure you copied the entire API key (32 characters)
```bash
# In backend/.env, the key should look like:
TMDB_API_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

**Check 2**: No extra spaces or quotes
```bash
# ❌ Wrong:
TMDB_API_KEY= a1b2c3d4...
TMDB_API_KEY="a1b2c3d4..."

# ✅ Correct:
TMDB_API_KEY=a1b2c3d4...
```

**Check 3**: Restart the backend server after changing .env

### API Error: 401 Unauthorized

Your API key is invalid or expired:
1. Go back to TMDB Settings → API
2. Verify your key is still active
3. If needed, regenerate the key
4. Update `.env` with the new key

### API Error: 429 Too Many Requests

You've exceeded TMDB's rate limit (40 requests per 10 seconds for free tier):
- Wait 10 seconds and try again
- This is normal during heavy testing
- The app handles this gracefully

### Images Still Not Showing

If you've configured TMDB but images don't load:

**Check 1**: Verify TMDB is actually configured
```bash
curl http://localhost:8000/health
# Should show "tmdb_configured": true
```

**Check 2**: Test image URLs manually
```bash
# Get a movie with poster
curl http://localhost:8000/api/movies/popular | jq '.results[0].poster_path'

# If you get a path like "/abc123.jpg", the full URL is:
# https://image.tmdb.org/t/p/w500/abc123.jpg
```

**Check 3**: Check browser console for image loading errors

## API Usage Limits

TMDB's free API tier includes:
- ✅ 40 requests per 10 seconds
- ✅ Unlimited daily requests
- ✅ Access to all public data
- ✅ Commercial use allowed (with attribution)

This is more than enough for development and personal use!

## TMDB Attribution

When using real TMDB data, you must:
1. Include TMDB attribution in your UI
2. Display: "This product uses the TMDB API but is not endorsed or certified by TMDB"
3. Link to https://www.themoviedb.org

The frontend will automatically handle this when TMDB is configured.

## Security Notes

✅ **API Key Security**:
- The `.env` file is already in `.gitignore`
- Never commit your API key to version control
- Never expose the key in frontend code
- Our backend properly keeps the key server-side

✅ **Safe to Share**:
- TMDB API keys are tied to your account
- They can be regenerated if compromised
- Rate limits prevent abuse

## Still Using Mock Data?

If you prefer to continue with mock data for now:
- ✅ All features work with mock data
- ✅ Search, browse, details, watchlist all functional
- ✅ Perfect for testing and development
- ⚠️ No real posters/backdrops (placeholders instead)
- ⚠️ Limited to 13 titles

You can add the TMDB API key anytime to switch to real data!

## Need Help?

Check these resources:
- TMDB API Docs: https://developers.themoviedb.org/3
- TMDB API Settings: https://www.themoviedb.org/settings/api
- API Status: https://status.themoviedb.org

## Quick Reference

```bash
# Check TMDB status
curl http://localhost:8000/health

# Test popular movies
curl http://localhost:8000/api/movies/popular

# Test search
curl "http://localhost:8000/api/search/multi?query=inception"

# View API documentation
open http://localhost:8000/docs
```
