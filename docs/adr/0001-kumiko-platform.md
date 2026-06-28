# ADR 0001: Kumiko as a multi-course platform

Status: accepted

## Decision

The product is named **Kumiko** and the recommended repository name is
`kumiko-study`.

The application is modeled around courses and exams rather than around ADBS.
ADBS is integrated through a compatibility provider.

## Rationale

Kumiko describes a Japanese joinery/lattice technique in which many precise
pieces form a larger structure. This is an appropriate metaphor for a modular
study system assembled from courses, exams, topics, questions, and learning
records.

## Consequences

- Generic platform code cannot depend on ADBS topic IDs.
- Persistence is scoped by course and exam.
- New course types use provider interfaces.
- Existing monoliths are isolated and reduced incrementally.
- The physical repository directory may be renamed separately when desired;
  code and documentation already use the product identity.
