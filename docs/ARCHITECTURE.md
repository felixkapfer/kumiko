# Kumiko architecture

## Goal

Kumiko is a local-first study platform organized as:

```text
Platform
└── Course
    └── Exam
        ├── topics
        ├── study notes
        ├── questions
        ├── examples
        ├── glossary
        ├── source documents
        └── user progress
```

The platform layer must never assume ADBS topic IDs or exam rules.

## Runtime

```text
Browser
  ├── GET /api/catalog
  ├── GET /api/courses/{course}/exams/{exam}/content
  └── GET/PUT /api/state
             │
             ▼
       Kumiko HTTP layer
        ├── catalog
        ├── content providers
        └── scoped state store
             │
             ▼
        SQLite in /data
```

## Backend modules

### Configuration

`kumiko/config.py` maps environment variables to immutable settings.

### Catalog

`kumiko/catalog.py` discovers and validates course manifests. It has no HTTP or
database responsibilities.

### Content providers

`kumiko/content.py` resolves an exam provider:

- `adbs-legacy`: existing generated ADBS payload;
- `json-v1`: generic JSON content payload.

Future providers should implement the same normalized payload contract. Generic
payloads may include exam-specific scoring metadata, localized navigation
labels for reusable frontend slots, and structured paper-study material.

### State store

`kumiko/storage.py` stores state under the composite scope:

```text
(course_id, exam_id, entity_id)
```

Progress from one exam can therefore never overwrite another exam.

### HTTP

`kumiko/web.py` maps requests to catalog, content, and storage services. Domain
validation must remain outside request handlers where possible.

## Frontend

The browser first loads the catalog, then the persisted context, then content
for the selected course/exam.

Reusable modules currently exist for:

- API access;
- course/exam context normalization.

The remaining `app.js` controller is legacy code. It must be split by feature:

```text
assets/js/
├── core/
├── state/
├── views/
├── features/practice/
├── features/exams/
├── features/glossary/
└── features/content-library/
```

## Compatibility boundary

`kumiko/adbs_legacy.py` is intentionally isolated. It still contains the old
ADBS content enrichment and generated-question logic. It may call generic
helpers, but generic code must not depend on it.

## Deployment

The same entry point runs locally and in Docker. The container:

- runs as a non-root user;
- listens on `0.0.0.0:8000`;
- stores SQLite data in `/data`;
- exposes a healthcheck;
- contains course content but no user database.
