# AGENTS.md

This is the authoritative project guide for Codex, Claude Code, and other
coding agents working on Kumiko.

## Product

Kumiko is a local-first study platform for a Master's degree. It must support:

- many courses;
- many exams per course;
- reusable learning features;
- course-specific content adapters where genuinely necessary;
- Docker deployment with persistent local data.

ADBS is the first course, not the product boundary.

Recommended repository name: `kumiko-study`.

## Required reading

Before architectural changes, read:

1. `README.md`
2. `docs/ARCHITECTURE.md`
3. `docs/ROADMAP.md`
4. `COURSE_FORMAT.md`

For ADBS content work, also read `QUESTION_FORMAT.md`.

## Commands

Use `uv`; do not use `pip` or global installs.

```bash
uv --cache-dir /tmp/adbs-uv-cache run python server.py
uv --cache-dir /tmp/adbs-uv-cache run python -m unittest discover -s tests -p "test_*.py" -v
node --test tests/*.test.mjs
node --check app.js
docker compose config
```

## Architecture boundaries

- `kumiko/config.py`: configuration only.
- `kumiko/catalog.py`: course/exam manifests only.
- `kumiko/content.py`: content-provider dispatch only.
- `kumiko/storage.py`: persistence and state validation only.
- `kumiko/web.py`: HTTP transport only.
- `kumiko/adbs_legacy.py`: temporary ADBS adapter. Do not add generic platform
  behavior here.
- `assets/js/`: reusable frontend modules.
- `app.js`: legacy ADBS UI controller. New independent features should be
  extracted into modules rather than making this file larger.

## Size and quality rules

- Target Python modules: <= 400 lines.
- Target frontend modules: <= 300 lines.
- A file may exceed the target only when it is data-heavy or a documented
  legacy module.
- Do not add another function to a legacy monolith when extracting a coherent
  module is practical.
- Keep pure domain logic separate from HTTP and DOM code.
- Add tests for schema, persistence, routing, scoring, and migrations.
- Prefer explicit data structures over implicit global state.

## Data invariants

- Every persisted learning record belongs to `course_id` and `exam_id`.
- Course IDs are globally unique.
- Exam IDs are unique inside a course.
- Question IDs are unique inside an exam content set.
- Existing questions are never hard-deleted. Use `archived` or `deleted`.
- Completed exam snapshots remain reviewable after content changes.
- User data must survive server and container restarts.

## Content rules

- Lecture material is the source of truth for exam scope.
- Important supplemental knowledge must be labeled as supplemental.
- German and English user-facing content should stay aligned.
- TMC questions use exact-match scoring and may have zero to all options
  correct.
- Every answer option needs a meaningful explanation.

## Docker rules

- The image runs as a non-root user.
- Runtime data goes to `/data`, never into the image layer.
- The app must expose `/health`.
- Never bake a real SQLite database into the image.
- Keep Docker startup equivalent to local startup.

## Safe change procedure

1. Inspect the current course and exam context.
2. Preserve existing user/content changes.
3. Implement the smallest coherent architecture step.
4. Run Python tests, JS tests, and syntax checks.
5. If HTTP changed, start the server and test `/health`, `/api/catalog`,
   `/api/state`, and the selected content endpoint.
6. Update architecture or roadmap docs when boundaries change.
