import { DIFFICULTY_LABELS } from "../../../engine.mjs";

const VIEW_TITLES = {
  dashboard: { de: "Überblick", en: "Dashboard" },
  learn: { de: "Lernstoff", en: "Study notes" },
  coding: { de: "Cypher-Beispiele", en: "Cypher examples" },
  practice: { de: "Fragen trainieren", en: "Practice questions" },
  exam: { de: "Prüfungssimulation", en: "Exam simulation" },
  history: { de: "Prüfungsverlauf", en: "Exam history" },
  glossary: { de: "Glossar", en: "Glossary" },
  slides: { de: "Slides", en: "Slides" },
  library: { de: "Fragenpool", en: "Question pool" },
};

const UI = {
  "nav.dashboard": { de: "Überblick", en: "Dashboard" },
  "nav.learn": { de: "Lernstoff", en: "Study notes" },
  "nav.coding": { de: "Cypher", en: "Cypher" },
  "nav.practice": { de: "Fragen", en: "Questions" },
  "nav.exam": { de: "Prüfung", en: "Exam" },
  "nav.history": { de: "Prüfungsverlauf", en: "Exam history" },
  "nav.glossary": { de: "Glossar", en: "Glossary" },
  "nav.slides": { de: "Slides", en: "Slides" },
  "nav.library": { de: "Fragenpool", en: "Question pool" },
  "common.localOffline": { de: "lokal & offline", en: "local & offline" },
  "common.resetProgress": { de: "Fortschritt zurücksetzen", en: "Reset progress" },
};

const DIFFICULTY_LABELS_EN = {
  1: "Basic",
  2: "Easy",
  3: "Medium",
  4: "Hard",
  5: "Extreme",
};

export function isKnownView(view) {
  return Object.hasOwn(VIEW_TITLES, view ?? "");
}

export function translate(key, language) {
  return UI[key]?.[language] || UI[key]?.de || key;
}

export function translated(value, language) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value[language] ?? value.de ?? value.en ?? "";
  }
  return value ?? "";
}

export function viewTitleFor(view, language, navigation = null) {
  const navigationLabel = navigation?.[view];
  if (navigationLabel) return translated(navigationLabel, language);
  return VIEW_TITLES[view]?.[language] || VIEW_TITLES[view]?.de || view;
}

export function glossaryTerm(entry, language) {
  return language === "en"
    ? entry.translations?.en?.term || entry.term
    : entry.term;
}

export function glossaryDefinition(entry, language) {
  return language === "en"
    ? entry.translations?.en?.definition || entry.definition
    : entry.definition;
}

export function difficultyLabel(level, language) {
  const labels = {
    de: DIFFICULTY_LABELS,
    en: DIFFICULTY_LABELS_EN,
  };
  return labels[language][level] || DIFFICULTY_LABELS[level];
}
