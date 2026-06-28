# Format für zusätzliche Fragen

Lege zusätzliche Dateien mit der Endung `.json` in `content/questions/` ab. Beim
Neuladen der App scannt der Server den Ordner automatisch. Alternativ kann eine
Datei unter **Fragenpool** direkt in die lokale SQLite-Datenbank importiert
werden.

Die vollständige Struktur:

```json
{
  "version": 1,
  "label": "Anzeigename des Fragenpakets",
  "questions": [
    {
      "id": "global-eindeutige-id",
      "topic": "nosql",
      "difficulty": 3,
      "status": "active",
      "languages": ["de", "en"],
      "prompt": "Welche Aussagen sind korrekt?",
      "context": "Optionaler Kontext",
      "options": [
        {
          "id": "a",
          "text": "Aussage",
          "correct": true,
          "explanation": "Begründung für diese Option"
        },
        {
          "id": "b",
          "text": "Weitere Aussage",
          "correct": false,
          "explanation": "Begründung für diese Option"
        }
      ],
      "explanation": "Gesamterklärung",
      "source": {
        "deck": "Quelle",
        "pages": "S. 1"
      },
      "tags": ["Begriff", "Rechnung"]
    }
  ]
}
```

Regeln:

- `version` muss `1` sein.
- Jede `id` muss über alle Dateien hinweg eindeutig sein.
- Gültige Themen sind `nosql`, `key-value`, `document`, `graph` und `column`.
- `difficulty` liegt zwischen `1` und `5`.
- `status` ist optional und kann `active`, `archived` oder `deleted` sein.
  Fehlt der Wert, gilt `active`.
- Jede Option benötigt eine eindeutige `id`, zweisprachige Felder für `text`
  und `explanation` sowie den booleschen Wert `correct`.
- Es dürfen 0 bis alle Optionen korrekt sein.
- Die App wertet ausschließlich exakte Auswahlmengen als richtig.
- `context`, `source` und `tags` sind optional, aber für anspruchsvolle Fragen
  empfehlenswert.

Ein direkt kopierbares Paket steht in
`examples/questions.example.json`.

## Mehrsprachige Felder

Jede Frage muss vollständig zweisprachig sein. Bei `prompt`, `context`,
`explanation`, `options[].text` und `options[].explanation` wird deshalb ein
Objekt mit deutschem und englischem Text verwendet:

```json
{
  "de": "Welche Aussagen sind korrekt?",
  "en": "Which statements are correct?"
}
```

`languages: ["de", "en"]` ist nur Metadaten und ersetzt keine Übersetzung.
Eine Frage gilt erst dann als zweisprachig, wenn Prompt, optionaler Kontext,
Gesamterklärung sowie Text und Erklärung jeder Antwortoption in beiden
Sprachen vorhanden sind. Unvollständige Fragen werden beim Laden oder Import
abgelehnt.

## Prompt-Vorlage für spätere KI-Fragen

```text
Erzeuge klausurnahe True-Multiple-Choice-Fragen zum Thema <THEMA>.
Verwende ausschließlich den bereitgestellten Vorlesungsstoff. Pro Aufgabe
können 0 bis alle Aussagen korrekt sein. Eine Aufgabe wird nur bei exakt
richtiger Auswahl gewertet. Liefere ausschließlich valides JSON im Format aus
QUESTION_FORMAT.md. Nutze global eindeutige IDs mit dem Präfix <PRAEFIX>.
Verteile die Schwierigkeit von 1 bis 5, begründe jede einzelne Option und gib
die genaue Folienquelle an. Baue neben Begriffsfragen auch Rechen-, Ablauf-,
Query-Auswertungs- und Prüfungsfallen ein.
```
