---
name: implement-ui
description: Build or refactor UI pages and components in Kira's frontend/ Next.js application. Use for Kira web UI implementation work.
---

# Implement UI in Kira

- Read `AGENTS.md` and inspect the nearest existing page, component, hook, and test before editing.
- Work in `frontend/src/` using Next.js App Router, React 19, strict TypeScript, Tailwind CSS, and existing Radix primitives in `frontend/src/components/ui/`.
- Keep API data and mutations in `frontend/src/lib/` hooks or clients. Validate external data with the project's Zod schemas. Follow the established translation pattern where the touched UI already uses it.
- Cover loading, empty, error, retry, keyboard access, and narrow screens for the interaction being changed.
- Run `npm run lint`, `npx tsc --noEmit`, and `npm test` from `frontend/`. Report checks that cannot run.
