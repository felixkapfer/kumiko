# ADBS Exam Prep 2026

Lokale Lern-App für den aktuellen Prüfungsstoff:

- NoSQL, Verteilung und Konsistenz
- Key-Value Stores: Bitcask und LSM-Trees
- Document Stores und MongoDB
- Graphdatenbanken und Cypher
- Column Stores und Wide Column Stores

Die App enthält Zusammenfassungen, ein erweitertes Glossar, 250 aktive
True-Multiple-Choice-Aufgaben, Wiederholungsplanung, Prüfungssimulationen
mit Alles-oder-nichts-Wertung, 48 ausführliche Cypher-Beispiele, einen
DE/EN-Umschalter und einen integrierten Slides-Viewer.

## AI-Projektkontext

Für spätere Änderungen durch AI-Tools liegen kompakte Projektbeschreibungen im
Root:

- [CLAUDE.md](CLAUDE.md) für Claude
- [CODEX.md](CODEX.md) für Codex

Diese Dateien beschreiben Zweck, Struktur, wichtige Dateien, Inhaltsformate,
Soft-Delete-Regeln und die relevanten Start- und Testbefehle.

## Start

Im Projektordner:

```bash
uv --cache-dir /tmp/adbs-uv-cache run python server.py
```

Danach im Browser öffnen:

```text
http://127.0.0.1:8000
```

Es werden keine Python- oder JavaScript-Pakete benötigt. `uv` verwaltet nur die
lokale Python-Laufzeit; die App selbst verwendet Browser-APIs, SQLite und die
Python-Standardbibliothek.

## Lernlogik

- Eine Frage ist nur richtig, wenn exakt alle korrekten und keine falschen
  Optionen markiert sind.
- Falsch beantwortete Fragen werden in derselben Session nach einigen anderen
  Aufgaben erneut eingereiht.
- Zusätzlich plant die App zeitversetzte Wiederholungen über mehrere Stufen.
- Filter erlauben neue, fällige, zuletzt falsche, zuletzt richtige und bereits
  beherrschte Fragen.
- Richtige Fragen können jederzeit erneut eingeplant oder gezielt gefiltert
  werden.
- Fortschritt, Sprache, Frage-Overrides, importierte Fragen und
  Prüfungsverlauf werden dauerhaft in `data/adbs_exam_prep.sqlite3` gespeichert.
- Beim ersten Start nach dem Update werden vorhandene Browserdaten automatisch
  aus `localStorage` in SQLite migriert und anschließend aus dem Browser
  entfernt.
- Archivierte oder als gelöscht markierte Fragen bleiben erhalten, werden aber
  nicht mehr in Übung oder Prüfung verwendet.

## Prüfungsverlauf

Abgegebene Prüfungssimulationen werden vollständig in SQLite gespeichert. Die
Seite **Prüfungsverlauf** zeigt bis zu 25 Versuche
mit Datum, Dauer, Punktzahl und Themen. Jeder Versuch kann erneut in der
Einzelansicht mit Vor/Zurück-Navigation oder als vollständige scrollbare
Auswertung geöffnet werden.

Ein Neustart des lokalen Python-Servers, ein Browserwechsel oder das Löschen der
Browserdaten löscht den Verlauf nicht. Für ein Backup genügt es, die Datei
`data/adbs_exam_prep.sqlite3` bei gestopptem Server zu kopieren.

## Cypher-Beispiele

Der Tab **Cypher** enthält 48 zweisprachige, direkt lesbare und ausführbare
Beispiele von Einstieg bis Extrem:

- zentrale Erklärung von `MATCH` gegenüber `WHERE`
- Knoten-, Relationship- und Property-Patterns
- `OPTIONAL MATCH`, Projektion, `DISTINCT`, Sortierung und Paginierung
- Aggregation mit `count`, `collect`, `sum` und `WITH`
- `CREATE`, `MERGE`, `SET`, `REMOVE`, `DELETE` und Constraints
- variable Pfade, `shortestPath`, `allShortestPaths` und Pfadfunktionen
- `EXISTS`- und `CALL`-Subqueries sowie typische kartesische Produkte

Ein gemeinsamer Beispielgraph kann aus dem Tab kopiert und in einer leeren
lokalen Neo4j-Übungsdatenbank ausgeführt werden. Die Beispiele benötigen kein
APOC.

## Sprache

Oben rechts kann zwischen Deutsch und Englisch gewechselt werden.

- Deutsch zeigt alle 250 aktiven Fragen.
- Englisch zeigt die englisch verfügbaren aktiven Fragen und nutzt englische
  UI-, Glossar- und Lerntexte.
- Die 71 ursprünglichen deutschen Fragen bleiben unverändert erhalten und
  werden nicht automatisch übersetzt oder gelöscht.

## Slides

Der Tab **Slides** zeigt die PDFs aus `lecture_slides/` direkt in der App.

## Glossar

Der Glossarbereich enthält über 140 Begriffe. Jeder Eintrag enthält eine
eigens formulierte Erklärung ohne vorausgesetztes Fachwissen, einen kurzen
Klausur-Merksatz, eine thematische Einordnung in Stichpunkten, eine vollständige
Facherklärung, konkrete Anwendungsbeispiele, typische Verwechslungen und
beantwortete klausurnahe Fragen. Von dort kann direkt zum zugehörigen
Lernkapitel oder zu einer interaktiven Übungsfrage gewechselt werden. Die
Glossarliste kann nach Thema, Suchtext und Tags gefiltert werden.

Der Lernstoff ist innerhalb jedes Themenblocks über ein Kapitelverzeichnis
navigierbar. Pro Seite wird nur ein Unterkapitel angezeigt. Jedes Unterkapitel
enthält mindestens fünf passend eingeordnete Begriffe mit einfacher Erklärung
und Merksatz sowie fünf direkt startbare Übungsfragen. Dadurch bleibt die
einzelne Seite übersichtlich, während der gesamte Stoff deutlich ausführlicher
abgedeckt wird.

Nach dem Beantworten einer Frage erklärt jede Option den tatsächlich
beschriebenen Begriff oder Sachverhalt. Falsche Glossaroptionen verwenden keine
allgemeinen Texte wie „anderes Konzept“, sondern nennen Definition und
Einordnung des ausgewählten Begriffs.

## Eigene oder KI-generierte Fragen

Lege eine oder mehrere JSON-Dateien in `content/questions/` ab und lade die
Seite neu. Der Server liest alle Dateien automatisch ein. Ein Server-Neustart
ist nicht nötig.

Format und Prompt-Vorlage: [QUESTION_FORMAT.md](QUESTION_FORMAT.md)

Beispiel: [examples/questions.example.json](examples/questions.example.json)

Alternativ können JSON-Dateien in der Ansicht **Fragenpool** per Drag-and-drop
direkt in die SQLite-Datenbank importiert werden.

Wenn Fragen nicht mehr verwendet werden sollen, setze `status` auf
`"archived"` oder `"deleted"` oder archiviere sie im Fragenpool. Die Frage
bleibt dabei erhalten; das ist ein Soft Delete.

## Tests

Inhalts- und Servervalidierung:

```bash
uv --cache-dir /tmp/adbs-uv-cache run python -m unittest discover -s tests -p "test_*.py"
```

Bewertungs- und Auswahlalgorithmen verwenden nur den vorhandenen Node-Runtime:

```bash
node --test tests/engine.test.mjs
```

## Stoffabgrenzung

Die fünf Dateien in `lecture_slides/` bilden den aktuellen Stoff. Die
bereitgestellten Prüfungen aus 2025 wurden verwendet, um Aufgabenstil,
Schwierigkeitsgrad und Alles-oder-nichts-Wertung nachzubilden. Themen aus der
Altklausur ohne aktuellen Foliensatz wurden nicht als aktueller Stoff
übernommen.
