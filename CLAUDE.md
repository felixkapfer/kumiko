# Claude Code context for Kumiko

Read [AGENTS.md](AGENTS.md) before making changes. It defines the product,
architecture boundaries, data invariants, commands, and file-size targets.

Kumiko is not an ADBS-only app. It is a local-first platform for multiple
Master's courses and multiple exams per course. ADBS remains operational
through a compatibility content provider while the old monolith is extracted
incrementally.

Primary architecture documents:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/ROADMAP.md](docs/ROADMAP.md)
- [COURSE_FORMAT.md](COURSE_FORMAT.md)

Do not expand `app.js` or `kumiko/adbs_legacy.py` with generic platform
features. Prefer small modules with tests.
