# Applications

The runnable products in this monorepo live under `apps/`:

- `desktop`: the current Electron client.
- `backend`: Supabase migrations, RLS policies, and Edge Functions.
- `web`: a reserved workspace for the future browser client; no pages are implemented yet.

Shared runtime-neutral code belongs in `packages/`. Browser clients may use `contracts` and `cloud-client`; server-only `data-access` and `object-store` code must stay behind the backend boundary.
