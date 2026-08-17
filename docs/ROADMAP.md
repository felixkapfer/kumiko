# Kumiko roadmap

## Completed foundation

- Product name and repository recommendation
- Course/exam catalog
- Course/exam-scoped persistence
- Automatic migration of existing ADBS SQLite data
- Generic JSON content provider
- Course and exam selector
- Dockerfile, Compose volume, non-root runtime, healthcheck
- Shared instructions for Codex and Claude Code

## Phase 1: finish modularization

Status markers: `[x]` done, `[~]` in progress, `[ ]` not started.

- [~] Split `app.js` into view and feature modules. Extracted so far:
  `core/html.js`, `core/i18n.js`, `core/exam-config.js`,
  `state/persistence.js`, `views/cypher-view.js`, plus `api.js`,
  `course-context.js`, `language-state.js`, `question-language.js`.
  Still inline: all nine view renderers, `navigate`, and `render`.
- [x] Split `styles.css` into tokens, layout, components, and feature styles.
  `styles.css` is now an `@import` barrel over `assets/css/`.
- [ ] Split `adbs_legacy.py` into loader, glossary enrichment, and question
  generation modules. Roughly half the file is literal data dictionaries, so
  this is mostly data extraction rather than restructuring.
- [~] Add route and catalog unit tests. Catalog is covered; no test imports
  `kumiko.web`, so the HTTP routes are still untested.
- [ ] Add browser smoke tests. Blocked on wanting zero dependencies; the
  current substitute is the manual click-through in `AGENTS.md`.

## Phase 2: generic course authoring

- Course creation UI
- Exam creation UI
- JSON schema validation with clear diagnostics
- Upload and organization of PDFs and notes
- Generic topic, glossary, example, and question editors
- Import/export one complete course bundle

## Phase 3: study intelligence

- Cross-course dashboard
- Calendar and exam deadlines
- Study plans based on exam date and mastery
- Session goals and streaks
- Weak-topic analysis
- Search across all courses

## Phase 4: richer learning modes

- Flashcards and free-text recall
- Coding/query example collections
- Calculation exercises with step-by-step solutions
- Essay questions and rubrics
- Configurable exam scoring models

## Phase 5: operational hardening

- Database migrations with schema versions
- Automated backups and restore UI
- Authentication for optional network deployment
- CSRF/security hardening for non-local use
- CI for tests and Docker builds
- Versioned course bundle format
- Cache versioning for `assets/js` modules, which are imported without a `?v=`
  query and are served without `Cache-Control`

## Next recommended feature

Complete the frontend split before adding another large feature. Persistence,
context, i18n, exam configuration, and the Cypher view are out of `app.js`.

The next extractions are the view renderers, in this order: practice, exam,
exam review, dashboard and learn, glossary, slides, question pool. `navigate`
and `render` should move last: their shape is determined by how the views are
extracted, so moving them earlier guarantees rework.
