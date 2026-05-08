# Triska

Stream Deck style shortcut panel and recordable workflows for clinical web
apps. Phase 0 scaffold — see [`PLAN.md`](./PLAN.md) for the full design and
[`HAZARD_LOG.md`](./HAZARD_LOG.md) for clinical safety tracking.

> **Status: pre-alpha.** Phase 0 ships a hello-world floating panel and an
> empty editor. No primitive actions, recorder, replay, or arming yet —
> those arrive in Phases 1–6 of `PLAN.md`. Do not deploy to clinical use.

## Stack

Manifest V3 · TypeScript · React · Vite (with `@crxjs/vite-plugin`) ·
Tailwind (editor only). Local-first; no network calls.

## Develop

```bash
cd triska
npm install
npm run dev
```

Then in Chrome:

1. `chrome://extensions` → Developer mode on.
2. *Load unpacked* → select `triska/dist`.
3. Visit any matched origin (default: `https://*.medicus.health/*` and
   `http://localhost/*`). The floating panel appears in the bottom-right.
4. `Ctrl+Shift+T` (or `Cmd+Shift+T` on macOS) toggles the panel.
5. Click the extension icon to open the editor (options page).

## Build

```bash
npm run build
```

Output goes to `triska/dist`. Load that as an unpacked extension.

## Phase status

- [x] Phase 0 — scaffolding, hello-world panel, editor shell, data model
      types
- [ ] Phase 1 — `NAVIGATE`, `CLICK`, `WAIT_FOR_DOM` primitives
- [ ] Phase 2 — `INJECT_TEXT` + editor authoring UI wired to
      `chrome.storage`
- [ ] Phase 3 — recorder
- [ ] Phase 4 — replay with SAFE mode, toasts, audit log, draft rollback
- [ ] Phase 5 — CONFIRM mode
- [ ] Phase 6 — LIVE mode + arming
- [ ] Phase 7 — polish (hotkeys, permissions, export/import, onboarding)
- [ ] Phase 8 — Medicus pre-loaded pack

See `PLAN.md` for full per-phase scope.
