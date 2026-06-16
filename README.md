# AI Business Competition Analyzer

AI Business Competition Analyzer is a complete Flask + HTML/CSS/JavaScript SaaS-style competitive intelligence platform. It tracks competitors, pricing movement, product performance, market demand, alerts, reports, and AI recommendations powered by Google Gemini.

## Tech Stack

- Frontend: HTML, CSS, JavaScript, Chart.js
- Backend: Python, Flask
- Database: MongoDB Atlas, with a local JSON development fallback
- AI: Google Gemini API using `gemini-2.5-flash`
- Environment: `.env`
- Version Control: Git

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
  .gitignore
  README.md
```

## File Purposes

- `backend/app.py`: Complete Flask API with dashboard metrics, competitor CRUD, pricing history, market signals, alerts, reports, MongoDB Atlas support, local development storage, and Gemini recommendations.
- `backend/requirements.txt`: Python dependencies required to run the backend locally or on Render.
- `backend/.env.example`: Environment variable template for MongoDB Atlas, Gemini, Flask, and CORS settings.
- `frontend/index.html`: Single-page SaaS dashboard layout.
- `frontend/styles.css`: Responsive premium analytics UI styling.
- `frontend/app.js`: Frontend API integration, Chart.js rendering, form handling, recommendations, and health checks.
- `.gitignore`: Keeps secrets, virtual environments, caches, and generated local data out of Git.

## Local Setup

1. Open a terminal in this folder.
2. Create and activate a Python virtual environment.

```powershell
cd "C:\Users\Rehan Raza\Documents\AI_Business_Competition_Analyzer\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

3. Edit `backend/.env` and add your keys.

```env
MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=ai_business_competition_analyzer
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_MODEL=gemini-2.5-flash
```

4. Start the backend.

```powershell
python app.py
```

5. Open the frontend.

```powershell
cd "C:\Users\Rehan Raza\Documents\AI_Business_Competition_Analyzer\frontend"
python -m http.server 5500
```

Then visit `http://127.0.0.1:5500`.

## API Endpoints

- `GET /api/health`
- `GET /api/dashboard`
- `GET /api/competitors`
- `POST /api/competitors`
- `PUT /api/competitors/<competitor_id>`
- `DELETE /api/competitors/<competitor_id>`
- `POST /api/prices`
- `POST /api/market-signals`
- `POST /api/alerts`
- `POST /api/reports`
- `GET /api/recommendations`

## Deployment Notes

- Frontend can be deployed to Vercel as a static site from the `frontend` folder.
- Backend can be deployed to Render using `backend/app.py` and `backend/requirements.txt`.
- MongoDB Atlas should be connected through `MONGODB_URI`.
- Gemini should be connected through `GEMINI_API_KEY`.
