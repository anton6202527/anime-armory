-- Desktop cloud sync metadata.
-- Project client keys survive local path moves, while asset relative paths let
-- clients compare a work tree with the current objects without exposing local
-- absolute paths to the server.

alter table public.projects
  add column if not exists client_key uuid;

update public.projects
set client_key = id
where client_key is null;

alter table public.projects
  alter column client_key set not null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'projects_owner_client_key_unique'
      and conrelid = 'public.projects'::regclass
  ) then
    alter table public.projects
      add constraint projects_owner_client_key_unique unique (owner_account_id, client_key);
  end if;
end
$$;

alter table public.assets
  add column if not exists relative_path text;

update public.assets
set relative_path = original_name
where relative_path is null;

alter table public.assets
  alter column relative_path set not null;

alter table public.assets
  drop constraint if exists assets_relative_path_length;
alter table public.assets
  add constraint assets_relative_path_length
  check (char_length(relative_path) between 1 and 1024);

alter table public.assets
  drop constraint if exists assets_relative_path_safe;
alter table public.assets
  add constraint assets_relative_path_safe
  check (
    relative_path !~ '^/'
    and relative_path !~ '\\'
    and relative_path !~ '(^|/)\.\.?(/|$)'
    and relative_path !~ '//'
  );

alter table public.assets
  drop constraint if exists assets_size_bytes_check;
alter table public.assets
  add constraint assets_size_bytes_check check (size_bytes >= 0);

create index if not exists assets_project_relative_path_idx
  on public.assets(project_id, relative_path, created_at desc)
  where deleted_at is null and status = 'ready';
