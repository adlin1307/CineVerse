# Scout Quick Start Guide

## Get Your CineVerse Chatbot Running in 3 Minutes

### Step 1: Get a Gemini API Key (30 seconds)

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Log in with any Google account
3. Click **"Create API Key"**
4. Copy the key (looks like: `AIzaSy...`)

**Free tier**: 60 requests/minute, plenty for testing and development.

---

### Step 2: Configure Backend (30 seconds)

Open `backend/.env` and add your key:

```bash
GEMINI_API_KEY=AIzaSy...your-actual-key-here...
```

Make sure `TMDB_API_KEY` is also configured (should already be set from Phase A).

---

### Step 3: Install & Start (2 minutes)

**Backend**:
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt  # Installs google-genai
python main.py
```

Backend starts on `http://localhost:8000`

**Frontend** (separate terminal):
```bash
cd frontend
npm install  # if you haven't already
npm run dev
```

Frontend starts on `http://localhost:5173`

---

### Step 4: Test Scout

1. Open http://localhost:5173
2. Click **"Ask Scout ✨"** in the top navigation
3. Try: *"Find something fun for tonight"*
4. Scout will ask if you want comedy or action
5. Reply: *"Action comedies"*
6. Watch Scout recommend real movies from TMDB!

---

## Example Conversations to Try

**Simple request**:
- "I want a thriller"
- "Something emotional"
- "Surprise me!"

**Refinement**:
- "Make it shorter" (adjusts runtime)
- "Something less popular" (finds hidden gems)
- "Try again" (different movies, same criteria)

**Exclusions**:
- "No horror this time"
- "Skip the sad stuff"
- "Nothing too long"

**Multi-turn**:
1. "I want a comedy"
2. "Make it under 90 minutes"
3. "Something recent"
4. "Try one more set"

Scout remembers context across the conversation!

---

## Troubleshooting

### "Scout is not configured"
- Check `backend/.env` has `GEMINI_API_KEY=...` (not the placeholder text)
- Restart the backend server
- Verify: `curl http://localhost:8000/api/scout/health`

### No recommendations appear
- Check browser console for errors
- Verify TMDB_API_KEY is also configured
- Try a simpler query: "action movies"

### Backend won't start
- Make sure port 8000 is available
- Check venv is activated: `which python` should show `backend/venv/bin/python`
- Verify all dependencies installed: `pip list | grep genai`

---

## What You Just Built

**Scout** is a conversational movie discovery AI powered by:
- **Gemini 3.8 Flash**: Google's latest language model for natural conversation
- **TMDB Catalog**: Real movie data, no hallucinations
- **CineVerse Recommendation Engine**: Intelligent ranking based on mood, occasion, runtime

**Distinctive personality**: Witty, cheeky, movie-obsessed (not generic customer support)

**Multi-turn context**: Scout remembers what you've said and refines preferences across the conversation.

**Centralized naming**: Change `CHATBOT_NAME` in `frontend/src/components/Scout/scoutConfig.js` to rename the entire chatbot.

---

## Next Steps

### Customize Scout's Personality

Edit `backend/services/scout_service.py` → `SCOUT_SYSTEM_INSTRUCTION`:
- Adjust tone (more formal, more casual, more nerdy)
- Add domain-specific knowledge (film festival recommendations, director styles)
- Change response length (currently 2-3 sentences)

### Change the Name

Edit `frontend/src/components/Scout/scoutConfig.js`:
```javascript
export const CHATBOT_NAME = 'MovieBot';  // Was 'Scout'
export const CHATBOT_ICON = '🎬';        // Was '✨'
```

Rebuild frontend:
```bash
cd frontend
npm run build
```

### Deploy to Production

1. Set `GEMINI_API_KEY` in production environment variables
2. Set `CORS allowed_origins` to your production domain (backend/config.py)
3. Build frontend: `npm run build`
4. Serve `frontend/dist` with your web server
5. Run backend with production ASGI server (uvicorn, gunicorn+uvicorn)

---

## Cost Estimates

**Free tier** (no credit card required):
- 60 requests/minute
- 1,500 requests/day
- Perfect for testing and small-scale use

**Paid tier** (if you need more):
- ~$0.0015 per 5-turn conversation
- $4.50/month for ~3,000 conversations
- $45/month for ~30,000 conversations

**Most student projects stay well within the free tier.**

---

## Support

- Full implementation details: `SCOUT_IMPLEMENTATION_REPORT.md`
- API documentation: http://localhost:8000/docs
- Test suite: `cd backend && pytest tests/test_scout*.py -v`
- Gemini API docs: https://ai.google.dev/gemini-api/docs

**Questions?** Check the troubleshooting guide in `SCOUT_IMPLEMENTATION_REPORT.md`
