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

## Git Notes

These files are intentionally not committed:

- `backend/.venv/`
- `backend/app.db`
- `backend/__pycache__/`
- `frontend/node_modules/`
- `frontend/dist/`
- `.env`

The SQLite database file is generated locally when the backend starts.