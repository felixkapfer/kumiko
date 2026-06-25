# Claude Project Context: ADBS Exam Prep 2026

This repository contains a local, static-first learning app for the Advanced
Database Systems exam preparation. It helps study the current semester topics
from the lecture slides with summaries, a bilingual glossary,
True-Multiple-Choice practice questions, exam simulation, spaced repetition and
an integrated PDF slide viewer.

## Core goal

The app prepares for an all-or-nothing True-Multiple-Choice exam:

- A question is correct only if exactly all correct options and no incorrect
  options are selected.
- Questions may have zero, one, multiple or all options correct.
- Wrong questions should reappear later during practice.
- Existing questions must not be hard-deleted. Use `status: "archived"` or
  `status: "deleted"` for soft delete behavior.
- The app itself has no AI integration. New AI-generated content is added as
  JSON files under `content/questions/` or glossary/content JSON files.

## How to run

Use `uv` for Python commands. Do not use `pip`, global Python package installs,
or dependency managers that are not already part of the project.

```bash
uv --cache-dir /tmp/adbs-uv-cache run python server.py
```

Open:

```text
http://127.0.0.1:8000
```

No Python packages and no JavaScript packages are required. The server uses only
the Python standard library. The frontend uses browser APIs and plain ES
modules.

## Validation

Python/content tests:

```bash
uv --cache-dir /tmp/adbs-uv-cache run python -m unittest discover -s tests -p "test_*.py" -v
```

JavaScript logic tests:

```bash
node --test tests/engine.test.mjs
```

Syntax check if needed:

```bash
node --check app.js
```

## Important files

### Runtime and UI

- `server.py`  
  Local HTTP server. Serves static files, PDFs, `/api/content` and `/api/state`.
  It loads and validates topics, glossary entries and question files, persists
  user state in SQLite, and generates deterministic glossary drill questions
  so the active pool stays at 250 questions.

- `index.html`  
  App shell and main mount points.

- `app.js`  
  Main frontend controller. Handles navigation, language switching, practice
  mode, exam mode, glossary rendering, glossary detail pages, slide viewer,
  Cypher examples, question library and database-backed imports.

- `engine.mjs`  
  Pure reusable logic for exact-match scoring, progress updates, filtering,
  shuffling and exam generation. Prefer changing this file for algorithmic
  behavior so it remains testable.

- `styles.css`  
  Complete styling for the static app.

### Content

- `content/topics.json`  
  German topic summaries for the five current lecture topics.

- `content/topics.en.json`  
  English topic summaries.

- `content/glossary.json`  
  Base German glossary.

- `content/glossary.en.json`  
  English translations for base glossary entries.

- `content/glossary.extra.json`  
  Additional German glossary terms.

- `content/glossary.extra.en.json`  
  English translations for additional glossary terms.

- `content/glossary.details.json`  
  Curated detailed glossary pages for central concepts. Other glossary entries
  receive structured fallback details in `server.py`.

- `content/questions/*.json`  
  Handwritten question packages. The server scans every `.json` file in this
  directory automatically.

- `examples/questions.example.json`  
  Copyable example for adding new questions.

- `QUESTION_FORMAT.md`  
  Authoritative schema and prompt template for adding more questions.

### Source material

- `lecture_slides/`  
  Current semester material and the source of truth for exam topics:
  - `ADBS-NoSQL.pdf`
  - `ADBS-KeyValueStores.pdf`
  - `ADBS-DocumentStores.pdf`
  - `ADBS-Graph.pdf`
  - `ADBS-ColumnStores.pdf`

- `exam_2025/`  
  Previous exam PDFs. Use these only to calibrate question style and difficulty.
  Do not treat topics from the old exam as current unless they also appear in
  `lecture_slides/`.

### Tests and docs

- `tests/test_content.py`  
  Validates loaded content, counts, glossary details, language support, soft
  delete status values and generated question coverage.

- `tests/engine.test.mjs`  
  Validates exact-match scoring, progress scheduling, filters, exam generation
  and scoring.

- `README.md`  
  User-facing project overview.

## Data model notes

### Question package structure

Question files under `content/questions/` use this high-level structure:

```json
{
  "version": 1,
  "label": "Package label",
  "questions": [
    {
      "id": "globally-unique-id",
      "topic": "nosql",
      "difficulty": 3,
      "status": "active",
      "languages": ["de", "en"],
      "prompt": {"de": "Frage?", "en": "Question?"},
      "options": [
        {
          "id": "a",
          "text": {"de": "Aussage", "en": "Statement"},
          "correct": true,
          "explanation": {"de": "Begründung", "en": "Reason"}
        }
      ],
      "explanation": {"de": "Gesamterklärung", "en": "Overall explanation"},
      "source": {"deck": "ADBS-NoSQL", "pages": "S. 1"},
      "tags": ["CAP", "Consistency"]
    }
  ]
}
```

Use `QUESTION_FORMAT.md` as the exact source of truth.

Valid topics:

- `nosql`
- `key-value`
- `document`
- `graph`
- `column`

Valid status values:

- `active`
- `archived`
- `deleted`

Valid difficulty range:

- `1` easiest to `5` hardest.

### Glossary structure

Glossary entries are merged from base and extra files, then enriched in
`server.py`.

Typical fields:

- `term`
- `definition`
- `topic`
- `tags`
- `expansion` for abbreviations such as CAP
- `detail` with explanation, examples, pitfalls, possible exam questions and
  related terms

When adding important concepts, prefer adding curated details to
`content/glossary.details.json`. For minor terms, tags and definitions may be
enough because fallback details are generated.

## Current content state

- Five current topics.
- 143 glossary terms.
- 250 active German questions.
- At least 175 English-supported questions.
- 71 original handwritten German questions are preserved unchanged.
- Additional deterministic glossary drill questions are generated by
  `server.py` from the first base glossary entries to keep the pool at 250.

If you change question counts or generation rules, update tests intentionally.

## Implementation constraints

- Preserve existing content unless the user explicitly asks for replacement.
- Never hard-delete existing questions. Archive or mark as deleted.
- Keep the app local/offline-friendly.
- Do not add AI API calls to the app.
- Do not introduce package dependencies unless there is a strong reason.
- Use plain JSON content files for study material.
- Keep German and English modes consistent when adding user-facing content.
- If adding questions, include option-level explanations and source references.
- If changing scoring or scheduling, update `engine.mjs` and
  `tests/engine.test.mjs` together.
- If changing content loading or generated questions, update `server.py` and
  `tests/test_content.py` together.

## Common tasks

### Add new questions

1. Create a new `.json` file under `content/questions/`.
2. Follow `QUESTION_FORMAT.md`.
3. Use globally unique IDs.
4. Prefer bilingual fields if the question should appear in English mode.
5. Run the Python/content tests.

### Archive a question

Set:

```json
"status": "archived"
```

or:

```json
"status": "deleted"
```

Do not remove the object from the JSON file unless the user explicitly requires
physical deletion.

### Add glossary terms

1. Add German terms to `content/glossary.extra.json` or the base glossary if
   they are core.
2. Add English translations to the matching `.en.json` file.
3. Add `tags`.
4. Add curated details in `content/glossary.details.json` for high-value terms.
5. Run the Python/content tests.

### Add or rename slides

1. Put PDFs into `lecture_slides/`.
2. Update `SLIDES` in `server.py`.
3. Verify the Slides tab loads the file.

## Local state

User progress, exam history, archived imports and UI settings are stored in
`data/adbs_exam_prep.sqlite3`. Existing browser `localStorage` data is migrated
once when the database is empty. Tests must use temporary database files.
