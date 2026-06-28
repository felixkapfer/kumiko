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

- Split `app.js` into view and feature modules
- Split `styles.css` into tokens, layout, components, and feature styles
- Split `adbs_legacy.py` into loader, glossary enrichment, and question
  generation modules
- Add route and catalog unit tests
- Add browser smoke tests

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

## Next recommended feature

Complete the frontend split before adding another large feature. The first
extraction should move persistence/context, navigation, and the Cypher view out
of `app.js`, followed by practice and exam features.
