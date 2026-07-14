# Backend

Supabase is the development backend for Anime Armory. Database migrations, RLS policies, and Edge Functions live in `supabase/` inside this workspace.

Run backend commands from the repository root:

```bash
npm run typecheck:edge
npm run supabase -- status
```

Cloudflare R2 configuration is kept in the repository-level `infrastructure/r2/` directory. Official Demo ZIP files use the separate public `anime-armory-demos-public` bucket; end users read its catalog anonymously.

The `assets` Edge Function remains a reserved authenticated/private-asset boundary for future Web or team features:

- create/discover cloud projects through a stable client key;
- list the current ready asset for each relative work path;
- issue signed upload/download requests after project-role checks;
- replace same-path objects only after the new upload is verified.

It is not wired into the public desktop app. Public desktop users have no login or upload IPC, and their works remain local. Local absolute paths and Supabase/R2 secrets are never accepted from clients.
