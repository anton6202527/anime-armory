# Web

This workspace reserves the boundary for the future Web client. No pages or Web runtime are implemented during the current desktop-first development phase.

When development starts, the Web app should consume `@anime-armory/contracts` and `@anime-armory/cloud-client`. R2 credentials and Supabase service-role secrets must remain in `apps/backend` and must never enter browser build variables.
