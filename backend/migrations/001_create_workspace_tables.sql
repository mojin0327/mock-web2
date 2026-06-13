create table if not exists workspace_items (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null,
    type text not null check (type in ('project', 'task', 'idea', 'log')),
    title text not null,
    content text not null default '',
    parent_id uuid references workspace_items(id) on delete set null,
    created_at timestamptz not null default current_timestamp,
    updated_at timestamptz not null default current_timestamp
);

create index if not exists idx_workspace_items_user_id on workspace_items(user_id);
create index if not exists idx_workspace_items_parent_id on workspace_items(parent_id);
create index if not exists idx_workspace_items_type on workspace_items(type);

create table if not exists workspace_projects (
    item_id uuid primary key references workspace_items(id) on delete cascade,
    goal text not null default '',
    budget numeric,
    starts_at date,
    ends_at date
);

create table if not exists workspace_tasks (
    item_id uuid primary key references workspace_items(id) on delete cascade,
    status text not null default 'todo' check (status in ('todo', 'doing', 'done', 'archived')),
    due_date date,
    assignee_id uuid
);

create table if not exists workspace_ideas (
    item_id uuid primary key references workspace_items(id) on delete cascade,
    source text not null default '',
    score integer check (score is null or (score >= 1 and score <= 10))
);

create table if not exists workspace_logs (
    item_id uuid primary key references workspace_items(id) on delete cascade,
    executed_at timestamptz not null default current_timestamp
);
