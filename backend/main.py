import os
import sqlite3
from pathlib import Path
from typing import Optional

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg.rows import dict_row
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Mock Web2 API")

frontend_origins = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in frontend_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
DB_KIND = "postgres" if DATABASE_URL else "sqlite"

DEFAULT_DB_PATH = "/tmp/app.db" if os.getenv("VERCEL") else Path(__file__).with_name("app.db")
DB_PATH = Path(os.getenv("DATABASE_PATH", DEFAULT_DB_PATH))
if os.getenv("VERCEL") and not DB_PATH.is_absolute():
    DB_PATH = Path("/tmp") / DB_PATH


class MemoCreate(BaseModel):
    text: str


class TaskCreate(BaseModel):
    title: str
    description: str = ""


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    done: Optional[bool] = None


def get_connection():
    if DB_KIND == "postgres":
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def placeholder() -> str:
    return "%s" if DB_KIND == "postgres" else "?"


def row_to_dict(row):
    return dict(row) if row is not None else None


def init_db():
    with get_connection() as connection:
        if DB_KIND == "postgres":
            connection.execute(
                """
                create table if not exists memos (
                    id serial primary key,
                    text text not null
                )
                """
            )
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
            return

        connection.execute(
            """
            create table if not exists memos (
                id integer primary key autoincrement,
                text text not null
            )
            """
        )
        connection.execute(
            """
            create table if not exists tasks (
                id integer primary key autoincrement,
                title text not null,
                description text not null default '',
                done integer not null default 0,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp
            )
            """
        )


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "database": DB_KIND, "redis": "skip"}


@app.get("/memos")
def list_memos():
    with get_connection() as connection:
        rows = connection.execute("select id, text from memos order by id desc").fetchall()
    return [row_to_dict(row) for row in rows]


@app.post("/memos")
def create_memo(payload: MemoCreate):
    with get_connection() as connection:
        if DB_KIND == "postgres":
            row = connection.execute(
                "insert into memos (text) values (%s) returning id, text",
                (payload.text,),
            ).fetchone()
            return row_to_dict(row)

        cursor = connection.execute(
            "insert into memos (text) values (?)",
            (payload.text,),
        )
        memo_id = cursor.lastrowid
        row = connection.execute("select id, text from memos where id = ?", (memo_id,)).fetchone()
    return row_to_dict(row)


def task_to_dict(row):
    task = row_to_dict(row)
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
        if DB_KIND == "postgres":
            row = connection.execute(
                """
                insert into tasks (title, description)
                values (%s, %s)
                returning id, title, description, done, created_at, updated_at
                """,
                (payload.title, payload.description),
            ).fetchone()
            return task_to_dict(row)

        cursor = connection.execute(
            "insert into tasks (title, description) values (?, ?)",
            (payload.title, payload.description),
        )
        task_id = cursor.lastrowid
        row = connection.execute(
            """
            select id, title, description, done, created_at, updated_at
            from tasks
            where id = ?
            """,
            (task_id,),
        ).fetchone()
    return task_to_dict(row)


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    param = placeholder()
    with get_connection() as connection:
        row = connection.execute(
            f"""
            select id, title, description, done, created_at, updated_at
            from tasks
            where id = {param}
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

    done_value = None
    if "done" in updates:
        done_value = updates["done"] if DB_KIND == "postgres" else int(updates["done"])

    allowed_fields = {
        "title": updates.get("title"),
        "description": updates.get("description"),
        "done": done_value,
    }
    fields = [field for field in allowed_fields if field in updates]
    values = [allowed_fields[field] for field in fields]
    param = placeholder()
    assignments = ", ".join([f"{field} = {param}" for field in fields])

    with get_connection() as connection:
        existing = connection.execute(f"select id from tasks where id = {param}", (task_id,)).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Task not found")

        connection.execute(
            f"update tasks set {assignments}, updated_at = current_timestamp where id = {param}",
            (*values, task_id),
        )
        row = connection.execute(
            f"""
            select id, title, description, done, created_at, updated_at
            from tasks
            where id = {param}
            """,
            (task_id,),
        ).fetchone()
    return task_to_dict(row)


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    param = placeholder()
    with get_connection() as connection:
        row = connection.execute(
            f"""
            select id, title, description, done, created_at, updated_at
            from tasks
            where id = {param}
            """,
            (task_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")
        connection.execute(f"delete from tasks where id = {param}", (task_id,))
    return {"deleted": True, "task": task_to_dict(row)}
