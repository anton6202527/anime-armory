-- Project deletion is a server-side administrative operation. Authenticated
-- clients retain read/create/update access, while service_role keeps the full
-- table grant established by the foundation migration.
revoke delete on table public.projects from authenticated;

drop policy if exists projects_delete_owner on public.projects;

-- Read quota counters through the server-side Supabase client. Keeping this as
-- one RPC gives the caller a consistent account-level view without exposing
-- either table to authenticated clients.
create or replace function public.account_asset_usage(target_account_id uuid)
returns table (
  reserved_bytes bigint,
  active_uploads bigint
)
language sql
stable
security definer
set search_path = ''
as $$
  select
    coalesce((
      select sum(assets.size_bytes)
      from public.assets as assets
      where assets.owner_account_id = target_account_id
        and assets.deleted_at is null
        and assets.status in ('pending', 'uploading', 'ready')
    ), 0)::bigint as reserved_bytes,
    (
      select count(*)
      from public.asset_uploads as uploads
      where uploads.created_by = target_account_id
        and uploads.state = 'uploading'
        and uploads.expires_at > now()
    )::bigint as active_uploads;
$$;

revoke all on function public.account_asset_usage(uuid)
from public, anon, authenticated;
grant execute on function public.account_asset_usage(uuid) to service_role;
