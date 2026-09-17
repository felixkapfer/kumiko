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

Die Daten liegen im Volume `kumiko-data`. Der Container lauscht intern auf Port
`8000` und besitzt einen Healthcheck. `docker-compose.override.yml` veröffentlicht
ihn nach außen auf `8080`, die App ist also unter `http://127.0.0.1:8080`
erreichbar.

Inhalte werden per `COPY` ins Image gebacken. Änderungen an `content/` oder
`courses/` erscheinen deshalb erst nach `docker compose up --build`.

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

## Lokale Daten sichern und wiederherstellen

Die Datenbanken unter `data/` sind absichtlich nicht in Git. Das interaktive
Skript erstellt dafür datierte Archive und schlägt `~/backups/kumiko` als
Sicherungsort vor:

```bash
./scripts/kumiko-data.sh backup
./scripts/kumiko-data.sh restore
```

Beim Wiederherstellen fragt es nach dem Ordner des neuen Klons. Vorhandene
`data/`-Daten werden nicht gelöscht, sondern in einen datierten
`data.before-restore-*`-Ordner verschoben. Docker-Daten im Volume
`kumiko-data` werden von diesem Skript nicht verändert.

Ein Standard-Archiv heißt zum Beispiel
`2026-09-17 - 23-21 - backup-kumiko-data.tar.gz`.

## Projektordner verschieben

Wenn der gesamte Projektordner verschoben wird, bleiben Git-Historie, lokale
`data/`-Daten und die virtuelle Umgebung erhalten. Vor dem Verschieben sollte
ein Backup erstellt und die App beendet werden. Anschließend den ganzen
Projektordner (nicht nur dessen sichtbare Dateien) mit `mv` verschieben:

```bash
mv /alter/pfad/kumiko /neuer/pfad/kumiko
```

Der Zielordner `kumiko` darf dabei noch nicht existieren. Falls er nur als
leerer, zuvor angelegter Ordner existiert, kann er mit `rmdir` entfernt werden;
`rmdir` funktioniert ausschließlich bei leeren Ordnern.

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
