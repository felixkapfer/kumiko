function translated(value, language) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value[language] ?? value.de ?? value.en ?? "";
  }
  return value ?? "";
}

export function cypherViewHtml({
  material,
  language,
  selectedLevel,
  selectedCategory,
  difficultyLabel,
  escapeHtml,
}) {
  const examples = material.examples || [];
  const categories = [...new Set(examples.map((item) => item.category))];
  const visible = examples.filter(
    (example) =>
      (selectedLevel === "all" ||
        example.difficulty === Number(selectedLevel)) &&
      (selectedCategory === "all" ||
        example.category === selectedCategory),
  );
  const text = (value) => translated(value, language);
  const de = language === "de";

  return `
    <section class="coding-hero">
      <div>
        <p class="eyebrow">${examples.length} ${de ? "ausführbare Cypher-Beispiele" : "executable Cypher examples"}</p>
        <h2>${de ? "Cypher lesen, vergleichen und in Neo4j ausführen" : "Read, compare, and run Cypher in Neo4j"}</h2>
        <p>${de ? "Vorlesungsnahe Beispiele und klar markiertes Zusatzwissen decken elementare Patterns, Updates, Aggregation, Pfade, Subqueries und Performance ab." : "Lecture-aligned examples and clearly marked supplemental knowledge cover elementary patterns, updates, aggregation, paths, subqueries, and performance."}</p>
      </div>
      <div class="database-status">
        <span class="sync-dot"></span>
        <div><strong>Neo4j / Cypher</strong><span>${de ? "APOC-frei · Neo4j 5+" : "APOC-free · Neo4j 5+"}</span></div>
      </div>
    </section>

    <section class="panel cypher-core-difference">
      <p class="eyebrow">${de ? "Zentrale Unterscheidung" : "Core distinction"}</p>
      <h3>MATCH vs. WHERE</h3>
      <div class="comparison-grid">
        ${comparisonColumn("MATCH", material.matchVsWhere?.match, material.matchVsWhere?.matchExample, text, escapeHtml)}
        ${comparisonColumn("WHERE", material.matchVsWhere?.where, material.matchVsWhere?.whereExample, text, escapeHtml)}
      </div>
      <div class="example-box">${escapeHtml(text(material.matchVsWhere?.takeaway))}</div>
    </section>

    <details class="solution-details cypher-setup">
      <summary>${de ? "Gemeinsamen Beispielgraphen für Neo4j anzeigen" : "Show shared Neo4j example graph"}</summary>
      <div class="solution-content">
        <p>${escapeHtml(text(material.setup?.description))}</p>
        ${codeBlock("Cypher setup", material.setup?.query || "", escapeHtml)}
      </div>
    </details>

    ${filterRows({
      examples,
      categories,
      language,
      selectedLevel,
      selectedCategory,
      difficultyLabel,
      escapeHtml,
    })}

    <div class="coding-list">
      ${visible.map((example, index) =>
        exampleCard(example, index, language, difficultyLabel, escapeHtml)
      ).join("") || `<div class="empty-state">${de ? "Für diesen Filter gibt es keine Cypher-Beispiele." : "No Cypher examples match this filter."}</div>`}
    </div>
  `;
}

function comparisonColumn(label, description, query, text, escapeHtml) {
  return `<div><strong>${label}</strong><p>${escapeHtml(text(description))}</p><pre><code>${escapeHtml(query || "")}</code></pre></div>`;
}

function filterRows(options) {
  const {
    examples, categories, language, selectedLevel, selectedCategory,
    difficultyLabel, escapeHtml,
  } = options;
  const de = language === "de";
  const levels = [1, 2, 3, 4, 5]
    .map((level) => `<button class="chip ${selectedLevel === String(level) ? "active" : ""}" data-cypher-level="${level}">${level} · ${escapeHtml(difficultyLabel(level))}</button>`)
    .join("");
  const categoryButtons = categories.map((category) => {
    const count = examples.filter((item) => item.category === category).length;
    return `<button class="chip ${selectedCategory === category ? "active" : ""}" data-cypher-category="${escapeHtml(category)}">${escapeHtml(category)} · ${count}</button>`;
  }).join("");
  return `
    <div class="coding-filters">
      <span class="filter-label">${de ? "Schwierigkeit:" : "Difficulty:"}</span>
      <button class="chip ${selectedLevel === "all" ? "active" : ""}" data-cypher-level="all">${de ? "Alle" : "All"}</button>${levels}
    </div>
    <div class="coding-filters">
      <span class="filter-label">${de ? "Kategorie:" : "Category:"}</span>
      <button class="chip ${selectedCategory === "all" ? "active" : ""}" data-cypher-category="all">${de ? "Alle" : "All"} · ${examples.length}</button>${categoryButtons}
    </div>`;
}

function codeBlock(label, query, escapeHtml, extraClass = "") {
  return `<div class="code-block ${extraClass}"><div class="code-label">${label}</div><pre><code>${escapeHtml(query)}</code></pre></div>`;
}

function exampleCard(example, index, language, difficultyLabel, escapeHtml) {
  const de = language === "de";
  const text = (value) => translated(value, language);
  const scope = example.scope === "supplemental"
    ? `<span class="badge supplemental">${de ? "Wichtiges Zusatzwissen" : "Important supplement"}</span>`
    : `<span class="badge">${de ? "Vorlesungsnah" : "Lecture-aligned"}</span>`;
  const alternative = example.alternative
    ? codeBlock(de ? "Alternative / Vergleich" : "Alternative / comparison", example.alternative, escapeHtml)
    : "";
  const pitfall = example.pitfall
    ? `<div class="pitfall-box"><strong>${de ? "Klausurfalle:" : "Exam trap:"}</strong> ${escapeHtml(text(example.pitfall))}</div>`
    : "";
  return `
    <article class="coding-card" style="--topic-color:#ff8a5b">
      <header class="coding-card-header">
        <div class="question-meta">
          <span class="badge">${escapeHtml(example.category)}</span>
          <span class="badge difficulty-${example.difficulty}">${example.difficulty} · ${escapeHtml(difficultyLabel(example.difficulty))}</span>
          ${scope}
        </div>
        <span class="eyebrow">${escapeHtml(example.id)} · ${String(index + 1).padStart(2, "0")}</span>
      </header>
      <div class="coding-card-body">
        <h3>${escapeHtml(text(example.title))}</h3>
        <p>${escapeHtml(text(example.question))}</p>
        ${codeBlock("Cypher", example.query, escapeHtml, "solution-code")}
        ${alternative}
        <div class="cypher-explanation"><strong>${de ? "So liest du die Query" : "How to read the query"}</strong><p>${escapeHtml(text(example.explanation))}</p></div>
        <div class="example-box"><strong>${de ? "Ergebnisidee:" : "Result idea:"}</strong> ${escapeHtml(text(example.expectedResult))}</div>
        ${pitfall}
      </div>
    </article>`;
}
