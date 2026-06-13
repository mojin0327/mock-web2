import os
from typing import Literal, Optional

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


class WorkspaceItemCreate(BaseModel):
    type: Literal["project", "task", "idea", "log"]
    title: str
    content: str = ""
    parent_id: Optional[str] = None
    goal: str = ""
    budget: Optional[float] = None
    starts_at: Optional[str] = None
    ends_at: Optional[str] = None
    status: Literal["todo", "doing", "done", "archived"] = "todo"
    due_date: Optional[str] = None
    assignee_id: Optional[str] = None
    source: str = ""
    score: Optional[int] = None
    executed_at: Optional[str] = None


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


def workspace_item_to_dict(row):
    item = dict(row)
    item["detail"] = {
        "goal": item.pop("goal", None),
        "budget": item.pop("budget", None),
        "starts_at": item.pop("starts_at", None),
        "ends_at": item.pop("ends_at", None),
        "status": item.pop("status", None),
        "due_date": item.pop("due_date", None),
        "assignee_id": item.pop("assignee_id", None),
        "source": item.pop("source", None),
        "score": item.pop("score", None),
        "executed_at": item.pop("executed_at", None),
    }
    return item


def select_workspace_item(connection, item_id: str, user_id: str):
    return connection.execute(
        """
        select
            wi.id,
            wi.user_id,
            wi.type,
            wi.title,
            wi.content,
            wi.parent_id,
            wi.created_at,
            wi.updated_at,
            wp.goal,
            wp.budget,
            wp.starts_at,
            wp.ends_at,
            wt.status,
            wt.due_date,
            wt.assignee_id,
            wid.source,
            wid.score,
            wl.executed_at
        from workspace_items wi
        left join workspace_projects wp on wp.item_id = wi.id
        left join workspace_tasks wt on wt.item_id = wi.id
        left join workspace_ideas wid on wid.item_id = wi.id
        left join workspace_logs wl on wl.item_id = wi.id
        where wi.id = %s and wi.user_id = %s
        """,
        (item_id, user_id),
    ).fetchone()


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


@app.get("/workspace/items")
def list_workspace_items(user_id: str = Depends(get_current_user_id)):
    with get_connection() as connection:
        rows = connection.execute(
            """
            select
                wi.id,
                wi.user_id,
                wi.type,
                wi.title,
                wi.content,
                wi.parent_id,
                wi.created_at,
                wi.updated_at,
                wp.goal,
                wp.budget,
                wp.starts_at,
                wp.ends_at,
                wt.status,
                wt.due_date,
                wt.assignee_id,
                wid.source,
                wid.score,
                wl.executed_at
            from workspace_items wi
            left join workspace_projects wp on wp.item_id = wi.id
            left join workspace_tasks wt on wt.item_id = wi.id
            left join workspace_ideas wid on wid.item_id = wi.id
            left join workspace_logs wl on wl.item_id = wi.id
            where wi.user_id = %s
            order by wi.created_at desc
            """,
            (user_id,),
        ).fetchall()
    return [workspace_item_to_dict(row) for row in rows]


@app.post("/workspace/items")
def create_workspace_item(payload: WorkspaceItemCreate, user_id: str = Depends(get_current_user_id)):
    with get_connection() as connection:
        if payload.parent_id:
            parent = connection.execute(
                "select id from workspace_items where id = %s and user_id = %s",
                (payload.parent_id, user_id),
            ).fetchone()
            if parent is None:
                raise HTTPException(status_code=400, detail="parent_id does not belong to the current user")

        row = connection.execute(
            """
            insert into workspace_items (user_id, type, title, content, parent_id)
            values (%s, %s, %s, %s, %s)
            returning id
            """,
            (user_id, payload.type, payload.title, payload.content, payload.parent_id),
        ).fetchone()
        item_id = row["id"]

        if payload.type == "project":
            connection.execute(
                """
                insert into workspace_projects (item_id, goal, budget, starts_at, ends_at)
                values (%s, %s, %s, %s, %s)
                """,
                (item_id, payload.goal, payload.budget, payload.starts_at, payload.ends_at),
            )
        elif payload.type == "task":
            connection.execute(
                """
                insert into workspace_tasks (item_id, status, due_date, assignee_id)
                values (%s, %s, %s, %s)
                """,
                (item_id, payload.status, payload.due_date, payload.assignee_id),
            )
        elif payload.type == "idea":
            connection.execute(
                """
                insert into workspace_ideas (item_id, source, score)
                values (%s, %s, %s)
                """,
                (item_id, payload.source, payload.score),
            )
        elif payload.type == "log":
            if payload.executed_at:
                connection.execute(
                    """
                    insert into workspace_logs (item_id, executed_at)
                    values (%s, %s)
                    """,
                    (item_id, payload.executed_at),
                )
            else:
                connection.execute("insert into workspace_logs (item_id) values (%s)", (item_id,))

        created = select_workspace_item(connection, item_id, user_id)
    return workspace_item_to_dict(created)


@app.get("/workspace/items/{item_id}")
def get_workspace_item(item_id: str, user_id: str = Depends(get_current_user_id)):
    with get_connection() as connection:
        row = select_workspace_item(connection, item_id, user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Workspace item not found")
    return workspace_item_to_dict(row)


@app.delete("/workspace/items/{item_id}")
def delete_workspace_item(item_id: str, user_id: str = Depends(get_current_user_id)):
    with get_connection() as connection:
        row = select_workspace_item(connection, item_id, user_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Workspace item not found")
        connection.execute("delete from workspace_items where id = %s and user_id = %s", (item_id, user_id))
    return {"deleted": True, "item": workspace_item_to_dict(row)}
