# Applications

The runnable products in this monorepo live under `apps/`:

- `desktop`: the current Electron client.
- `backend`: Supabase migrations, RLS policies, and Edge Functions.
- `web`: the LabuTV browser Hub and cloud-agent canvas.

Shared runtime-neutral code belongs in `packages/`. Browser clients may use `contracts` and `cloud-client`; server-only `data-access` and `object-store` code must stay behind the backend boundary.
