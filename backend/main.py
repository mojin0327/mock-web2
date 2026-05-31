import os
from typing import Optional

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg.rows import dict_row
from pydantic import BaseModel

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required. Set it to your PostgreSQL connection string.")

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


def init_db():
    with get_connection() as connection:
        connection.execute(
            """
            create table if not exists tasks (
                id serial primary key,
                title text not null,
                description text not null default '',
                done boolean not null default false,
                created_at timestamptz not null default current_timestamp,
                updated_at timestamptz not null default current_timestamp
            )
            """
        )


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "database": "postgres", "redis": "skip"}


def task_to_dict(row):
    task = dict(row)
    task["done"] = bool(task["done"])
    return task


@app.get("/tasks")
def list_tasks():
    with get_connection() as connection:
        rows = connection.execute(
            """
            select id, title, description, done, created_at, updated_at
            from tasks
            order by id desc
            """
        ).fetchall()
    return [task_to_dict(row) for row in rows]


@app.post("/tasks")
def create_task(payload: TaskCreate):
    with get_connection() as connection:
        row = connection.execute(
            """
            insert into tasks (title, description)
            values (%s, %s)
            returning id, title, description, done, created_at, updated_at
            """,
            (payload.title, payload.description),
        ).fetchone()
    return task_to_dict(row)


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    with get_connection() as connection:
        row = connection.execute(
            """
            select id, title, description, done, created_at, updated_at
            from tasks
            where id = %s
            """,
            (task_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_to_dict(row)


@app.patch("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskUpdate):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return get_task(task_id)

    allowed_fields = {
        "title": updates.get("title"),
        "description": updates.get("description"),
        "done": updates.get("done"),
    }
    fields = [field for field in allowed_fields if field in updates]
    values = [allowed_fields[field] for field in fields]
    assignments = ", ".join([f"{field} = %s" for field in fields])

    with get_connection() as connection:
        existing = connection.execute("select id from tasks where id = %s", (task_id,)).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Task not found")

        connection.execute(
            f"update tasks set {assignments}, updated_at = current_timestamp where id = %s",
            (*values, task_id),
        )
        row = connection.execute(
            """
            select id, title, description, done, created_at, updated_at
            from tasks
            where id = %s
            """,
            (task_id,),
        ).fetchone()
    return task_to_dict(row)


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    with get_connection() as connection:
        row = connection.execute(
            """
            select id, title, description, done, created_at, updated_at
            from tasks
            where id = %s
            """,
            (task_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")
        connection.execute("delete from tasks where id = %s", (task_id,))
    return {"deleted": True, "task": task_to_dict(row)}
