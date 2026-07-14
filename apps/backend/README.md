# Backend

Supabase is the development backend for Anime Armory. Database migrations, RLS policies, and Edge Functions live in `supabase/` inside this workspace.

Run backend commands from the repository root:

```bash
npm run typecheck:edge
npm run supabase -- status
```

Cloudflare R2 remains an external private object store. Its declarative configuration is kept in the repository-level `infrastructure/r2/` directory.
