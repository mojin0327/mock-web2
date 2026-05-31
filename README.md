# Mock Web2

React + FastAPI + Supabase Auth + PostgreSQL task management app for learning full-stack web development.

## Stack

- Frontend: React + Vite
- Backend: FastAPI
- Auth: Supabase Auth
- Database: PostgreSQL
- Version control: Git + GitHub

## Project Structure

```text
mock web2/
|-- backend/
|   |-- .env.example
|   |-- main.py
|   `-- requirements.txt
|-- frontend/
|   |-- .env.example
|   |-- index.html
|   |-- package.json
|   `-- src/
|       |-- main.jsx
|       `-- styles.css
|-- .gitignore
|-- LICENSE
`-- README.md
```

## Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn main:app --reload --port 8000
```

API docs:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/health
```

## Frontend Setup

Open a second terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

App:

```text
http://localhost:5173
```

## API

Task endpoints require a Supabase access token:

```text
Authorization: Bearer <supabase-access-token>
```

```text
GET    /tasks       List tasks
POST   /tasks       Create a task
GET    /tasks/{id}  Get one task
PATCH  /tasks/{id}  Update a task
DELETE /tasks/{id}  Delete a task
```

## Google Login

The frontend includes email/password login and Google OAuth login.

Enable Google in Supabase:

```text
Supabase Dashboard -> Authentication -> Providers -> Google
```

Google login needs an OAuth client ID and client secret from Google Cloud.
Set the Google OAuth callback URL to the Supabase callback URL shown in the Supabase Google provider settings.

## Environment Variables

Backend variables live in `backend/.env`:

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
FRONTEND_ORIGINS=http://localhost:5173
SUPABASE_URL=https://your-project.supabase.co
```

`DATABASE_URL` is required. The backend will not start without a PostgreSQL connection string.
`SUPABASE_URL` is required so the backend can verify Supabase Auth JWTs through the project's JWKS endpoint.

Frontend variables live in `frontend/.env`:

```text
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-supabase-anon-key
```

Commit `.env.example` files, but do not commit real `.env` files.
Never put a Supabase `service_role` key in frontend code.

## Deployment Notes

Recommended beginner deployment path:

1. Deploy `backend/` to Render, Railway, or another Python web service.
2. Set the backend start command:

```text
uvicorn main:app --host 0.0.0.0 --port $PORT
```

3. Set backend environment variables:

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
FRONTEND_ORIGINS=https://your-frontend-domain.example
SUPABASE_URL=https://your-project.supabase.co
```


4. Deploy `frontend/` to Vercel or another static frontend host.
5. If frontend and backend are deployed as Vercel Services in one project, set frontend environment variable:

```text
VITE_API_URL=/backend
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-supabase-anon-key
```


## Git Notes

These files are intentionally not committed:

- `backend/.venv/`
- `backend/app.db`
- `backend/__pycache__/`
- `backend/.env`
- `frontend/node_modules/`
- `frontend/dist/`
- `frontend/.env`

PostgreSQL data is stored in the database service configured by `DATABASE_URL`.
