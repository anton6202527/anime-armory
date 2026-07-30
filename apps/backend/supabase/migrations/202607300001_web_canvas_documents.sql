-- Versioned Web canvas state. PostgreSQL stores the collaborative document and
-- UI state; source/generated binary files remain in R2 through public.assets.

create table public.project_canvases (
  project_id uuid primary key references public.projects(id) on delete cascade,
  owner_account_id uuid not null default public.current_account_id()
    references public.accounts(id) on delete restrict,
  document jsonb not null default '{}'::jsonb,
  revision bigint not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint project_canvases_document_object_check
    check (jsonb_typeof(document) = 'object'),
  constraint project_canvases_revision_positive_check
    check (revision > 0)
);

create or replace function private.bump_project_canvas_revision()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.revision = old.revision + 1;
  new.updated_at = now();
  return new;
end;
$$;

create trigger project_canvases_bump_revision
before update on public.project_canvases
for each row execute function private.bump_project_canvas_revision();

alter table public.project_canvases enable row level security;

create policy project_canvases_select_member on public.project_canvases
for select to authenticated
using (private.can_read_project(project_id));

create policy project_canvases_insert_editor on public.project_canvases
for insert to authenticated
with check (
  owner_account_id = public.current_account_id()
  and private.can_write_project(project_id)
);

create policy project_canvases_update_editor on public.project_canvases
for update to authenticated
using (private.can_write_project(project_id))
with check (private.can_write_project(project_id));

revoke all on table public.project_canvases from public, anon, authenticated;
grant select, insert, update on table public.project_canvases to authenticated;
grant all on table public.project_canvases to service_role;
