# OpenDocX Open Source Checklist

> Status: v0.1.0 public alpha prep
> Last updated: 2026-06-09

OpenDocX is ready to be opened as an alpha project once the checklist below is clean. The goal is not to claim production maturity; the goal is to make a new contributor or evaluator understand the product, run it locally, and see the core workflow.

## Positioning

- [x] Rename public product surface from OpenDocX to OpenDocX.
- [x] State the new positioning: documentation, manual, and publishing layer for AI / Vibe Coding projects.
- [x] Mark v0.1.0 as public alpha, not stable production software.
- [x] Keep known limitations visible in README.

## Repository Hygiene

- [x] Keep runtime data out of git: `.env`, `data/builds/`, `data/uploads/`, `data/docs/`, local DB files.
- [x] Keep internal work notes under `docs/internal/` ignored.
- [ ] Review tracked generated files, especially `frontend/tsconfig.tsbuildinfo`.
- [ ] Ensure no local absolute paths remain in public setup docs or runtime defaults.
- [ ] Decide whether legacy lowercase identifiers such as `opendocx-theme` should stay for compatibility or migrate later.

## Runability

- [x] Document default ports: backend `8001`, frontend `3077`.
- [x] Provide demo seed data.
- [x] Provide default alpha login: `admin@opendocx.local / admin123`.
- [ ] Run `bash scripts/seed_demo.sh` against a clean DB.
- [ ] Run backend tests.
- [ ] Run frontend build.
- [ ] Build a demo static site and verify `/published` plus `/docs`.

## Product Scope

- [x] Core admin workflow: login, projects, versions, documents, editor, publish, build.
- [x] AI workflow: editor panel, floating tip, selection-aware Q&A, streaming responses.
- [x] Release workflow: pre-build modal, draft detection, single and batch publish.
- [x] Operations workflow: users, RBAC, audit logs, feedback moderation.
- [x] Static-site rendering: Markdown, tables, Mermaid, admonitions, Pygments, images, video, iframe styling.
- [ ] Formula rendering is not complete.
- [ ] MDX is not implemented.
- [ ] Real-time collaborative editing is not implemented.
- [ ] Frontend tests are not implemented.

## Launch Materials

- [x] README.
- [x] CHANGELOG.
- [x] ROADMAP.
- [x] USER-GUIDE.
- [x] API reference.
- [x] ARCHITECTURE.
- [x] SECURITY.
- [x] CONTRIBUTING.
- [x] Issue templates.
- [ ] Replace screenshot placeholders with real OpenDocX screenshots.
- [ ] Decide final GitHub org/repo URL.
