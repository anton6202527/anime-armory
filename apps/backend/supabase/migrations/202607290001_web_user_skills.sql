-- Web user product state. Authentication remains owned by Supabase Auth; these
-- tables contain only profile presentation, product preferences, and private
-- user-authored Skill definitions.

create table public.user_profiles (
  owner_id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  avatar_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint user_profiles_display_name_length
    check (display_name is null or char_length(display_name) <= 120),
  constraint user_profiles_avatar_url_length
    check (avatar_url is null or char_length(avatar_url) <= 2048)
);

create table public.user_settings (
  owner_id uuid primary key references auth.users(id) on delete cascade,
  theme text not null default 'dark',
  preferences jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint user_settings_theme_check check (theme in ('dark', 'light', 'system')),
  constraint user_settings_preferences_object_check
    check (jsonb_typeof(preferences) = 'object')
);

create table public.user_skills (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  slug text not null,
  title text not null,
  description text not null default '',
  creation_line text not null,
  category text not null default '通用技能',
  media_type text not null default 'mixed',
  visibility text not null default 'private',
  guide text not null default '',
  steps text[] not null default '{}'::text[],
  use_cases text[] not null default '{}'::text[],
  definition jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint user_skills_owner_slug_unique unique (owner_id, slug),
  constraint user_skills_slug_length check (char_length(slug) between 1 and 80),
  constraint user_skills_slug_format check (slug ~ '^[a-z0-9][a-z0-9._-]*$'),
  constraint user_skills_title_length check (char_length(btrim(title)) between 1 and 120),
  constraint user_skills_description_length check (char_length(description) <= 2000),
  constraint user_skills_creation_line_check
    check (creation_line in ('novel', 'n2d', 'comic', 'ad', 'mv', 'song')),
  constraint user_skills_category_length check (char_length(btrim(category)) between 1 and 80),
  constraint user_skills_media_type_check
    check (media_type in ('text', 'image', 'video', 'audio', 'mixed')),
  constraint user_skills_visibility_check
    check (visibility in ('private', 'public')),
  constraint user_skills_guide_length check (char_length(guide) <= 8000),
  constraint user_skills_steps_count check (cardinality(steps) <= 40),
  constraint user_skills_use_cases_count check (cardinality(use_cases) <= 40),
  constraint user_skills_definition_object_check
    check (jsonb_typeof(definition) = 'object')
);

create index user_skills_owner_updated_idx
  on public.user_skills(owner_id, updated_at desc);

create trigger user_profiles_set_updated_at
before update on public.user_profiles
for each row execute function private.set_updated_at();

create trigger user_settings_set_updated_at
before update on public.user_settings
for each row execute function private.set_updated_at();

create trigger user_skills_set_updated_at
before update on public.user_skills
for each row execute function private.set_updated_at();

-- Ensure every Supabase Auth user has stable product defaults. This is kept in
-- a separate trigger from account creation so either subsystem can evolve
-- without changing the other trigger's responsibilities.
create or replace function private.ensure_web_user_state()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.user_profiles (owner_id, display_name)
  values (
    new.id,
    nullif(coalesce(new.raw_user_meta_data ->> 'display_name', new.raw_user_meta_data ->> 'name'), '')
  )
  on conflict (owner_id) do nothing;

  insert into public.user_settings (owner_id, theme)
  values (new.id, 'dark')
  on conflict (owner_id) do nothing;

  return new;
end;
$$;

drop trigger if exists on_auth_user_web_state_created on auth.users;
create trigger on_auth_user_web_state_created
after insert on auth.users
for each row execute function private.ensure_web_user_state();

-- Backfill product state when this migration is applied after users exist.
insert into public.user_profiles (owner_id, display_name)
select
  users.id,
  nullif(coalesce(users.raw_user_meta_data ->> 'display_name', users.raw_user_meta_data ->> 'name'), '')
from auth.users as users
on conflict (owner_id) do nothing;

insert into public.user_settings (owner_id, theme)
select users.id, 'dark'
from auth.users as users
on conflict (owner_id) do nothing;

alter table public.user_profiles enable row level security;
alter table public.user_settings enable row level security;
alter table public.user_skills enable row level security;

create policy user_profiles_select_self on public.user_profiles
for select to authenticated
using (owner_id = (select auth.uid()));

create policy user_profiles_insert_self on public.user_profiles
for insert to authenticated
with check (owner_id = (select auth.uid()));

create policy user_profiles_update_self on public.user_profiles
for update to authenticated
using (owner_id = (select auth.uid()))
with check (owner_id = (select auth.uid()));

create policy user_settings_select_self on public.user_settings
for select to authenticated
using (owner_id = (select auth.uid()));

create policy user_settings_insert_self on public.user_settings
for insert to authenticated
with check (owner_id = (select auth.uid()));

create policy user_settings_update_self on public.user_settings
for update to authenticated
using (owner_id = (select auth.uid()))
with check (owner_id = (select auth.uid()));

create policy user_skills_select_self on public.user_skills
for select to authenticated
using (owner_id = (select auth.uid()));

create policy user_skills_select_public on public.user_skills
for select to anon, authenticated
using (visibility = 'public');

create policy user_skills_insert_self on public.user_skills
for insert to authenticated
with check (owner_id = (select auth.uid()));

create policy user_skills_update_self on public.user_skills
for update to authenticated
using (owner_id = (select auth.uid()))
with check (owner_id = (select auth.uid()));

create policy user_skills_delete_self on public.user_skills
for delete to authenticated
using (owner_id = (select auth.uid()));

revoke all on table public.user_profiles from public, anon, authenticated;
revoke all on table public.user_settings from public, anon, authenticated;
revoke all on table public.user_skills from public, anon, authenticated;

grant select, insert, update on table public.user_profiles to authenticated;
grant select, insert, update on table public.user_settings to authenticated;
grant select, insert, update, delete on table public.user_skills to authenticated;
grant select on table public.user_skills to anon;

grant all on table public.user_profiles to service_role;
grant all on table public.user_settings to service_role;
grant all on table public.user_skills to service_role;
