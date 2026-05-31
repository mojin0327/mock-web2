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

```text
GET    /tasks       List tasks
POST   /tasks       Create a task
GET    /tasks/{id}  Get one task
PATCH  /tasks/{id}  Update a task
DELETE /tasks/{id}  Delete a task
```

## Environment Variables

Backend variables live in `backend/.env`:

```text
DATABASE_PATH=app.db
DATABASE_URL=
FRONTEND_ORIGINS=http://localhost:5173
```

`DATABASE_URL` is optional locally. When it is empty, the backend uses SQLite. When it is set to a PostgreSQL connection string, the backend uses PostgreSQL.

Frontend variables live in `frontend/.env`:

```text
VITE_API_URL=http://localhost:8000
```

Commit `.env.example` files, but do not commit real `.env` files.

## Deployment Notes

Recommended beginner deployment path:

1. Deploy `backend/` to Render, Railway, or another Python web service.
2. Set the backend start command:

```text
uvicorn main:app --host 0.0.0.0 --port $PORT
```

3. Set backend environment variables for a demo SQLite deployment:

```text
DATABASE_PATH=app.db
FRONTEND_ORIGINS=https://your-frontend-domain.example
```

On Vercel, use a writable temporary SQLite path if you keep SQLite:

```text
DATABASE_PATH=/tmp/app.db
```

This is only for demo deployments. Data stored in `/tmp` can disappear between function instances or redeploys.

4. Deploy `frontend/` to Vercel or another static frontend host.
5. If frontend and backend are deployed as Vercel Services in one project, set frontend environment variable:

```text
VITE_API_URL=/backend
```

SQLite is fine for this learning project, but production apps usually use PostgreSQL or another managed database.

For a PostgreSQL deployment, set this on the backend instead:

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
FRONTEND_ORIGINS=https://your-frontend-domain.example
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

The SQLite database file is generated locally when the backend starts.
