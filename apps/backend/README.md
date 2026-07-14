# Backend

Supabase is the development backend for Anime Armory. Database migrations, RLS policies, and Edge Functions live in `supabase/` inside this workspace.

Run backend commands from the repository root:

```bash
npm run typecheck:edge
npm run supabase -- status
```

Cloudflare R2 remains an external private object store. Its declarative configuration is kept in the repository-level `infrastructure/r2/` directory.

The `assets` Edge Function also owns the authenticated desktop sync boundary:

- create/discover cloud projects through a stable client key;
- list the current ready asset for each relative work path;
- issue signed upload/download requests after project-role checks;
- replace same-path objects only after the new upload is verified.

Local absolute paths and Supabase/R2 secrets are never accepted from desktop clients.
