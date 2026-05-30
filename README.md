# Mock Web2

React + FastAPI + SQLite task management app for learning full-stack web development.

## Stack

- Frontend: React + Vite
- Backend: FastAPI
- Database: SQLite
- Version control: Git + GitHub

## Project Structure

```text
mock web2/
|-- backend/
|   |-- main.py
|   `-- requirements.txt
|-- frontend/
|   |-- index.html
|   |-- package.json
|   `-- src/
|       |-- main.jsx
|       `-- styles.css
|-- .env.example
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
npm run dev
```

App:

```text
http://localhost:5173
```

## API

```text
GET    /tasks       List tasks
POST   /tasks       Create a task
GET    /tasks/{id}  Get one task
PATCH  /tasks/{id}  Update a task
DELETE /tasks/{id}  Delete a task
```

## Environment Variables

Copy `.env.example` to `.env` when you start using real local configuration.

```powershell
Copy-Item .env.example .env
```

Current example:

```text
BACKEND_PORT=8000
FRONTEND_PORT=5173
DATABASE_PATH=app.db
```

The app works without `.env` because local defaults are built in.


## Deployment Notes

Recommended beginner deployment path:

1. Deploy `backend/` to Render, Railway, or another Python web service.
2. Set the backend start command:

```text
uvicorn main:app --host 0.0.0.0 --port $PORT
```

3. Set backend environment variables:

```text
DATABASE_PATH=app.db
FRONTEND_ORIGINS=https://your-frontend-domain.example
```

4. Deploy `frontend/` to Vercel or another static frontend host.
5. Set frontend environment variable:

```text
VITE_API_URL=https://your-backend-domain.example
```

SQLite is fine for this learning project, but production apps usually use PostgreSQL or another managed database.
## Git Notes

These files are intentionally not committed:

- `backend/.venv/`
- `backend/app.db`
- `backend/__pycache__/`
- `frontend/node_modules/`
- `frontend/dist/`
- `.env`

The SQLite database file is generated locally when the backend starts.