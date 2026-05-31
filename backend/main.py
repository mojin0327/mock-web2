import os
from typing import Optional

import jwt
import psycopg
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jwt import PyJWKClient, PyJWTError
from psycopg.rows import dict_row
from pydantic import BaseModel

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required. Set it to your PostgreSQL connection string.")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_JWKS_URL = os.getenv("SUPABASE_JWKS_URL") or (
    f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json" if SUPABASE_URL else ""
)
SUPABASE_JWT_ISSUER = f"{SUPABASE_URL}/auth/v1" if SUPABASE_URL else None
supabase_jwks_client = PyJWKClient(SUPABASE_JWKS_URL) if SUPABASE_JWKS_URL else None

app = FastAPI(title="Mock Web2 API")

frontend_origins = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in frontend_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskCreate(BaseModel):
    title: str
    description: str = ""


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    done: Optional[bool] = None


def get_connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    if not supabase_jwks_client:
        raise HTTPException(status_code=500, detail="SUPABASE_URL or SUPABASE_JWKS_URL is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        signing_key = supabase_jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            issuer=SUPABASE_JWT_ISSUER,
        )
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid bearer token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token does not include a user id")
    return user_id


def init_db():
    with get_connection() as connection:
        connection.execute(
            """
            create table if not exists tasks (
                id serial primary key,
                user_id uuid not null,
                title text not null,
                description text not null default '',
                done boolean not null default false,
                created_at timestamptz not null default current_timestamp,
                updated_at timestamptz not null default current_timestamp
            )
            """
        )
        connection.execute("alter table tasks add column if not exists user_id uuid")
        connection.execute("create index if not exists idx_tasks_user_id on tasks(user_id)")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "database": "postgres",
        "auth": "jwks" if supabase_jwks_client else "missing",
        "redis": "skip",
    }


def task_to_dict(row):
    task = dict(row)
    task["done"] = bool(task["done"])
    return task


@app.get("/tasks")
def list_tasks(user_id: str = Depends(get_current_user_id)):
    with get_connection() as connection:
        rows = connection.execute(
            """
            select id, title, description, done, created_at, updated_at
            from tasks
            where user_id = %s
            order by id desc
            """,
            (user_id,),
        ).fetchall()
    return [task_to_dict(row) for row in rows]


@app.post("/tasks")
def create_task(payload: TaskCreate, user_id: str = Depends(get_current_user_id)):
    with get_connection() as connection:
        row = connection.execute(
            """
            insert into tasks (user_id, title, description)
            values (%s, %s, %s)
            returning id, title, description, done, created_at, updated_at
            """,
            (user_id, payload.title, payload.description),
        ).fetchone()
    return task_to_dict(row)


@app.get("/tasks/{task_id}")
def get_task(task_id: int, user_id: str = Depends(get_current_user_id)):
    with get_connection() as connection:
        row = connection.execute(
            """
            select id, title, description, done, created_at, updated_at
            from tasks
            where id = %s and user_id = %s
            """,
            (task_id, user_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_to_dict(row)


@app.patch("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskUpdate, user_id: str = Depends(get_current_user_id)):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return get_task(task_id, user_id)

    allowed_fields = {
        "title": updates.get("title"),
        "description": updates.get("description"),
        "done": updates.get("done"),
    }
    fields = [field for field in allowed_fields if field in updates]
    values = [allowed_fields[field] for field in fields]
    assignments = ", ".join([f"{field} = %s" for field in fields])

    with get_connection() as connection:
        existing = connection.execute(
            "select id from tasks where id = %s and user_id = %s",
            (task_id, user_id),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Task not found")

        connection.execute(
            f"update tasks set {assignments}, updated_at = current_timestamp where id = %s and user_id = %s",
            (*values, task_id, user_id),
        )
        row = connection.execute(
            """
            select id, title, description, done, created_at, updated_at
            from tasks
            where id = %s and user_id = %s
            """,
            (task_id, user_id),
        ).fetchone()
    return task_to_dict(row)


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, user_id: str = Depends(get_current_user_id)):
    with get_connection() as connection:
        row = connection.execute(
            """
            select id, title, description, done, created_at, updated_at
            from tasks
            where id = %s and user_id = %s
            """,
            (task_id, user_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")
        connection.execute("delete from tasks where id = %s and user_id = %s", (task_id, user_id))
    return {"deleted": True, "task": task_to_dict(row)}
