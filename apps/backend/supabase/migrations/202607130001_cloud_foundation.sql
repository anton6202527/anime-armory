-- LabuTV cloud foundation.
-- Large binary content lives in object storage; Postgres stores identity,
-- authorization, metadata, and resumable-upload state only.

create schema if not exists private;
revoke all on schema private from public;

create table public.accounts (
  id uuid primary key default gen_random_uuid(),
  display_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint accounts_display_name_length check (display_name is null or char_length(display_name) <= 120)
);

create table public.account_identities (
  account_id uuid not null references public.accounts(id) on delete cascade,
  provider text not null,
  provider_subject text not null,
  email text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (provider, provider_subject),
  constraint account_identities_provider_check check (provider in ('supabase', 'tencent')),
  constraint account_identities_provider_subject_length check (char_length(provider_subject) between 1 and 255)
);

create index account_identities_account_id_idx on public.account_identities(account_id);

create table public.projects (
  id uuid primary key default gen_random_uuid(),
  owner_account_id uuid not null references public.accounts(id) on delete restrict,
  name text not null,
  archived_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint projects_name_length check (char_length(btrim(name)) between 1 and 160)
);

create table public.project_members (
  project_id uuid not null references public.projects(id) on delete cascade,
  account_id uuid not null references public.accounts(id) on delete cascade,
  role text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (project_id, account_id),
  constraint project_members_role_check check (role in ('owner', 'editor', 'viewer'))
);

create index project_members_account_id_idx on public.project_members(account_id, project_id);

create table public.assets (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  owner_account_id uuid not null references public.accounts(id) on delete restrict,
  storage_provider text not null,
  storage_bucket text not null,
  object_key text not null,
  object_etag text,
  object_version_id text,
  original_name text not null,
  content_type text not null,
  size_bytes bigint not null,
  sha256 text,
  status text not null default 'pending',
  failure_reason text,
  deleted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint assets_storage_provider_check check (storage_provider in ('r2', 'cos')),
  constraint assets_bucket_length check (char_length(storage_bucket) between 1 and 255),
  constraint assets_object_key_length check (char_length(object_key) between 1 and 1024),
  constraint assets_original_name_length check (char_length(original_name) between 1 and 255),
  constraint assets_content_type_length check (char_length(content_type) between 1 and 255),
  constraint assets_size_bytes_check check (size_bytes > 0),
  constraint assets_sha256_check check (sha256 is null or sha256 ~ '^[0-9a-f]{64}$'),
  constraint assets_status_check check (status in ('pending', 'uploading', 'ready', 'failed', 'deleted')),
  constraint assets_object_unique unique (storage_provider, storage_bucket, object_key)
);

create index assets_project_created_idx on public.assets(project_id, created_at desc);
create index assets_owner_account_idx on public.assets(owner_account_id, created_at desc);
create index assets_status_idx on public.assets(status) where status in ('pending', 'uploading', 'failed');

create table public.asset_uploads (
  asset_id uuid primary key references public.assets(id) on delete cascade,
  created_by uuid not null references public.accounts(id) on delete restrict,
  mode text not null,
  upload_id text,
  part_size_bytes bigint,
  state text not null default 'pending',
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint asset_uploads_mode_check check (mode in ('single', 'multipart')),
  constraint asset_uploads_state_check check (state in ('pending', 'uploading', 'completed', 'aborted', 'failed')),
  constraint asset_uploads_part_size_check check (part_size_bytes is null or part_size_bytes >= 5242880),
  constraint asset_uploads_mode_fields_check check (
    (mode = 'single' and upload_id is null and part_size_bytes is null)
    or
    (mode = 'multipart' and upload_id is not null and part_size_bytes is not null)
  )
);

create index asset_uploads_expiry_idx on public.asset_uploads(expires_at)
  where state in ('pending', 'uploading');

create table public.jobs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  created_by uuid not null references public.accounts(id) on delete restrict,
  kind text not null,
  state text not null default 'queued',
  input jsonb not null default '{}'::jsonb,
  output jsonb,
  error_message text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  updated_at timestamptz not null default now(),
  constraint jobs_kind_length check (char_length(kind) between 1 and 120),
  constraint jobs_state_check check (state in ('queued', 'running', 'succeeded', 'failed', 'cancelled'))
);

create index jobs_project_created_idx on public.jobs(project_id, created_at desc);
create index jobs_pending_idx on public.jobs(state, created_at) where state in ('queued', 'running');

create or replace function private.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger accounts_set_updated_at
before update on public.accounts
for each row execute function private.set_updated_at();

create trigger account_identities_set_updated_at
before update on public.account_identities
for each row execute function private.set_updated_at();

create trigger projects_set_updated_at
before update on public.projects
for each row execute function private.set_updated_at();

create trigger project_members_set_updated_at
before update on public.project_members
for each row execute function private.set_updated_at();

create trigger assets_set_updated_at
before update on public.assets
for each row execute function private.set_updated_at();

create trigger asset_uploads_set_updated_at
before update on public.asset_uploads
for each row execute function private.set_updated_at();

create trigger jobs_set_updated_at
before update on public.jobs
for each row execute function private.set_updated_at();

create or replace function private.ensure_supabase_account()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.accounts (id, display_name)
  values (
    new.id,
    nullif(coalesce(new.raw_user_meta_data ->> 'display_name', new.raw_user_meta_data ->> 'name'), '')
  )
  on conflict (id) do nothing;

  insert into public.account_identities (account_id, provider, provider_subject, email)
  values (new.id, 'supabase', new.id::text, new.email)
  on conflict (provider, provider_subject) do update
    set email = excluded.email,
        updated_at = now();

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert or update of email, raw_user_meta_data on auth.users
for each row execute function private.ensure_supabase_account();

-- Backfill accounts if this migration is applied to an existing Supabase project.
insert into public.accounts (id, display_name)
select
  users.id,
  nullif(coalesce(users.raw_user_meta_data ->> 'display_name', users.raw_user_meta_data ->> 'name'), '')
from auth.users as users
on conflict (id) do nothing;

insert into public.account_identities (account_id, provider, provider_subject, email)
select users.id, 'supabase', users.id::text, users.email
from auth.users as users
on conflict (provider, provider_subject) do update
  set email = excluded.email,
      updated_at = now();

create or replace function public.current_account_id()
returns uuid
language sql
stable
security definer
set search_path = ''
as $$
  select identities.account_id
  from public.account_identities as identities
  where identities.provider = 'supabase'
    and identities.provider_subject = (select auth.uid())::text
  limit 1
$$;

revoke all on function public.current_account_id() from public;
grant execute on function public.current_account_id() to authenticated, service_role;

create or replace function private.can_read_project(target_project_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.project_members as members
    where members.project_id = target_project_id
      and members.account_id = public.current_account_id()
  )
$$;

create or replace function private.can_write_project(target_project_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.project_members as members
    where members.project_id = target_project_id
      and members.account_id = public.current_account_id()
      and members.role in ('owner', 'editor')
  )
$$;

create or replace function private.is_project_owner(target_project_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.projects as projects
    where projects.id = target_project_id
      and projects.owner_account_id = public.current_account_id()
  )
$$;

create or replace function private.can_read_asset(target_asset_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.assets as assets
    join public.project_members as members on members.project_id = assets.project_id
    where assets.id = target_asset_id
      and members.account_id = public.current_account_id()
  )
$$;

create or replace function private.add_project_owner_membership()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.project_members (project_id, account_id, role)
  values (new.id, new.owner_account_id, 'owner')
  on conflict (project_id, account_id) do update set role = 'owner';
  return new;
end;
$$;

create trigger projects_add_owner_membership
after insert on public.projects
for each row execute function private.add_project_owner_membership();

create or replace function private.protect_project_owner_membership()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  project_owner_id uuid;
begin
  select projects.owner_account_id into project_owner_id
  from public.projects as projects
  where projects.id = old.project_id;

  if old.account_id = project_owner_id then
    if tg_op = 'DELETE' or new.account_id <> old.account_id or new.role <> 'owner' then
      raise exception 'the project owner membership cannot be removed or demoted';
    end if;
  end if;

  if tg_op = 'UPDATE' and new.role = 'owner' and new.account_id <> project_owner_id then
    raise exception 'only the project owner may have the owner role';
  end if;

  return case when tg_op = 'DELETE' then old else new end;
end;
$$;

create trigger project_members_protect_owner
before update or delete on public.project_members
for each row execute function private.protect_project_owner_membership();

alter table public.accounts enable row level security;
alter table public.account_identities enable row level security;
alter table public.projects enable row level security;
alter table public.project_members enable row level security;
alter table public.assets enable row level security;
alter table public.asset_uploads enable row level security;
alter table public.jobs enable row level security;

create policy accounts_select_self on public.accounts
for select to authenticated
using (id = public.current_account_id());

create policy account_identities_select_self on public.account_identities
for select to authenticated
using (account_id = public.current_account_id());

create policy projects_select_member on public.projects
for select to authenticated
using (private.can_read_project(id));

create policy projects_insert_owner on public.projects
for insert to authenticated
with check (owner_account_id = public.current_account_id());

create policy projects_update_owner on public.projects
for update to authenticated
using (private.is_project_owner(id))
with check (owner_account_id = public.current_account_id());

create policy projects_delete_owner on public.projects
for delete to authenticated
using (private.is_project_owner(id));

create policy project_members_select_member on public.project_members
for select to authenticated
using (private.can_read_project(project_id));

create policy project_members_insert_owner on public.project_members
for insert to authenticated
with check (
  private.is_project_owner(project_id)
  and role <> 'owner'
);

create policy project_members_update_owner on public.project_members
for update to authenticated
using (private.is_project_owner(project_id))
with check (
  private.is_project_owner(project_id)
  and role <> 'owner'
);

create policy project_members_delete_owner on public.project_members
for delete to authenticated
using (private.is_project_owner(project_id));

create policy assets_select_member on public.assets
for select to authenticated
using (private.can_read_project(project_id));

create policy jobs_select_member on public.jobs
for select to authenticated
using (private.can_read_project(project_id));

create policy jobs_insert_editor on public.jobs
for insert to authenticated
with check (
  private.can_write_project(project_id)
  and created_by = public.current_account_id()
);

create policy jobs_update_editor on public.jobs
for update to authenticated
using (private.can_write_project(project_id))
with check (private.can_write_project(project_id));

-- Authenticated clients may read asset metadata but cannot directly mutate object
-- references or upload state. The Edge Function validates R2 and writes with the
-- server-only service role.
revoke all on table public.accounts from anon, authenticated;
revoke all on table public.account_identities from anon, authenticated;
revoke all on table public.projects from anon, authenticated;
revoke all on table public.project_members from anon, authenticated;
revoke all on table public.assets from anon, authenticated;
revoke all on table public.asset_uploads from anon, authenticated;
revoke all on table public.jobs from anon, authenticated;

grant select on table public.accounts to authenticated;
grant select on table public.account_identities to authenticated;
grant select, insert, update, delete on table public.projects to authenticated;
grant select, insert, update, delete on table public.project_members to authenticated;
grant select on table public.assets to authenticated;
grant select, insert, update on table public.jobs to authenticated;

grant all on table public.accounts to service_role;
grant all on table public.account_identities to service_role;
grant all on table public.projects to service_role;
grant all on table public.project_members to service_role;
grant all on table public.assets to service_role;
grant all on table public.asset_uploads to service_role;
grant all on table public.jobs to service_role;

revoke all on all functions in schema private from public, anon, authenticated;
grant usage on schema private to authenticated;
grant execute on function private.can_read_project(uuid) to authenticated;
grant execute on function private.can_write_project(uuid) to authenticated;
grant execute on function private.is_project_owner(uuid) to authenticated;
grant execute on function private.can_read_asset(uuid) to authenticated;
