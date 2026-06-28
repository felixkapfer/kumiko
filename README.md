# Kumiko

Kumiko ist eine lokale, Docker-fähige Lernplattform für mehrere Kurse und
mehrere Klausuren pro Kurs. ADBS ist der erste vollständig integrierte Kurs.

Der Name ist bewusst gewählt: Bei der japanischen Kumiko-Technik entsteht aus
vielen präzise gefügten Einzelteilen ein stabiles Gesamtwerk. Dasselbe Prinzip
gilt für die Plattform: Kurse, Klausuren, Lernmodule, Fragen und Fortschritt
bleiben getrennte Bausteine.

Empfohlener Repository-Name: `kumiko-study`.

## Aktueller Funktionsumfang

- Kurs- und Klausurauswahl über einen automatisch geladenen Katalog
- ADBS-Lernstoff, Glossar, Slides und 250 aktive TMC-Fragen
- AIR-Lernstoff, Paper-Lernsektion, Glossar, Slides und MC-Fragen mit
  Teilpunkten/Minuspunkten
- ADBS-Prüfungssimulation mit Alles-oder-nichts-Wertung
- Kursabhängige Prüfungssimulation für exact-match und AIR-Multiple-Choice
  Scoring
- Wiederholungsplanung und kurs-/klausurspezifischer Fortschritt
- SQLite-Persistenz mit Migration der bisherigen ADBS-Daten
- 66 ausführliche Cypher-Beispiele von Grundlagen bis Extrem
- DE/EN-Umschaltung
- Dockerfile und Compose-Konfiguration

## Lokal starten

```bash
uv --cache-dir /tmp/adbs-uv-cache run python server.py
```

Danach `http://127.0.0.1:8000` öffnen.

## Mit Docker starten

```bash
docker compose up --build
```

Die Daten liegen im Volume `kumiko-data`. Der Container veröffentlicht Port
`8000` und besitzt einen Healthcheck.

## Kurse und Klausuren

Jeder Kurs liegt unter `courses/<course-id>/course.json`. Ein Kurs kann mehrere
Klausuren definieren. Der Katalog wird beim Serverstart automatisch geladen.

ADBS verwendet aktuell den Provider `adbs-legacy`, damit die vorhandenen
Inhalte ohne riskante Migration weiter funktionieren. Neue Kurse können den
generischen Provider `json-v1` verwenden.

Das genaue Format steht in [COURSE_FORMAT.md](COURSE_FORMAT.md).

## Architektur

Die neue Plattformschicht ist modular:

```text
kumiko/
├── config.py        # Umgebungsvariablen und Pfade
├── catalog.py       # Kurse und Klausuren
├── content.py       # Content-Provider
├── storage.py       # kurs-/klausurspezifische SQLite-Persistenz
├── web.py           # HTTP/API und statische Dateien
└── adbs_legacy.py   # bestehende ADBS-Inhaltslogik, schrittweise zu zerlegen
```

Das Frontend nutzt ES-Module unter `assets/js/` für API- und Kurskontext.
`app.js` ist noch der bestehende ADBS-UI-Controller und wird gemäß Roadmap
weiter in Views und Features aufgeteilt.

Mehr Details:

- [AGENTS.md](AGENTS.md): verbindliche Regeln für Codex und Claude Code
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): Zielarchitektur und Datenfluss
- [docs/ROADMAP.md](docs/ROADMAP.md): schrittweiser Ausbau

## Persistenz

Standardmäßig wird `data/kumiko.sqlite3` verwendet. Im Container ist der
Standardpfad `/data/kumiko.sqlite3`.

Gespeichert werden:

- ausgewählter Kurs und ausgewählte Klausur
- Sprache
- Lernfortschritt und Wiederholungsintervalle
- Frage-Overrides und importierte Fragen
- vollständiger Prüfungsverlauf

Bestehende Daten aus `data/adbs_exam_prep.sqlite3` werden einmalig in den
ADBS-Kurskontext migriert, wenn die neue Datenbank noch leer ist.

## Konfiguration

Siehe [.env.example](.env.example):

- `KUMIKO_HOST`
- `KUMIKO_PORT`
- `KUMIKO_DATA_DIR`
- `KUMIKO_COURSES_DIR`
- `KUMIKO_DATABASE_NAME`

## Tests

```bash
uv --cache-dir /tmp/adbs-uv-cache run python -m unittest discover -s tests -p "test_*.py" -v
node --test tests/*.test.mjs
node --check app.js
```

## Entwicklungsprinzipien

- Keine neuen Monolithen: neue Python-Module möglichst unter 400 Zeilen,
  Frontend-Module möglichst unter 300 Zeilen.
- Fachlogik bleibt unabhängig von HTTP und DOM testbar.
- Nutzerinhalte werden nie hart gelöscht.
- Persistenz ist immer nach Kurs und Klausur getrennt.
- Neue Features werden generisch implementiert oder klar als kursspezifischer
  Adapter gekennzeichnet.
- ADBS-Funktionen dürfen beim Plattformumbau nicht regressieren.
