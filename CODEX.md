# Codex context for Kumiko

Read [AGENTS.md](AGENTS.md) first. It is the authoritative instruction file.

Kumiko is a multi-course, multi-exam study platform. ADBS is the first course
and currently uses `kumiko/adbs_legacy.py` as a compatibility adapter.

Key files:

- `kumiko/web.py`: HTTP server and API
- `kumiko/storage.py`: scoped SQLite persistence
- `kumiko/catalog.py`: course/exam manifests
- `kumiko/content.py`: content-provider dispatch
- `courses/*/course.json`: catalog entries
- `assets/js/`: reusable frontend modules
- `app.js`: legacy ADBS UI controller; reduce rather than grow
- `docs/ARCHITECTURE.md`: target boundaries
- `docs/ROADMAP.md`: migration sequence

Use:

```bash
uv --cache-dir /tmp/adbs-uv-cache run python server.py
uv --cache-dir /tmp/adbs-uv-cache run python -m unittest discover -s tests -p "test_*.py" -v
node --test tests/*.test.mjs
node --check app.js
```

Do not hard-delete questions or store user data outside the scoped SQLite
model. New generic features do not belong in `adbs_legacy.py`.
