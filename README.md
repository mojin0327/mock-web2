# Mock Web2

React + FastAPI + SQLite の学習用タスク管理アプリです。

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install fastapi "uvicorn[standard]"
uvicorn main:app --reload --port 8000
```

API docs:

```text
http://localhost:8000/docs
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

App:

```text
http://localhost:5173
```

## What This App Does

- `GET /tasks`: タスク一覧を取得
- `POST /tasks`: タスクを作成
- `GET /tasks/{id}`: タスク詳細を取得
- `PATCH /tasks/{id}`: タスクを更新
- `DELETE /tasks/{id}`: タスクを削除

SQLite の `backend/app.db` にデータを保存します。`app.db` はローカル実行時に作られるためGitには入れません。