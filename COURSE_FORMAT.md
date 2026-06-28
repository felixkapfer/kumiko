# Course manifest format

Kumiko discovers courses from:

```text
courses/<course-id>/course.json
```

Schema version 1:

```json
{
  "version": 1,
  "id": "adbs",
  "code": "ADBS",
  "title": "Advanced Database Systems",
  "university": "TU Wien",
  "degree": "Masterstudium",
  "semester": "Sommersemester 2026",
  "description": "Short course description.",
  "color": "#b8f34a",
  "status": "active",
  "defaultExamId": "practical-test-3-2026",
  "exams": [
    {
      "id": "practical-test-3-2026",
      "title": "Practical Test 3 · 2026",
      "date": null,
      "provider": "adbs-legacy"
    }
  ]
}
```

## Providers

### `adbs-legacy`

Compatibility provider for the current ADBS content. It requires no
`contentPath`.

### `json-v1`

Loads one complete content payload relative to the course directory:

```json
{
  "id": "final-2027",
  "title": "Final Exam 2027",
  "provider": "json-v1",
  "contentPath": "exams/final-2027/content.json"
}
```

The content payload currently follows the ADBS frontend contract:

- `topics`
- `glossary`
- `questions`
- `sources`
- `slides`
- `errors`

Optional generic fields:

- `scoring`: exam scoring model. If omitted, the frontend uses exact-match
  scoring. `type: "signed-selection"` supports multiple-choice scoring with
  positive points for correctly selected options and negative points for
  incorrectly selected options.
- `navigation`: localized labels for reusable navigation slots. Example:
  `{ "coding": { "de": "Paper", "en": "Paper" } }`.
- `paperStudy`: structured learning material for a paper-focused exam part.

This contract will be formalized into independent module schemas in a later
roadmap phase.
