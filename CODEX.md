# Codex Project Context: ADBS Exam Prep 2026

This is a local exam-prep web app for the Advanced Database Systems course.
Start here when modifying the project.

## Operating rules

- Use `uv` for Python commands:

  ```bash
  uv --cache-dir /tmp/adbs-uv-cache run python server.py
  ```

- Do not use `pip`, global installs, or new package managers.
- Do not add runtime dependencies unless explicitly required.
- Preserve user content. Existing questions must not be hard-deleted.
- Use soft delete semantics for questions:
  - `status: "archived"`
  - `status: "deleted"`
- The app must remain local/offline-friendly and must not call AI APIs.
- Keep German and English content aligned when adding user-facing content.

## What the app does

The app helps prepare for an all-or-nothing True-Multiple-Choice exam.

- Exact-match scoring: full points only if the selected option IDs equal the
  correct option IDs.
- Practice mode: wrong questions are reinserted later.
- Review scheduling: progress is stored in local SQLite.
- Exam mode: shuffled questions/options and final scoring.
- Exam history: up to 25 completed exam snapshots in local SQLite,
  including questions, selections, option order and review data.
- Glossary: searchable/filterable, bilingual, with detail pages.
- Slides: PDFs from `lecture_slides/` are viewable in-app.
- Questions: loaded from JSON files and deterministic generated glossary drills.

## Repository map

```text
.
├── app.js                         # main frontend controller
├── engine.mjs                     # pure quiz/scoring/filtering logic
├── index.html                     # static app shell
├── server.py                      # stdlib HTTP server + content loader/API
├── styles.css                     # app styles
├── README.md                      # user-facing docs
├── QUESTION_FORMAT.md             # schema for additional questions
├── data/                           # generated SQLite database (gitignored)
├── content/
│   ├── cypher_examples.json        # 48 bilingual Neo4j/Cypher examples
│   ├── topics.json                # German topic summaries
│   ├── topics.en.json             # English topic summaries
│   ├── glossary.json              # base German glossary
│   ├── glossary.en.json           # base English glossary translations
│   ├── glossary.extra.json        # extra German glossary terms
│   ├── glossary.extra.en.json     # extra English glossary translations
│   ├── glossary.details.json      # curated detail pages for key terms
│   └── questions/                 # handwritten question packages
├── lecture_slides/                # current semester source PDFs
├── exam_2025/                     # old exam PDFs, style calibration only
├── examples/questions.example.json
└── tests/
    ├── test_content.py            # content/server validation
    └── engine.test.mjs            # JS logic validation
```

## Key implementation details

### `server.py`

Responsibilities:

- Serve static assets.
- Serve PDFs from `lecture_slides/`.
- Expose `/api/content`.
- Expose `/api/state` and persist user state in SQLite.
- Load topics, glossary and all `content/questions/*.json`.
- Validate question packages.
- Merge German/English glossary data.
- Enrich glossary entries with tags, matching study sections, concrete examples,
  misconceptions and answered questions from the handwritten pool.
- Attach at least five study concepts and five relevant questions to every
  chapter so the frontend can render one bounded chapter at a time.
- Generate deterministic glossary drill questions.
- Keep the active German question pool at 250.

Important symbols:

- `STATUS_VALUES`
- `BASE_GLOSSARY_QUESTION_COUNT`
- `SLIDES`
- `validate_question`
- `localize_glossary`
- `enrich_glossary`
- `generate_glossary_questions`

### `app.js`

Responsibilities:

- Navigation and rendering.
- DE/EN language toggle.
- Practice sessions.
- Exam simulation.
- Glossary list and detail pages.
- Tag/topic/search filtering.
- Slides tab.
- Executable Cypher example library from basic patterns to advanced subqueries.
- Question library and database-backed imports.
- Local archive/restore overrides.

State is stored in `data/adbs_exam_prep.sqlite3`. Existing `localStorage` data
is imported once on first startup when the database is still empty.

Completed exam snapshots use `adbs-exam-prep-exam-history-v1`. They must remain
reviewable after reloads and server restarts. The history UI supports summary,
single-question navigation and a scrollable all-questions review.

### `engine.mjs`

Pure logic. Prefer editing this file for algorithmic changes because it is easy
to test.

Contains:

- exact-match scoring
- shuffled exam generation
- progress update logic
- due/wrong/correct/mastered filtering

## Current expected content counts

Tests currently assume:

- 5 topics
- at least 140 glossary entries
- every glossary entry has tags and detail
- 5 slides
- 250 active German questions
- at least 175 English-supported questions
- at least one zero-correct and one all-correct question

If a requested change intentionally changes these values, update
`tests/test_content.py` with the implementation.

## Commands

Run app:

```bash
uv --cache-dir /tmp/adbs-uv-cache run python server.py
```

Run Python/content tests:

```bash
uv --cache-dir /tmp/adbs-uv-cache run python -m unittest discover -s tests -p "test_*.py" -v
```

Run JavaScript logic tests:

```bash
node --test tests/engine.test.mjs
```

Check JS syntax:

```bash
node --check app.js
```

## Adding questions

Use `QUESTION_FORMAT.md` as the authoritative schema.

Minimal rules:

- File location: `content/questions/*.json`
- `version` must be `1`.
- `id` must be globally unique.
- `topic` must be one of:
  - `nosql`
  - `key-value`
  - `document`
  - `graph`
  - `column`
- `difficulty` must be `1` to `5`.
- `status` is optional; default is `active`.
- Options need unique IDs and boolean `correct`.
- There may be 0 to all correct options.
- Add option-level explanations.
- Add source references from `lecture_slides/`.
- Prefer bilingual fields:
  - `prompt`
  - `context`
  - `explanation`
  - `options[].text`
  - `options[].explanation`

Do not remove old question objects. Archive them if needed.

## Adding glossary content

Use these files:

- German: `content/glossary.extra.json`
- English: `content/glossary.extra.en.json`
- Curated details: `content/glossary.details.json`

Each useful glossary entry should have:

- clear definition
- topic
- tags
- abbreviation expansion if applicable
- related terms where useful
- curated detail for central exam concepts

Details are generated from the matching study section and relevant handwritten
questions. Central concepts should additionally have manual detail pages.
Generic exam-relevance filler text is intentionally forbidden by the content
tests.

Generated question feedback must name and define the concept represented by
every option. Phrases such as "denotes a different concept" are intentionally
forbidden by the tests.

## Slides and source material

Current exam-relevant PDFs are in `lecture_slides/`:

- `ADBS-NoSQL.pdf`
- `ADBS-KeyValueStores.pdf`
- `ADBS-DocumentStores.pdf`
- `ADBS-Graph.pdf`
- `ADBS-ColumnStores.pdf`

If slides change:

1. Add or rename the PDF.
2. Update `SLIDES` in `server.py`.
3. Check the Slides tab.

Old exams are in `exam_2025/`. They are useful for style and difficulty only.
Do not add old-exam-only topics as current exam material unless they are also in
the current slides.

## Safe modification checklist

Before finishing a change:

1. Verify content/schema changes with:

   ```bash
   uv --cache-dir /tmp/adbs-uv-cache run python -m unittest discover -s tests -p "test_*.py" -v
   ```

2. If frontend logic changed, run:

   ```bash
   node --test tests/engine.test.mjs
   ```

3. If `app.js` changed, run:

   ```bash
   node --check app.js
   ```

4. Keep generated/cache files out of commits:
   - `.venv/`
   - `__pycache__/`
   - `.uv-cache/`

## Common pitfalls

- Do not reduce the active question pool accidentally.
- Do not break English mode by adding German-only generated content without
  language metadata.
- Do not physically delete questions when the user asks to remove them from
  practice.
- Do not treat browser-imported archived questions as server content.
- Do not edit lecture slide PDFs unless explicitly requested.
- Test SQLite persistence with temporary database files.
