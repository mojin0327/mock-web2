alter table workspace_items add column if not exists legacy_task_id integer;

create unique index if not exists idx_workspace_items_legacy_task_id
on workspace_items(legacy_task_id)
where legacy_task_id is not null;

insert into workspace_items (
    user_id,
    type,
    title,
    content,
    legacy_task_id,
    created_at,
    updated_at
)
select
    t.user_id,
    'task',
    t.title,
    t.description,
    t.id,
    t.created_at,
    t.updated_at
from tasks t
where t.user_id is not null
and not exists (
    select 1
    from workspace_items wi
    where wi.legacy_task_id = t.id
);

insert into workspace_tasks (item_id, status)
select
    wi.id,
    case when t.done then 'done' else 'todo' end
from workspace_items wi
join tasks t on t.id = wi.legacy_task_id
where not exists (
    select 1
    from workspace_tasks wt
    where wt.item_id = wi.id
)
and wi.type = 'task';
