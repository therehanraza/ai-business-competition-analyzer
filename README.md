# AI Business Competition Analyzer

A deployable competitive intelligence workspace built with Flask, MongoDB Atlas, Gemini, and a static HTML/CSS/JavaScript frontend.

The main showcase feature is the AI Competitor Intelligence Command Center. Add competitor websites/companies, enrich competitor profiles with AI, log pricing, traffic, funding, hiring, product launch, sentiment, and market-mention signals, then generate alerts, predictions, battlecards, strategic recommendations, reports, and natural-language copilot answers. If `GEMINI_API_KEY` is not configured, the app falls back to a local intelligence engine so the workflow still works.

## Features Completed

- SaaS-style dashboard with competitor, pricing, demand, alert, and recommendation views.
- Top-of-page AI competitor intelligence center with positive/negative developments, traffic trends, market mentions, top-watch signals, opportunities, and threats.
- Competitor activity tracking for traffic, funding, hiring, product launches, pricing, sentiment, and market mentions.
- Real-time generated alerts and likely-next-move predictions from growth and activity signals.
- AI copilot endpoint and UI for natural-language competitive-positioning questions.
- AI Company Discovery flow that enriches a competitor from a name/website and starts tracking the company with generated pricing, activity, and market signals.
- AI Battlecard Generator with Gemini support and rules-engine fallback.
- Battlecard history API with optional non-persistent previews.
- Competitor watchlist create flow.
- Price history logging and chart refresh.
- Market signal intake and regional demand chart.
- Alert intake, status updates, and open-alert tracking.
- Report brief creation, report history, and JSON export.
- Full backend CRUD for competitors, prices, market signals, alerts, reports, and battlecards.
- Backend unit tests against an isolated local JSON store.
- MongoDB Atlas support with local JSON fallback for development.
- Production CORS configuration through `ALLOWED_ORIGINS`.
- Render backend deployment config in `render.yaml`.
- Vercel frontend deployment config in `frontend/vercel.json`.
- Presentation-safe local intelligence mode when the deployed API route is unavailable, so charts, analyzer results, battlecards, reports, and intake workflows still work during reviews.

## Project Structure

```text
AI_Business_Competition_Analyzer/
  backend/
    app.py
    requirements.txt
    .env.example
  frontend/
    index.html
    styles.css
    app.js
    vercel.json
  render.yaml
  README.md
```

## Local Setup

Start the Flask API:

```powershell
cd "C:\Users\Rehan Raza\OneDrive\Desktop\AI_Business_Competition_Analyzer\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Start the frontend in a second terminal:

```powershell
cd "C:\Users\Rehan Raza\OneDrive\Desktop\AI_Business_Competition_Analyzer\frontend"
python -m http.server 5500
```

Open `http://127.0.0.1:5500`.

## Environment Variables

Backend variables:

```env
FLASK_ENV=production
FLASK_DEBUG=0
PORT=5000
MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=ai_business_competition_analyzer
LOCAL_DATA_PATH=
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_MODEL=gemini-flash-latest
ALLOWED_ORIGINS=https://your-vercel-domain.vercel.app,http://localhost:5500,http://127.0.0.1:5500
```

## Deploy Backend To Render

1. Push this repository to GitHub.
2. In Render, create a new Blueprint and select this repo.
3. Render will read `render.yaml`.
4. Add these secret environment variables when prompted:
   - `MONGODB_URI`
   - `GEMINI_API_KEY`
   - `ALLOWED_ORIGINS`
5. Deploy the service.

The expected backend URL is:

```text
https://ai-business-competition-analyzer-api.onrender.com
```

If you choose a different Render service name, update `frontend/vercel.json`.

## Deploy Frontend To Vercel

1. Create a Vercel project from the same GitHub repo.
2. Set the Vercel project root directory to `frontend`.
3. Confirm `frontend/vercel.json` points `/api/*` to your Render backend URL.
4. Deploy.
5. Add the Vercel production URL to the backend `ALLOWED_ORIGINS` value in Render.

## MongoDB Atlas Setup

1. Create an Atlas cluster.
2. Create a database user with read/write permissions.
3. Allow access from Render. For a quick review deployment, `0.0.0.0/0` works, but production should use tighter network access.
4. Copy the connection string into Render as `MONGODB_URI`.
5. Keep `MONGODB_DATABASE=ai_business_competition_analyzer`.

The backend seeds starter competitors, price history, market signals, and alerts when the MongoDB `competitors` collection is empty.

## API Endpoints

- `GET /api/health`
- `GET /api/dashboard`
- `GET /api/competitors`
- `POST /api/competitors`
- `GET /api/competitors/<competitor_id>`
- `PUT /api/competitors/<competitor_id>`
- `DELETE /api/competitors/<competitor_id>`
- `GET /api/prices`
- `GET /api/price-history`
- `POST /api/prices`
- `GET /api/prices/<price_id>`
- `PUT /api/prices/<price_id>`
- `DELETE /api/prices/<price_id>`
- `GET /api/market-signals`
- `POST /api/market-signals`
- `GET /api/market-signals/<signal_id>`
- `PUT /api/market-signals/<signal_id>`
- `DELETE /api/market-signals/<signal_id>`
- `GET /api/activity-signals`
- `POST /api/activity-signals`
- `GET /api/activity-signals/<signal_id>`
- `PUT /api/activity-signals/<signal_id>`
- `DELETE /api/activity-signals/<signal_id>`
- `POST /api/enrich-competitor`
- `POST /api/track-competitor`
- `GET /api/intelligence`
- `POST /api/copilot`
- `GET /api/alerts`
- `POST /api/alerts`
- `GET /api/alerts/<alert_id>`
- `PUT /api/alerts/<alert_id>`
- `PATCH /api/alerts/<alert_id>/status`
- `DELETE /api/alerts/<alert_id>`
- `GET /api/reports`
- `POST /api/reports`
- `GET /api/reports/<report_id>`
- `DELETE /api/reports/<report_id>`
- `GET /api/reports/<report_id>/export`
- `GET /api/recommendations`
- `POST /api/battlecard`
- `GET /api/battlecards`
- `POST /api/battlecards`
- `GET /api/battlecards/<battlecard_id>`
- `DELETE /api/battlecards/<battlecard_id>`

## Backend Tests

```powershell
cd "C:\Users\Rehan Raza\OneDrive\Desktop\AI_Business_Competition_Analyzer"
.\backend\.venv\Scripts\python.exe -m unittest discover -s backend -p "test_*.py" -v
```

## Production Notes

- The frontend uses `http://127.0.0.1:5000` only on localhost.
- In production, the frontend calls `/api`, and Vercel rewrites those calls to Render.
- If `/api` or the Render fallback is unavailable, the frontend automatically switches to local intelligence mode and labels the sidebar status as `Local Intelligence`.
- The backend still works without MongoDB, but Render's filesystem is ephemeral, so MongoDB Atlas is required for persistent production data.
- The app works without Gemini, but battlecards and recommendations use the rules engine until `GEMINI_API_KEY` is set.
