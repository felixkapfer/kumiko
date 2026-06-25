import {
  DIFFICULTY_LABELS,
  buildExam,
  exactMatch,
  formatDue,
  masteryForTopic,
  questionStatus,
  scoreExam,
  selectQuestions,
  shuffle,
  updateProgress,
} from "./engine.mjs";

const STORAGE_KEY = "adbs-exam-prep-state-v1";
const CUSTOM_KEY = "adbs-exam-prep-custom-questions-v1";
const OVERRIDES_KEY = "adbs-exam-prep-question-overrides-v1";
const LANGUAGE_KEY = "adbs-exam-prep-language-v1";
const EXAM_HISTORY_KEY = "adbs-exam-prep-exam-history-v1";
const MAX_EXAM_HISTORY = 25;
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

const state = {
  data: null,
  progress: {},
  questionOverrides: {},
  customQuestions: [],
  language: "de",
  currentView: "dashboard",
  learnTopic: null,
  learnSection: 0,
  selectedSlide: "nosql",
  practice: {
    queue: [],
    index: 0,
    feedback: null,
    selected: [],
    optionOrder: {},
    sessionCorrect: 0,
    sessionAnswered: 0,
    filters: {
      topics: [],
      difficulties: [],
      status: "all",
      shuffle: true,
      limit: "20",
    },
  },
  exam: null,
  examHistory: [],
  glossaryQuery: "",
  glossaryTopic: "all",
  glossaryTag: "all",
  selectedGlossaryTerm: null,
  cypherLevel: "all",
  cypherCategory: "all",
};

const content = document.querySelector("#app-content");
const viewTitle = document.querySelector("#view-title");
const sidebar = document.querySelector(".sidebar");
let toastTimer = null;
let examTimer = null;
let persistenceQueue = Promise.resolve();
let persistenceErrorShown = false;

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function tr(key) {
  return UI[key]?.[state.language] || UI[key]?.de || key;
}

function localized(value) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value[state.language] ?? value.de ?? value.en ?? "";
  }
  return value ?? "";
}

function glossaryTerm(entry) {
  return state.language === "en"
    ? entry.translations?.en?.term || entry.term
    : entry.term;
}

function glossaryDefinition(entry) {
  return state.language === "en"
    ? entry.translations?.en?.definition || entry.definition
    : entry.definition;
}

function viewLabel(view) {
  return VIEW_TITLES[view]?.[state.language] || VIEW_TITLES[view]?.de || view;
}

function difficultyLabel(level) {
  const labels = {
    de: DIFFICULTY_LABELS,
    en: {
      1: "Basic",
      2: "Easy",
      3: "Medium",
      4: "Hard",
      5: "Extreme",
    },
  };
  return labels[state.language][level] || DIFFICULTY_LABELS[level];
}

function dueLabel(timestamp) {
  if (state.language === "de") return formatDue(timestamp);
  if (!timestamp || timestamp <= Date.now()) return "now";
  const delta = timestamp - Date.now();
  const minutes = Math.ceil(delta / 60000);
  if (minutes < 60) return `in ${minutes} min`;
  const hours = Math.ceil(minutes / 60);
  if (hours < 48) return `in ${hours} h`;
  return `in ${Math.ceil(hours / 24)} days`;
}

function updateStaticLanguage() {
  document.documentElement.lang = state.language;
  viewTitle.textContent = viewLabel(state.currentView);
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = tr(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-label]").forEach((button) => {
    const number = button.querySelector("span")?.outerHTML || "";
    button.innerHTML = `${number} ${tr(button.dataset.i18nLabel)}`;
  });
  document.querySelectorAll(".lang-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.language === state.language);
  });
}

function statePayload() {
  return {
    version: 1,
    progress: state.progress,
    questionOverrides: state.questionOverrides,
    customQuestions: state.customQuestions,
    language: state.language,
    examHistory: state.examHistory.slice(0, MAX_EXAM_HISTORY),
  };
}

function saveState() {
  const payload = JSON.stringify(statePayload());
  const operation = persistenceQueue.then(async () => {
    const response = await fetch("/api/state", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: payload,
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `HTTP ${response.status}`);
    }
    persistenceErrorShown = false;
  });
  persistenceQueue = operation.catch((error) => {
    console.error("Database persistence failed:", error);
    if (!persistenceErrorShown && state.data) {
      persistenceErrorShown = true;
      showToast(
        state.language === "de"
          ? `Speichern in der Datenbank fehlgeschlagen: ${error.message}`
          : `Saving to the database failed: ${error.message}`,
      );
    }
  });
  return operation;
}

function legacyBrowserState() {
  const legacy = {
    progress: {},
    questionOverrides: {},
    customQuestions: [],
    language: localStorage.getItem(LANGUAGE_KEY) || "de",
    examHistory: [],
  };
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    legacy.progress = stored.progress || {};
  } catch {
    legacy.progress = {};
  }
  try {
    legacy.questionOverrides = JSON.parse(
      localStorage.getItem(OVERRIDES_KEY) || "{}",
    );
  } catch {
    legacy.questionOverrides = {};
  }
  try {
    const storedHistory = JSON.parse(
      localStorage.getItem(EXAM_HISTORY_KEY) || "[]",
    );
    legacy.examHistory = Array.isArray(storedHistory)
      ? storedHistory
          .filter(
            (entry) =>
              entry &&
              entry.id &&
              Array.isArray(entry.questions) &&
              entry.answers &&
              entry.finishedAt,
          )
          .sort((a, b) => b.finishedAt - a.finishedAt)
          .slice(0, MAX_EXAM_HISTORY)
      : [];
  } catch {
    legacy.examHistory = [];
  }
  try {
    legacy.customQuestions = JSON.parse(
      localStorage.getItem(CUSTOM_KEY) || "[]",
    );
  } catch {
    legacy.customQuestions = [];
  }
  legacy.hasData = Boolean(
    Object.keys(legacy.progress).length ||
      Object.keys(legacy.questionOverrides).length ||
      legacy.customQuestions.length ||
      legacy.examHistory.length ||
      localStorage.getItem(LANGUAGE_KEY),
  );
  return legacy;
}

function normalizeCustomQuestions(questions = []) {
  return questions.map((question) => {
    const status = question.status || question._status || "active";
    return {
      status,
      ...question,
      _status: status,
      _sourceFile: question._sourceFile || "Database import",
      _languages: question._languages || question.languages || [
        "de",
        ...(question.prompt?.en ||
        question.options?.some((option) => option.text?.en)
          ? ["en"]
          : []),
      ],
    };
  });
}

function applyStoredState(stored) {
  state.progress = stored.progress || {};
  state.questionOverrides = stored.questionOverrides || {};
  state.customQuestions = normalizeCustomQuestions(stored.customQuestions);
  state.language = stored.language || "de";
  state.examHistory = Array.isArray(stored.examHistory)
    ? stored.examHistory
        .filter(
          (entry) =>
            entry &&
            entry.id &&
            Array.isArray(entry.questions) &&
            entry.answers &&
            entry.finishedAt,
        )
        .sort((a, b) => b.finishedAt - a.finishedAt)
        .slice(0, MAX_EXAM_HISTORY)
    : [];
}

function clearLegacyBrowserState() {
  [
    STORAGE_KEY,
    CUSTOM_KEY,
    OVERRIDES_KEY,
    LANGUAGE_KEY,
    EXAM_HISTORY_KEY,
  ].forEach((key) => localStorage.removeItem(key));
}

async function loadState() {
  const response = await fetch("/api/state", { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const stored = await response.json();
  if (stored.hasData) {
    applyStoredState(stored);
    return;
  }

  const legacy = legacyBrowserState();
  applyStoredState(legacy);
  if (legacy.hasData) {
    await saveState();
    clearLegacyBrowserState();
  }
}

function customQuestions() {
  return normalizeCustomQuestions(state.customQuestions);
}

async function loadContent() {
  const response = await fetch("/api/content", { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const data = await response.json();
  const imported = customQuestions();
  const knownIds = new Set(data.questions.map((question) => question.id));
  data.questions.push(
    ...imported.filter((question) => {
      if (knownIds.has(question.id)) return false;
      knownIds.add(question.id);
      return true;
    }),
  );
  data.sources.push({
    file: "Database import",
    label: "In SQLite importierte Fragen",
    count: imported.length,
  });
  state.data = data;
  state.learnTopic = data.topics[0]?.id || null;
  document.querySelector("#sidebar-question-count").textContent =
    sidebarCountLabel();
}

function questionLifecycle(question) {
  return (
    state.questionOverrides[question.id]?.status ||
    question._status ||
    question.status ||
    "active"
  );
}

function supportsLanguage(question, language = state.language) {
  if (language === "de") return true;
  if (question._languages?.includes(language)) return true;
  if (question.languages?.includes(language)) return true;
  return Boolean(
    question.prompt?.[language] ||
      question.context?.[language] ||
      question.options?.some((option) => option.text?.[language]),
  );
}

function activeQuestions(language = state.language) {
  return state.data.questions.filter(
    (question) =>
      questionLifecycle(question) === "active" && supportsLanguage(question, language),
  );
}

function sidebarCountLabel() {
  const count = state.data ? activeQuestions().length : 0;
  const suffix = state.language === "de" ? "aktive Fragen" : "active questions";
  return `${count} ${suffix}`;
}

function showToast(message) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("visible"), 2600);
}

function topicById(id) {
  return state.data.topics.find((topic) => topic.id === id);
}

function topicContent(topic) {
  if (!topic) return null;
  if (state.language === "en" && topic.translations?.en) {
    return { ...topic, ...topic.translations.en, color: topic.color, deck: topic.deck, pages: topic.pages };
  }
  return topic;
}

function questionById(id) {
  return state.data.questions.find((question) => question.id === id);
}

function topicQuestions(id) {
  return activeQuestions().filter((question) => question.topic === id);
}

function navigate(view) {
  if (!VIEW_TITLES[view]) return;
  if (view !== "exam") clearInterval(examTimer);
  state.currentView = view;
  viewTitle.textContent = viewLabel(view);
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });
  sidebar.classList.remove("open");
  render();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function render() {
  if (!state.data) return;
  const renderers = {
    dashboard: renderDashboard,
    learn: renderLearn,
    coding: renderCypherExamples,
    practice: renderPractice,
    exam: renderExam,
    history: renderExamHistory,
    glossary: renderGlossary,
    slides: renderSlides,
    library: renderLibrary,
  };
  renderers[state.currentView]();
  updateStaticLanguage();
  document.querySelector("#sidebar-question-count").textContent = sidebarCountLabel();
}

function stats() {
  const values = Object.values(state.progress);
  const attempts = values.reduce((sum, item) => sum + (item.attempts || 0), 0);
  const correct = values.reduce((sum, item) => sum + (item.correct || 0), 0);
  const questions = activeQuestions();
  const due = questions.filter((question) => {
    const status = questionStatus(state.progress[question.id]);
    return status === "due" || status === "wrong";
  }).length;
  const mastered = questions.filter(
    (question) => questionStatus(state.progress[question.id]) === "mastered",
  ).length;
  return {
    attempts,
    accuracy: attempts ? Math.round((correct / attempts) * 100) : 0,
    due,
    mastered,
    mastery: questions.length
      ? Math.round((mastered / questions.length) * 100)
      : 0,
  };
}

function renderDashboard() {
  const current = stats();
  const topicRows = state.data.topics
    .map((topic, index) => {
      const view = topicContent(topic);
      const questions = topicQuestions(topic.id);
      const mastery = masteryForTopic(questions, state.progress);
      return `
        <article class="topic-card" data-open-topic="${escapeHtml(topic.id)}" style="--topic-color:${escapeHtml(topic.color)}">
          <span class="topic-index">0${index + 1}</span>
          <h3>${escapeHtml(view.title)}</h3>
          <div class="progress-track"><div class="progress-fill" style="width:${mastery}%"></div></div>
          <div class="meta"><span>${questions.length} ${state.language === "de" ? "Fragen" : "questions"}</span><span>${mastery}%</span></div>
        </article>
      `;
    })
    .join("");

  const priorities = [...state.data.topics]
    .map((topic) => ({
      topic,
      mastery: masteryForTopic(topicQuestions(topic.id), state.progress),
    }))
    .sort((a, b) => a.mastery - b.mastery)
    .map(
      ({ topic, mastery }, index) => {
        const view = topicContent(topic);
        return `
        <div class="priority-row">
          <span class="priority-number">${String(index + 1).padStart(2, "0")}</span>
          <div><strong>${escapeHtml(view.title)}</strong><br><small>${state.language === "de" ? (mastery < 20 ? "Grundlagen aufbauen" : mastery < 60 ? "Lücken schließen" : "Festigen") : (mastery < 20 ? "Build fundamentals" : mastery < 60 ? "Close gaps" : "Consolidate")}</small></div>
          <div class="progress-track"><div class="progress-fill" style="width:${mastery}%"></div></div>
          <button class="ghost-button" data-practice-topic="${escapeHtml(topic.id)}">${state.language === "de" ? "Start" : "Start"}</button>
        </div>
      `;
      },
    )
    .join("");

  content.innerHTML = `
    <div class="hero-grid">
      <section class="hero-card">
        <p class="eyebrow">${state.language === "de" ? "Dein lokaler Lernstand" : "Your local study state"}</p>
        <h2>${state.language === "de" ? "Alles-oder-nichts trainieren.<br>Bis jede Aussage sitzt." : "Train all-or-nothing scoring.<br>Until every statement is solid."}</h2>
        <p>${state.language === "de" ? "Die Fragen bilden das Prüfungsformat nach: Eine Aufgabe zählt nur dann als richtig, wenn exakt alle korrekten Optionen und keine falsche Option markiert wurden." : "The questions follow the exam format: a task counts only if you select exactly all correct options and no incorrect option."}</p>
        <div class="hero-actions">
          <button class="primary-button" data-action="quick-practice">${state.language === "de" ? "Fällige Fragen starten" : "Start due questions"}</button>
          <button class="secondary-button" data-view-link="learn">${state.language === "de" ? "Zusammenfassungen öffnen" : "Open summaries"}</button>
        </div>
      </section>
      <aside class="hero-card focus-card">
        <span class="eyebrow">${state.language === "de" ? "Gesamtfortschritt" : "Overall progress"}</span>
        <span class="large-number">${current.mastery}%</span>
        <p>${state.language === "de" ? `${current.mastered} von ${activeQuestions().length} aktiven Fragen gelten aktuell als sicher beherrscht.` : `${current.mastered} of ${activeQuestions().length} active questions are currently considered mastered.`}</p>
        <div class="progress-track"><div class="progress-fill" style="width:${current.mastery}%"></div></div>
      </aside>
    </div>

    <div class="stats-grid">
      <article class="stat-card"><span>${state.language === "de" ? "Beantwortet" : "Answered"}</span><strong>${current.attempts}</strong></article>
      <article class="stat-card"><span>${state.language === "de" ? "Exakte Trefferquote" : "Exact accuracy"}</span><strong>${current.accuracy}%</strong></article>
      <article class="stat-card"><span>${state.language === "de" ? "Jetzt fällig" : "Due now"}</span><strong>${current.due}</strong></article>
      <article class="stat-card"><span>${state.language === "de" ? "Sicher beherrscht" : "Mastered"}</span><strong>${current.mastered}</strong></article>
    </div>

    <div class="section-heading">
      <div><p class="eyebrow">${state.language === "de" ? "5 Themenblöcke" : "5 topic blocks"}</p><h3>${state.language === "de" ? "Prüfungsstoff" : "Exam scope"}</h3></div>
      <button class="ghost-button" data-view-link="learn">${state.language === "de" ? "Alle Zusammenfassungen" : "All summaries"}</button>
    </div>
    <div class="topic-grid">${topicRows}</div>

    <div class="section-heading">
      <div><p class="eyebrow">${state.language === "de" ? "Nach Lernstand sortiert" : "Sorted by mastery"}</p><h3>${state.language === "de" ? "Empfohlene Reihenfolge" : "Recommended order"}</h3></div>
    </div>
    <div class="priority-list">${priorities}</div>
  `;

  bindCommonLinks();
  content.querySelectorAll("[data-open-topic]").forEach((card) => {
    card.addEventListener("click", () => {
      state.learnTopic = card.dataset.openTopic;
      navigate("learn");
    });
  });
  content.querySelectorAll("[data-practice-topic]").forEach((button) => {
    button.addEventListener("click", () => {
      state.practice.filters.topics = [button.dataset.practiceTopic];
      startPractice();
    });
  });
  content.querySelector('[data-action="quick-practice"]').addEventListener("click", () => {
    state.practice.filters = {
      topics: [],
      difficulties: [],
      status: current.due ? "due" : "all",
      shuffle: true,
      limit: "20",
    };
    startPractice();
  });
}

function bindCommonLinks() {
  content.querySelectorAll("[data-view-link]").forEach((button) => {
    button.addEventListener("click", () => navigate(button.dataset.viewLink));
  });
}

function renderLearn() {
  const baseTopic = topicById(state.learnTopic) || state.data.topics[0];
  const topic = topicContent(baseTopic);
  const sectionIndex = Math.max(
    0,
    Math.min(Number(state.learnSection) || 0, topic.sections.length - 1),
  );
  state.learnSection = sectionIndex;
  const section = topic.sections[sectionIndex];
  const sectionMetadata = baseTopic.sections[sectionIndex] || {};
  const glossaryTerms = (sectionMetadata.studyTerms || [])
    .map((term) => state.data.glossary.find((entry) => entry.term === term))
    .filter(Boolean);
  const chapterQuestionIds = sectionMetadata.questionIds || [];
  const chapterQuestions = chapterQuestionIds
    .map((id) => questionById(id))
    .filter((question) => question && supportsLanguage(question));
  const tabs = state.data.topics
    .map(
      (entry) => {
        const view = topicContent(entry);
        return `
        <button class="topic-tab ${entry.id === baseTopic.id ? "active" : ""}" data-topic="${escapeHtml(entry.id)}" style="--topic-color:${escapeHtml(entry.color)}">
          ${escapeHtml(view.title)}
        </button>
      `;
      },
    )
    .join("");

  content.innerHTML = `
    <div class="learn-layout">
      <aside class="learn-sidebar">
        <div class="topic-tabs">
          <p class="sidebar-section-label">${state.language === "de" ? "Themenblöcke" : "Topics"}</p>
          ${tabs}
        </div>
        <nav class="chapter-nav" aria-label="${state.language === "de" ? "Kapitelübersicht" : "Chapter overview"}">
          <p class="sidebar-section-label">${state.language === "de" ? "Unterkapitel" : "Chapters"}</p>
          ${topic.sections.map((section, index) => `
            <button class="${index === sectionIndex ? "active" : ""}" data-learn-section="${index}">
              <span>${String(index + 1).padStart(2, "0")}</span>
              ${escapeHtml(section.title)}
            </button>
          `).join("")}
        </nav>
      </aside>
      <article class="summary-card" style="--topic-color:${escapeHtml(baseTopic.color)}">
        <header class="summary-hero">
          <span class="topic-kicker">${escapeHtml(topic.deck)} · ${escapeHtml(topic.pages)}</span>
          <h2>${escapeHtml(topic.title)}</h2>
          <p>${escapeHtml(topic.overview)}</p>
          <div class="study-stats">
            <span><strong>${topic.sections.length}</strong> ${state.language === "de" ? "Kapitel" : "chapters"}</span>
            <span><strong>${state.data.glossary.filter((entry) => entry.topic === topic.id).length}</strong> ${state.language === "de" ? "erklärte Begriffe" : "explained concepts"}</span>
            <span><strong>${topicQuestions(topic.id).length}</strong> ${state.language === "de" ? "Übungsfragen" : "practice questions"}</span>
          </div>
          <div class="focus-chips">${topic.examFocus.map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("")}</div>
        </header>
        <div class="summary-body">
          <div class="chapter-progress">
            <span>${state.language === "de" ? "Unterkapitel" : "Chapter"} ${sectionIndex + 1} / ${topic.sections.length}</span>
            <div class="progress-track"><div class="progress-fill" style="width:${((sectionIndex + 1) / topic.sections.length) * 100}%"></div></div>
          </div>

          <section class="study-section single-chapter">
            <header class="study-section-header">
              <span class="study-section-number">${String(sectionIndex + 1).padStart(2, "0")}</span>
              <div>
                <p class="eyebrow">${escapeHtml(topic.title)}</p>
                <h3>${escapeHtml(section.title)}</h3>
              </div>
            </header>
            <div class="study-section-content">
              ${section.body ? `<p>${escapeHtml(section.body)}</p>` : ""}
              ${section.bullets?.length ? `<ul>${section.bullets.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : ""}
              ${section.formula ? `<div class="formula-box">${escapeHtml(section.formula)}</div>` : ""}
              ${section.example ? `<div class="example-box"><strong>${state.language === "de" ? "Konkretes Beispiel:" : "Concrete example:"}</strong> ${escapeHtml(section.example)}</div>` : ""}
              ${section.pitfall ? `<div class="pitfall-box"><strong>${state.language === "de" ? "Typische Prüfungsfalle:" : "Typical exam trap:"}</strong> ${escapeHtml(section.pitfall)}</div>` : ""}
            </div>
          </section>

          <section class="chapter-deep-dive">
            <div class="section-heading">
              <div>
                <p class="eyebrow">${glossaryTerms.length} ${state.language === "de" ? "Begriffe" : "concepts"}</p>
                <h3>${state.language === "de" ? "Begriffe dieses Unterkapitels" : "Concepts in this chapter"}</h3>
              </div>
            </div>
            <div class="concept-study-grid">
              ${glossaryTerms.map((entry) => `
                <article class="concept-study-card">
                  <h4>${escapeHtml(glossaryTerm(entry))}</h4>
                  <p>${escapeHtml(localized(entry.detail?.simpleExplanation || glossaryDefinition(entry)))}</p>
                  <div class="concept-takeaway">
                    <span>${state.language === "de" ? "Merksatz" : "Takeaway"}</span>
                    ${escapeHtml(localized(entry.detail?.examTakeaway || glossaryDefinition(entry)))}
                  </div>
                  <button class="ghost-button compact" data-learn-term="${escapeHtml(entry.term)}">${state.language === "de" ? "Vollständige Erklärung öffnen" : "Open complete explanation"}</button>
                </article>
              `).join("") || `<div class="empty-state">${state.language === "de" ? "Diesem Unterkapitel sind noch keine Glossarbegriffe zugeordnet." : "No glossary concepts are assigned to this chapter yet."}</div>`}
            </div>
          </section>

          ${chapterQuestions.length ? `
            <section class="chapter-question-section">
              <div class="section-heading">
                <div>
                  <p class="eyebrow">${chapterQuestions.length} ${state.language === "de" ? "passende Fragen" : "matching questions"}</p>
                  <h3>${state.language === "de" ? "Dieses Unterkapitel prüfen" : "Test this chapter"}</h3>
                </div>
                <button class="primary-button" id="practice-chapter">${state.language === "de" ? "Kapitel-Fragen starten" : "Start chapter questions"}</button>
              </div>
              <div class="chapter-question-list">
                ${chapterQuestions.slice(0, 6).map((question) => `
                  <button data-chapter-question="${escapeHtml(question.id)}">
                    <span>${question.difficulty}</span>
                    ${escapeHtml(localized(question.prompt))}
                  </button>
                `).join("")}
              </div>
            </section>
          ` : ""}

          ${sectionIndex === topic.sections.length - 1 ? `
            <section class="summary-section">
              <h3>${state.language === "de" ? "Selbstcheck zum Themenblock" : "Topic self-check"}</h3>
              <div><ul class="check-list">${topic.checklist.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div>
            </section>
          ` : ""}

          <div class="chapter-pagination">
            <button class="secondary-button" data-chapter-direction="-1" ${sectionIndex === 0 ? "disabled" : ""}>${state.language === "de" ? "← Vorheriges Unterkapitel" : "← Previous chapter"}</button>
            <button class="primary-button" data-chapter-direction="1" ${sectionIndex === topic.sections.length - 1 ? "disabled" : ""}>${state.language === "de" ? "Nächstes Unterkapitel →" : "Next chapter →"}</button>
          </div>
        </div>
      </article>
    </div>
  `;

  content.querySelectorAll("[data-topic]").forEach((button) => {
    button.addEventListener("click", () => {
      state.learnTopic = button.dataset.topic;
      state.learnSection = 0;
      renderLearn();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });
  content.querySelectorAll("[data-learn-section]").forEach((button) => {
    button.addEventListener("click", () => {
      state.learnSection = Number(button.dataset.learnSection);
      renderLearn();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });
  content.querySelectorAll("[data-learn-term]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedGlossaryTerm = button.dataset.learnTerm;
      navigate("glossary");
    });
  });
  content.querySelectorAll("[data-chapter-direction]").forEach((button) => {
    button.addEventListener("click", () => {
      state.learnSection += Number(button.dataset.chapterDirection);
      renderLearn();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });
  content.querySelectorAll("[data-chapter-question]").forEach((button) => {
    button.addEventListener("click", () => {
      startQuestionSet([button.dataset.chapterQuestion]);
    });
  });
  content.querySelector("#practice-chapter")?.addEventListener("click", () => {
    startQuestionSet(chapterQuestions.map((question) => question.id));
  });
}

function renderCypherExamples() {
  const material = state.data.cypherExamples || {};
  const examples = material.examples || [];
  const categories = [...new Set(examples.map((example) => example.category))];
  const visible = examples.filter(
    (example) =>
      (state.cypherLevel === "all" ||
        example.difficulty === Number(state.cypherLevel)) &&
      (state.cypherCategory === "all" ||
        example.category === state.cypherCategory),
  );

  content.innerHTML = `
    <section class="coding-hero">
      <div>
        <p class="eyebrow">${examples.length} ${state.language === "de" ? "ausführbare Cypher-Beispiele" : "executable Cypher examples"}</p>
        <h2>${state.language === "de" ? "Cypher lesen, vergleichen und in Neo4j ausführen" : "Read, compare, and run Cypher in Neo4j"}</h2>
        <p>${state.language === "de" ? "Keine Programmieraufgaben: Die Sammlung zeigt konkrete Graph-Queries von elementaren Patterns bis zu komplexen Pfaden und Subqueries. Jedes Beispiel erklärt, welche Zeilen entstehen und warum." : "No programming exercises: this collection presents concrete graph queries from elementary patterns to complex paths and subqueries. Every example explains which rows are produced and why."}</p>
      </div>
      <div class="database-status">
        <span class="sync-dot"></span>
        <div>
          <strong>Neo4j / Cypher</strong>
          <span>${state.language === "de" ? "APOC-frei · für Neo4j 5+" : "APOC-free · for Neo4j 5+"}</span>
        </div>
      </div>
    </section>

    <section class="panel cypher-core-difference">
      <p class="eyebrow">${state.language === "de" ? "Zentrale Unterscheidung" : "Core distinction"}</p>
      <h3>MATCH vs. WHERE</h3>
      <div class="comparison-grid">
        <div>
          <strong>MATCH</strong>
          <p>${escapeHtml(localized(material.matchVsWhere?.match))}</p>
          <pre><code>${escapeHtml(material.matchVsWhere?.matchExample || "")}</code></pre>
        </div>
        <div>
          <strong>WHERE</strong>
          <p>${escapeHtml(localized(material.matchVsWhere?.where))}</p>
          <pre><code>${escapeHtml(material.matchVsWhere?.whereExample || "")}</code></pre>
        </div>
      </div>
      <div class="example-box">${escapeHtml(localized(material.matchVsWhere?.takeaway))}</div>
    </section>

    <details class="solution-details cypher-setup">
      <summary>${state.language === "de" ? "Gemeinsamen Beispielgraphen für Neo4j anzeigen" : "Show shared Neo4j example graph"}</summary>
      <div class="solution-content">
        <p>${escapeHtml(localized(material.setup?.description))}</p>
        <div class="code-block">
          <div class="code-label">Cypher setup</div>
          <pre><code>${escapeHtml(material.setup?.query || "")}</code></pre>
        </div>
      </div>
    </details>

    <div class="coding-filters" role="group" aria-label="${state.language === "de" ? "Themenfilter" : "Topic filter"}">
      <span class="filter-label">${state.language === "de" ? "Schwierigkeit:" : "Difficulty:"}</span>
      <button class="chip ${state.cypherLevel === "all" ? "active" : ""}" data-cypher-level="all">${state.language === "de" ? "Alle" : "All"}</button>
      ${[1, 2, 3, 4, 5].map((level) => `<button class="chip ${state.cypherLevel === String(level) ? "active" : ""}" data-cypher-level="${level}">${level} · ${escapeHtml(difficultyLabel(level))}</button>`).join("")}
    </div>
    <div class="coding-filters" role="group" aria-label="${state.language === "de" ? "Kategorienfilter" : "Category filter"}">
      <span class="filter-label">${state.language === "de" ? "Kategorie:" : "Category:"}</span>
      <button class="chip ${state.cypherCategory === "all" ? "active" : ""}" data-cypher-category="all">${state.language === "de" ? "Alle" : "All"} · ${examples.length}</button>
      ${categories.map((category) => {
        const count = examples.filter((example) => example.category === category).length;
        return `<button class="chip ${state.cypherCategory === category ? "active" : ""}" data-cypher-category="${escapeHtml(category)}">${escapeHtml(category)} · ${count}</button>`;
      }).join("")}
    </div>

    <div class="coding-list">
      ${visible.map((example, index) => {
        return `
          <article class="coding-card" style="--topic-color:#ff8a5b">
            <header class="coding-card-header">
              <div class="question-meta">
                <span class="badge">${escapeHtml(example.category)}</span>
                <span class="badge difficulty-${example.difficulty}">${example.difficulty} · ${escapeHtml(difficultyLabel(example.difficulty))}</span>
              </div>
              <span class="eyebrow">${escapeHtml(example.id)} · ${String(index + 1).padStart(2, "0")}</span>
            </header>
            <div class="coding-card-body">
              <h3>${escapeHtml(localized(example.title))}</h3>
              <p>${escapeHtml(localized(example.question))}</p>
              <div class="code-block solution-code">
                <div class="code-label">Cypher</div>
                <pre><code>${escapeHtml(example.query)}</code></pre>
              </div>
              ${example.alternative ? `
                <div class="code-block">
                  <div class="code-label">${state.language === "de" ? "Alternative / Vergleich" : "Alternative / comparison"}</div>
                  <pre><code>${escapeHtml(example.alternative)}</code></pre>
                </div>
              ` : ""}
              <div class="cypher-explanation">
                <strong>${state.language === "de" ? "So liest du die Query" : "How to read the query"}</strong>
                <p>${escapeHtml(localized(example.explanation))}</p>
              </div>
              <div class="example-box"><strong>${state.language === "de" ? "Ergebnisidee:" : "Result idea:"}</strong> ${escapeHtml(localized(example.expectedResult))}</div>
              ${example.pitfall ? `<div class="pitfall-box"><strong>${state.language === "de" ? "Klausurfalle:" : "Exam trap:"}</strong> ${escapeHtml(localized(example.pitfall))}</div>` : ""}
            </div>
          </article>
        `;
      }).join("") || `<div class="empty-state">${state.language === "de" ? "Für diesen Filter gibt es keine Cypher-Beispiele." : "No Cypher examples match this filter."}</div>`}
    </div>
  `;

  content.querySelectorAll("[data-cypher-level]").forEach((button) => {
    button.addEventListener("click", () => {
      state.cypherLevel = button.dataset.cypherLevel;
      renderCypherExamples();
    });
  });
  content.querySelectorAll("[data-cypher-category]").forEach((button) => {
    button.addEventListener("click", () => {
      state.cypherCategory = button.dataset.cypherCategory;
      renderCypherExamples();
    });
  });
}

function filterPanelHtml() {
  const filters = state.practice.filters;
  return `
    <aside class="panel filter-panel">
      <h3>${state.language === "de" ? "Session konfigurieren" : "Configure session"}</h3>
      <div class="filter-group">
        <label>${state.language === "de" ? "Themen" : "Topics"}</label>
        <div class="filter-chips">
          ${state.data.topics
            .map((topic) => {
              const view = topicContent(topic);
              return `
                <button class="chip ${filters.topics.includes(topic.id) ? "active" : ""}" data-filter-topic="${escapeHtml(topic.id)}">${escapeHtml(view.shortTitle || view.title)}</button>
              `;
            })
            .join("")}
        </div>
      </div>
      <div class="filter-group">
        <label>${state.language === "de" ? "Schwierigkeit" : "Difficulty"}</label>
        <div class="filter-chips">
          ${Object.entries(DIFFICULTY_LABELS)
            .map(
              ([level, label]) => `
                <button class="chip ${filters.difficulties.includes(Number(level)) ? "active" : ""}" data-filter-difficulty="${level}">${level} · ${escapeHtml(difficultyLabel(level))}</button>
              `,
            )
            .join("")}
        </div>
      </div>
      <div class="filter-group">
        <label for="status-filter">${state.language === "de" ? "Fragenstatus" : "Question status"}</label>
        <select id="status-filter">
          <option value="all" ${filters.status === "all" ? "selected" : ""}>${state.language === "de" ? "Alle Fragen" : "All questions"}</option>
          <option value="due" ${filters.status === "due" ? "selected" : ""}>${state.language === "de" ? "Fällig / falsch" : "Due / wrong"}</option>
          <option value="new" ${filters.status === "new" ? "selected" : ""}>${state.language === "de" ? "Noch nie beantwortet" : "Never answered"}</option>
          <option value="wrong" ${filters.status === "wrong" ? "selected" : ""}>${state.language === "de" ? "Zuletzt falsch" : "Last wrong"}</option>
          <option value="correct" ${filters.status === "correct" ? "selected" : ""}>${state.language === "de" ? "Zuletzt richtig" : "Last correct"}</option>
          <option value="mastered" ${filters.status === "mastered" ? "selected" : ""}>${state.language === "de" ? "Sicher beherrscht" : "Mastered"}</option>
        </select>
      </div>
      <div class="filter-group">
        <label for="limit-filter">${state.language === "de" ? "Sessionlänge" : "Session length"}</label>
        <select id="limit-filter">
          <option value="10" ${filters.limit === "10" ? "selected" : ""}>10 ${state.language === "de" ? "Fragen" : "questions"}</option>
          <option value="20" ${filters.limit === "20" ? "selected" : ""}>20 ${state.language === "de" ? "Fragen" : "questions"}</option>
          <option value="40" ${filters.limit === "40" ? "selected" : ""}>40 ${state.language === "de" ? "Fragen" : "questions"}</option>
          <option value="all" ${filters.limit === "all" ? "selected" : ""}>${state.language === "de" ? "Alle passenden" : "All matching"}</option>
        </select>
      </div>
      <div class="filter-group">
        <label><input id="shuffle-filter" type="checkbox" ${filters.shuffle ? "checked" : ""}> ${state.language === "de" ? "Fragen mischen" : "Shuffle questions"}</label>
      </div>
      <button class="primary-button" id="start-practice">${state.language === "de" ? "Neue Session starten" : "Start new session"}</button>
    </aside>
  `;
}

function bindPracticeFilters() {
  content.querySelectorAll("[data-filter-topic]").forEach((button) => {
    button.addEventListener("click", () => {
      const id = button.dataset.filterTopic;
      const topics = state.practice.filters.topics;
      state.practice.filters.topics = topics.includes(id)
        ? topics.filter((entry) => entry !== id)
        : [...topics, id];
      button.classList.toggle("active");
    });
  });
  content.querySelectorAll("[data-filter-difficulty]").forEach((button) => {
    button.addEventListener("click", () => {
      const value = Number(button.dataset.filterDifficulty);
      const levels = state.practice.filters.difficulties;
      state.practice.filters.difficulties = levels.includes(value)
        ? levels.filter((entry) => entry !== value)
        : [...levels, value];
      button.classList.toggle("active");
    });
  });
  content.querySelector("#status-filter").addEventListener("change", (event) => {
    state.practice.filters.status = event.target.value;
  });
  content.querySelector("#limit-filter").addEventListener("change", (event) => {
    state.practice.filters.limit = event.target.value;
  });
  content.querySelector("#shuffle-filter").addEventListener("change", (event) => {
    state.practice.filters.shuffle = event.target.checked;
  });
  content.querySelector("#start-practice").addEventListener("click", startPractice);
}

function startPractice() {
  let selected = selectQuestions(
    activeQuestions(),
    state.progress,
    state.practice.filters,
  );
  if (state.practice.filters.shuffle) selected = shuffle(selected);
  if (state.practice.filters.limit !== "all") {
    selected = selected.slice(0, Number(state.practice.filters.limit));
  }
  state.practice.queue = selected.map((question) => question.id);
  state.practice.index = 0;
  state.practice.feedback = null;
  state.practice.selected = [];
  state.practice.optionOrder = {};
  state.practice.sessionCorrect = 0;
  state.practice.sessionAnswered = 0;
  navigate("practice");
  if (!selected.length) showToast(state.language === "de" ? "Für diese Filter gibt es keine passenden Fragen." : "No questions match these filters.");
}

function startQuestionSet(questionIds) {
  const selected = [...new Set(questionIds)]
    .map((id) => questionById(id))
    .filter(
      (question) =>
        question &&
        questionLifecycle(question) === "active" &&
        supportsLanguage(question),
    );
  state.practice.queue = selected.map((question) => question.id);
  state.practice.index = 0;
  state.practice.feedback = null;
  state.practice.selected = [];
  state.practice.optionOrder = {};
  state.practice.sessionCorrect = 0;
  state.practice.sessionAnswered = 0;
  navigate("practice");
  if (!selected.length) {
    showToast(
      state.language === "de"
        ? "Für dieses Unterkapitel sind noch keine passenden Fragen hinterlegt."
        : "No matching questions are available for this chapter yet.",
    );
  }
}

function orderedOptions(question, mode = "practice") {
  const key = `${mode}:${question.id}`;
  const store =
    mode === "practice" ? state.practice.optionOrder : state.exam.optionOrder;
  if (!store[key]) store[key] = shuffle(question.options.map((option) => option.id));
  return store[key].map((id) => question.options.find((option) => option.id === id));
}

function renderPractice() {
  const session = state.practice;
  const questionId = session.queue[session.index];
  const question = questionById(questionId);
  let questionArea = `
    <div class="empty-state">
      <h3>${state.language === "de" ? "Noch keine Session aktiv" : "No active session"}</h3>
      <p>${state.language === "de" ? "Wähle Themen, Schwierigkeitsgrad und Fragenstatus. Falsche Antworten werden innerhalb der Session später erneut eingeplant." : "Choose topics, difficulty and question status. Wrong answers are scheduled again later in the same session."}</p>
    </div>
  `;

  if (question) {
    questionArea = renderQuestionCard(question, "practice");
  } else if (session.queue.length && session.index >= session.queue.length) {
    const rate = session.sessionAnswered
      ? Math.round((session.sessionCorrect / session.sessionAnswered) * 100)
      : 0;
    questionArea = `
      <div class="result-card">
        <p class="eyebrow">${state.language === "de" ? "Session abgeschlossen" : "Session complete"}</p>
        <h2>${session.sessionCorrect} / ${session.sessionAnswered} ${state.language === "de" ? "exakt richtig" : "exactly correct"}</h2>
        <div class="result-score">${rate}%</div>
        <p>${state.language === "de" ? "Nur vollständig richtige Auswahlmengen zählen als Treffer." : "Only fully exact selections count as correct."}</p>
        <div class="hero-actions" style="justify-content:center">
          <button class="primary-button" id="repeat-session">${state.language === "de" ? "Neue Session" : "New session"}</button>
          <button class="secondary-button" data-view-link="dashboard">${state.language === "de" ? "Zum Überblick" : "Back to dashboard"}</button>
        </div>
      </div>
    `;
  }

  content.innerHTML = `
    <div class="practice-layout">
      ${filterPanelHtml()}
      <div class="question-area">${questionArea}</div>
    </div>
  `;
  bindPracticeFilters();
  bindCommonLinks();
  if (question) bindQuestionCard(question, "practice");
  content.querySelector("#repeat-session")?.addEventListener("click", startPractice);
}

function renderQuestionCard(question, mode) {
  const isPractice = mode === "practice";
  const session = isPractice ? state.practice : state.exam;
  const feedback = isPractice ? session.feedback : null;
  const selected = new Set(
    isPractice
      ? session.selected
      : session.answers[question.id] || [],
  );
  const topic = topicContent(topicById(question.topic));
  const options = orderedOptions(question, mode);
  const progress = state.progress[question.id];
  const optionHtml = options
    .map((option, index) => {
      const checked = selected.has(option.id);
      const classes = [];
      if (feedback && option.correct) classes.push("correct-option");
      if (feedback && checked && !option.correct) classes.push("wrong-selected");
      return `
        <label class="option ${classes.join(" ")}">
          <input type="checkbox" value="${escapeHtml(option.id)}" ${checked ? "checked" : ""} ${feedback ? "disabled" : ""}>
          <div class="option-main">
            <span class="option-letter">${String.fromCharCode(65 + index)}</span>
            <span class="option-text">${escapeHtml(localized(option.text))}</span>
          </div>
          ${feedback ? `<div class="option-explanation">${option.correct ? (state.language === "de" ? "✓ Richtig. " : "✓ Correct. ") : (state.language === "de" ? "✗ Falsch. " : "✗ Incorrect. ")}${escapeHtml(localized(option.explanation || ""))}</div>` : ""}
        </label>
      `;
    })
    .join("");

  const header = isPractice
    ? `
      <div class="session-header">
        <span>${state.language === "de" ? "Frage" : "Question"} ${Math.min(session.index + 1, session.queue.length)} ${state.language === "de" ? "von" : "of"} ${session.queue.length}</span>
        <span>${session.sessionCorrect} ${state.language === "de" ? "exakt richtig" : "exactly correct"} · ${session.sessionAnswered} ${state.language === "de" ? "beantwortet" : "answered"}</span>
      </div>
    `
    : "";

  const feedbackHtml = feedback
    ? `
      <div class="feedback-banner ${feedback.correct ? "correct" : "wrong"}">
        <strong>${feedback.correct ? (state.language === "de" ? "Exakt richtig — voller Punkt." : "Exactly correct — full point.") : (state.language === "de" ? "Nicht exakt — 0 Punkte." : "Not exact — 0 points.")}</strong>
        <p>${escapeHtml(localized(question.explanation))} ${progress?.dueAt ? `${state.language === "de" ? "Nächste reguläre Wiederholung" : "Next regular review"}: ${dueLabel(progress.dueAt)}.` : ""}</p>
      </div>
    `
    : "";

  return `
    ${header}
    <article class="question-card">
      <div class="question-topline">
        <div class="question-meta">
          <span class="badge" style="border-color:${escapeHtml(topic?.color || "#555")}">${escapeHtml(topic?.shortTitle || topic?.title || question.topic)}</span>
          <span class="badge difficulty-${question.difficulty}">${question.difficulty} · ${escapeHtml(difficultyLabel(question.difficulty))}</span>
          ${question.tags?.slice(0, 2).map((tag) => `<span class="badge">${escapeHtml(tag)}</span>`).join("") || ""}
        </div>
        <span class="eyebrow">${escapeHtml(question.source?.pages || "")}</span>
      </div>
      <div class="question-content">
        <h2>${escapeHtml(localized(question.prompt))}</h2>
        ${question.context ? `<div class="question-context">${escapeHtml(localized(question.context))}</div>` : ""}
        <p class="answer-note">${state.language === "de" ? "Markiere exakt alle richtigen Aussagen. Es können 0 bis alle Optionen richtig sein." : "Select exactly all correct statements. From 0 to all options may be correct."}</p>
        <div class="options-list">${optionHtml}</div>
        ${feedbackHtml}
      </div>
      <div class="question-actions">
        <div>
          ${isPractice && feedback ? `<button class="ghost-button" data-action="repeat-question">${state.language === "de" ? "Nochmals einplanen" : "Schedule again"}</button>` : ""}
        </div>
        <div>
          ${
            isPractice
              ? feedback
                ? `<button class="primary-button" data-action="next-question">${state.language === "de" ? "Nächste Frage" : "Next question"}</button>`
                : `<button class="primary-button" data-action="submit-question">${state.language === "de" ? "Antwort prüfen" : "Check answer"}</button>`
              : `<button class="secondary-button" data-action="exam-prev">${state.language === "de" ? "Zurück" : "Back"}</button>
                 <button class="primary-button" data-action="exam-next">${state.language === "de" ? "Weiter" : "Next"}</button>`
          }
        </div>
      </div>
    </article>
  `;
}

function bindQuestionCard(question, mode) {
  const checkboxes = content.querySelectorAll('.option input[type="checkbox"]');
  checkboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      const selected = [...checkboxes]
        .filter((input) => input.checked)
        .map((input) => input.value);
      if (mode === "practice") {
        state.practice.selected = selected;
      } else {
        state.exam.answers[question.id] = selected;
        state.exam.visited.add(question.id);
        updateExamNav();
      }
    });
  });

  if (mode === "practice") {
    content.querySelector('[data-action="submit-question"]')?.addEventListener("click", () => {
      const correct = exactMatch(state.practice.selected, question.options);
      state.progress[question.id] = updateProgress(
        state.progress[question.id],
        correct,
      );
      state.progress[question.id].lastSelection = [...state.practice.selected];
      state.practice.feedback = { correct };
      state.practice.sessionAnswered += 1;
      if (correct) state.practice.sessionCorrect += 1;
      if (
        !correct &&
        !state.practice.queue
          .slice(state.practice.index + 1)
          .includes(question.id)
      ) {
        const delay = 3 + Math.floor(Math.random() * 4);
        const insertAt = Math.min(
          state.practice.queue.length,
          state.practice.index + delay,
        );
        state.practice.queue.splice(insertAt, 0, question.id);
      }
      saveState();
      renderPractice();
    });
    content.querySelector('[data-action="next-question"]')?.addEventListener("click", () => {
      state.practice.index += 1;
      state.practice.feedback = null;
      state.practice.selected = [];
      renderPractice();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
    content.querySelector('[data-action="repeat-question"]')?.addEventListener("click", () => {
      if (
        !state.practice.queue
          .slice(state.practice.index + 1)
          .includes(question.id)
      ) {
        state.practice.queue.splice(state.practice.index + 2, 0, question.id);
      }
      showToast(state.language === "de" ? "Frage wurde erneut eingeplant." : "Question was scheduled again.");
    });
  } else {
    content.querySelector('[data-action="exam-prev"]').addEventListener("click", () => {
      state.exam.index = Math.max(0, state.exam.index - 1);
      renderExam();
    });
    content.querySelector('[data-action="exam-next"]').addEventListener("click", () => {
      state.exam.visited.add(question.id);
      state.exam.index = Math.min(
        state.exam.questions.length - 1,
        state.exam.index + 1,
      );
      renderExam();
    });
  }
}

function renderExam() {
  if (!state.exam) {
    content.innerHTML = `
      <div class="exam-setup">
        <section class="setup-card">
          <p class="eyebrow">${state.language === "de" ? "Realistischer Prüfungsmodus" : "Realistic exam mode"}</p>
          <h2>${state.language === "de" ? "Eine falsche oder fehlende Markierung bedeutet 0 Punkte." : "One wrong or missing mark means 0 points."}</h2>
          <p>${state.language === "de" ? "Während der Simulation werden keine Lösungen angezeigt. Die Auswertung erfolgt gesammelt am Ende." : "No solutions are shown during the simulation. Evaluation happens at the end."}</p>
          <div class="setup-grid">
            <div class="setup-field">
              <label for="exam-count">${state.language === "de" ? "Anzahl der Aufgaben" : "Number of tasks"}</label>
              <select id="exam-count">
                <option value="10">10 ${state.language === "de" ? "Aufgaben" : "tasks"}</option>
                <option value="20" selected>20 ${state.language === "de" ? "Aufgaben" : "tasks"}</option>
                <option value="30">30 ${state.language === "de" ? "Aufgaben" : "tasks"}</option>
                <option value="40">40 ${state.language === "de" ? "Aufgaben" : "tasks"}</option>
              </select>
            </div>
            <div class="setup-field">
              <label for="exam-duration">${state.language === "de" ? "Zeitlimit" : "Time limit"}</label>
              <select id="exam-duration">
                <option value="20">20 ${state.language === "de" ? "Minuten" : "minutes"}</option>
                <option value="40" selected>40 ${state.language === "de" ? "Minuten" : "minutes"}</option>
                <option value="60">60 ${state.language === "de" ? "Minuten" : "minutes"}</option>
                <option value="90">90 ${state.language === "de" ? "Minuten" : "minutes"}</option>
              </select>
            </div>
          </div>
          <button class="primary-button" id="start-exam">${state.language === "de" ? "Prüfung starten" : "Start exam"}</button>
        </section>
        <aside class="setup-card">
          <h3>${state.language === "de" ? "Regeln" : "Rules"}</h3>
          <ul class="exam-rules">
            <li>${state.language === "de" ? "Pro Aufgabe sind 0 bis alle Aussagen richtig." : "Per task, 0 to all statements may be correct."}</li>
            <li>${state.language === "de" ? "Nur die exakt richtige Auswahlmenge gibt einen Punkt." : "Only the exact selection gets a point."}</li>
            <li>${state.language === "de" ? "Fragen und Antwortoptionen werden gemischt." : "Questions and options are shuffled."}</li>
            <li>${state.language === "de" ? "Alle fünf aktuellen Themen werden möglichst gleichmäßig abgedeckt." : "All five current topics are covered as evenly as possible."}</li>
            <li>${state.language === "de" ? "Nach Abgabe erhältst du eine vollständige Auswertung." : "After submission you get a full review."}</li>
          </ul>
        </aside>
      </div>
    `;
    content.querySelector("#start-exam").addEventListener("click", startExam);
    return;
  }

  if (state.exam.finished) {
    renderExamResult();
    return;
  }

  const question = state.exam.questions[state.exam.index];
  const remaining = Math.max(0, state.exam.endsAt - Date.now());
  content.innerHTML = `
    <div class="exam-header">
      <div><strong>${state.language === "de" ? "Aufgabe" : "Task"} ${state.exam.index + 1} / ${state.exam.questions.length}</strong><br><span class="eyebrow">${state.language === "de" ? "Alles-oder-nichts-Wertung" : "All-or-nothing scoring"}</span></div>
      <div class="timer" id="exam-timer">${formatTimer(remaining)}</div>
      <button class="danger-button" id="finish-exam">${state.language === "de" ? "Prüfung abgeben" : "Submit exam"}</button>
    </div>
    <div class="exam-layout">
      <div>${renderQuestionCard(question, "exam")}</div>
      <nav class="exam-nav" aria-label="Prüfungsfragen">
        ${state.exam.questions
          .map(
            (entry, index) => `
              <button data-exam-index="${index}" class="${index === state.exam.index ? "active" : ""} ${(state.exam.answers[entry.id]?.length || state.exam.visited.has(entry.id)) ? "answered" : ""}">${index + 1}</button>
            `,
          )
          .join("")}
      </nav>
    </div>
  `;
  bindQuestionCard(question, "exam");
  content.querySelectorAll("[data-exam-index]").forEach((button) => {
    button.addEventListener("click", () => {
      state.exam.visited.add(question.id);
      state.exam.index = Number(button.dataset.examIndex);
      renderExam();
    });
  });
  content.querySelector("#finish-exam").addEventListener("click", () => {
    if (window.confirm(state.language === "de" ? "Prüfung jetzt verbindlich abgeben?" : "Submit the exam now?")) finishExam();
  });
  startExamTimer();
}

function startExam() {
  const count = Number(content.querySelector("#exam-count").value);
  const duration = Number(content.querySelector("#exam-duration").value);
  const questions = buildExam(activeQuestions(), count);
  state.exam = {
    questions,
    index: 0,
    answers: {},
    visited: new Set(),
    optionOrder: {},
    startedAt: Date.now(),
    endsAt: Date.now() + duration * 60 * 1000,
    finished: false,
    result: null,
    reviewMode: "summary",
    reviewIndex: 0,
  };
  renderExam();
}

function startExamTimer() {
  clearInterval(examTimer);
  examTimer = setInterval(() => {
    if (!state.exam || state.exam.finished) {
      clearInterval(examTimer);
      return;
    }
    const remaining = state.exam.endsAt - Date.now();
    const timer = document.querySelector("#exam-timer");
    if (timer) timer.textContent = formatTimer(Math.max(0, remaining));
    if (remaining <= 0) finishExam();
  }, 1000);
}

function formatTimer(milliseconds) {
  const totalSeconds = Math.ceil(milliseconds / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function updateExamNav() {
  document.querySelectorAll("[data-exam-index]").forEach((button) => {
    const question = state.exam.questions[Number(button.dataset.examIndex)];
    button.classList.toggle(
      "answered",
      Boolean(
        state.exam.answers[question.id]?.length ||
          state.exam.visited.has(question.id),
      ),
    );
  });
}

function examQuestionSnapshot(question) {
  return {
    id: question.id,
    topic: question.topic,
    difficulty: question.difficulty,
    prompt: question.prompt,
    context: question.context,
    options: question.options.map((option) => ({
      id: option.id,
      text: option.text,
      correct: option.correct,
      explanation: option.explanation,
    })),
    explanation: question.explanation,
    source: question.source,
    tags: question.tags,
    _languages: question._languages,
  };
}

function persistExamHistory() {
  state.examHistory = state.examHistory.slice(0, MAX_EXAM_HISTORY);
  saveState();
  return true;
}

function archiveCompletedExam(finishedAt) {
  if (state.exam.historyId) return true;
  const record = {
    version: 1,
    id: `exam-${finishedAt}-${Math.random().toString(36).slice(2, 8)}`,
    startedAt: state.exam.startedAt,
    finishedAt,
    durationMs: Math.max(0, finishedAt - state.exam.startedAt),
    language: state.language,
    questions: state.exam.questions.map(examQuestionSnapshot),
    answers: Object.fromEntries(
      state.exam.questions.map((question) => [
        question.id,
        [...(state.exam.answers[question.id] || [])],
      ]),
    ),
    optionOrder: { ...state.exam.optionOrder },
    result: state.exam.result,
  };
  state.examHistory = [
    record,
    ...state.examHistory.filter((entry) => entry.id !== record.id),
  ].slice(0, MAX_EXAM_HISTORY);
  state.exam.historyId = record.id;
  return true;
}

function finishExam() {
  clearInterval(examTimer);
  const result = scoreExam(state.exam.questions, state.exam.answers);
  state.exam.questions.forEach((question) => {
    const detail = result.details.find((entry) => entry.id === question.id);
    state.progress[question.id] = updateProgress(
      state.progress[question.id],
      detail.correct,
    );
    state.progress[question.id].lastSelection = [
      ...(state.exam.answers[question.id] || []),
    ];
  });
  state.exam.finished = true;
  state.exam.result = result;
  state.exam.reviewMode = "summary";
  state.exam.reviewIndex = 0;
  archiveCompletedExam(Date.now());
  saveState();
  renderExam();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderExamResult() {
  const mode = state.exam.reviewMode || "summary";
  if (mode === "single" || mode === "all") {
    renderExamReview(mode);
    return;
  }

  const { result, questions } = state.exam;
  const rows = result.details
    .map((detail, index) => {
      const question = questions.find((entry) => entry.id === detail.id);
      return `
        <div class="result-row ${detail.correct ? "ok" : "fail"}">
          <span>${detail.correct ? "✓" : "✗"}</span>
          <span>${escapeHtml(localized(question.prompt))}</span>
          <button class="ghost-button" data-review-index="${index}">${state.language === "de" ? "Ansehen" : "Review"}</button>
        </div>
      `;
    })
    .join("");
  content.innerHTML = `
    <section class="result-card">
      <p class="eyebrow">${state.language === "de" ? "Prüfung ausgewertet" : "Exam evaluated"}</p>
      <h2>${result.points} ${state.language === "de" ? "von" : "of"} ${result.maximum} ${state.language === "de" ? "Punkten" : "points"}</h2>
      <div class="result-score">${result.percentage}%</div>
      <p>${state.language === "de" ? (result.percentage >= 80 ? "Starker Stand. Jetzt gezielt die verbliebenen Fehlermuster beseitigen." : result.percentage >= 60 ? "Solide Basis, aber die Alles-oder-nichts-Fallen kosten noch Punkte." : "Die Grundlagen und Abgrenzungen sollten vor der nächsten Simulation systematisch wiederholt werden.") : (result.percentage >= 80 ? "Strong status. Now target the remaining error patterns." : result.percentage >= 60 ? "Solid base, but all-or-nothing traps still cost points." : "Repeat fundamentals and distinctions before the next simulation.")}</p>
      <div class="review-mode-actions">
        <button class="primary-button" id="review-one-by-one">${state.language === "de" ? "Ergebnisse einzeln durchgehen" : "Review one by one"}</button>
        <button class="secondary-button" id="review-all">${state.language === "de" ? "Alle Lösungen untereinander" : "Show all solutions"}</button>
      </div>
      <div class="result-breakdown">${rows}</div>
      <div class="hero-actions" style="justify-content:center">
        <button class="primary-button" id="new-exam">${state.language === "de" ? "Neue Prüfung" : "New exam"}</button>
        <button class="secondary-button" id="practice-mistakes">${state.language === "de" ? "Fehler trainieren" : "Practice mistakes"}</button>
        <button class="ghost-button" id="open-exam-history">${state.language === "de" ? "Zum Prüfungsverlauf" : "Open exam history"}</button>
      </div>
    </section>
  `;
  content.querySelector("#new-exam").addEventListener("click", () => {
    state.exam = null;
    renderExam();
  });
  content.querySelector("#practice-mistakes").addEventListener("click", () => {
    const wrongIds = result.details
      .filter((detail) => !detail.correct)
      .map((detail) => detail.id);
    if (!wrongIds.length) {
      showToast(
        state.language === "de"
          ? "In dieser Prüfung gab es keine Fehler."
          : "There were no mistakes in this exam.",
      );
      return;
    }
    startQuestionSet(wrongIds);
  });
  content.querySelector("#open-exam-history").addEventListener("click", () => {
    navigate("history");
  });
  content.querySelector("#review-one-by-one").addEventListener("click", () => {
    state.exam.reviewMode = "single";
    state.exam.reviewIndex = 0;
    renderExam();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  content.querySelector("#review-all").addEventListener("click", () => {
    state.exam.reviewMode = "all";
    renderExam();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  content.querySelectorAll("[data-review-index]").forEach((button) => {
    button.addEventListener("click", () => {
      state.exam.reviewMode = "single";
      state.exam.reviewIndex = Number(button.dataset.reviewIndex);
      renderExam();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });
}

function renderExamReviewQuestion(question, index, showNavigation = false) {
  const selected = new Set(state.exam.answers[question.id] || []);
  const exact = exactMatch([...selected], question.options);
  const topic = topicContent(topicById(question.topic));
  const options = orderedOptions(question, "exam")
    .map((option, optionIndex) => {
      const checked = selected.has(option.id);
      const classes = [];
      if (option.correct) classes.push("correct-option");
      if (checked && !option.correct) classes.push("wrong-selected");
      if (option.correct && !checked) classes.push("missed-correct");
      if (!option.correct && !checked) classes.push("correctly-unselected");

      let verdict;
      if (option.correct && checked) {
        verdict = state.language === "de"
          ? "✓ Richtig und von dir ausgewählt."
          : "✓ Correct and selected by you.";
      } else if (option.correct) {
        verdict = state.language === "de"
          ? "✓ Richtig, aber von dir nicht ausgewählt."
          : "✓ Correct, but not selected by you.";
      } else if (checked) {
        verdict = state.language === "de"
          ? "✗ Falsch, aber von dir ausgewählt."
          : "✗ Incorrect, but selected by you.";
      } else {
        verdict = state.language === "de"
          ? "✗ Falsch und richtigerweise nicht ausgewählt."
          : "✗ Incorrect and correctly left unselected.";
      }

      return `
        <label class="option review-option ${classes.join(" ")}">
          <input type="checkbox" ${checked ? "checked" : ""} disabled>
          <div>
            <div class="option-main">
              <span class="option-letter">${String.fromCharCode(65 + optionIndex)}</span>
              <span class="option-text">${escapeHtml(localized(option.text))}</span>
            </div>
            <div class="option-explanation"><strong>${verdict}</strong> ${escapeHtml(localized(option.explanation || ""))}</div>
          </div>
        </label>
      `;
    })
    .join("");

  return `
    <article class="question-card exam-review-question ${exact ? "review-correct" : "review-wrong"}">
      <div class="question-topline">
        <div class="question-meta">
          <span class="badge">${state.language === "de" ? "Frage" : "Question"} ${index + 1} / ${state.exam.questions.length}</span>
          <span class="badge" style="border-color:${escapeHtml(topic?.color || "#555")}">${escapeHtml(topic?.shortTitle || topic?.title || question.topic)}</span>
          <span class="badge difficulty-${question.difficulty}">${question.difficulty} · ${escapeHtml(difficultyLabel(question.difficulty))}</span>
        </div>
        <span class="review-status ${exact ? "ok" : "fail"}">${exact ? "✓ " : "✗ "}${state.language === "de" ? (exact ? "Exakt richtig" : "Nicht exakt") : (exact ? "Exactly correct" : "Not exact")}</span>
      </div>
      <div class="question-content">
        <h2>${escapeHtml(localized(question.prompt))}</h2>
        ${question.context ? `<div class="question-context">${escapeHtml(localized(question.context))}</div>` : ""}
        <div class="review-legend">
          <span class="selected-marker">${state.language === "de" ? "Häkchen = deine Auswahl" : "Checkmark = your selection"}</span>
          <span class="correct-marker">${state.language === "de" ? "Grün = richtige Aussage" : "Green = correct statement"}</span>
          <span class="wrong-marker">${state.language === "de" ? "Rot = falsch ausgewählt" : "Red = incorrectly selected"}</span>
        </div>
        <div class="options-list">${options}</div>
        <div class="feedback-banner ${exact ? "correct" : "wrong"}">
          <strong>${exact ? (state.language === "de" ? "Exakt richtig — 1 Punkt." : "Exactly correct — 1 point.") : (state.language === "de" ? "Nicht exakt — 0 Punkte." : "Not exact — 0 points.")}</strong>
          <p>${escapeHtml(localized(question.explanation))}</p>
        </div>
      </div>
      ${showNavigation ? `
        <div class="question-actions review-question-actions">
          <button class="secondary-button" data-review-direction="-1" ${index === 0 ? "disabled" : ""}>${state.language === "de" ? "← Vorherige Frage" : "← Previous question"}</button>
          <button class="primary-button" data-review-direction="1" ${index === state.exam.questions.length - 1 ? "disabled" : ""}>${state.language === "de" ? "Nächste Frage →" : "Next question →"}</button>
        </div>
      ` : ""}
    </article>
  `;
}

function renderExamReview(mode) {
  const { result, questions } = state.exam;
  const wrongCount = result.maximum - result.points;
  const toolbar = `
    <div class="exam-review-toolbar">
      <button class="ghost-button" id="review-summary">${state.language === "de" ? "← Zurück zur Übersicht" : "← Back to summary"}</button>
      <div>
        <strong>${result.points} / ${result.maximum}</strong>
        <span>${state.language === "de" ? `${wrongCount} nicht exakt` : `${wrongCount} not exact`}</span>
      </div>
      <div class="review-toolbar-actions">
        <button class="ghost-button" id="review-history">${state.language === "de" ? "Verlauf" : "History"}</button>
        <button class="secondary-button" id="toggle-review-mode">${mode === "single" ? (state.language === "de" ? "Alle untereinander" : "Show all") : (state.language === "de" ? "Einzeln durchgehen" : "One by one")}</button>
      </div>
    </div>
  `;

  if (mode === "all") {
    content.innerHTML = `
      ${toolbar}
      <div class="review-all-heading">
        <p class="eyebrow">${state.language === "de" ? "Vollständige Auswertung" : "Complete review"}</p>
        <h2>${state.language === "de" ? "Alle Fragen und Lösungen" : "All questions and solutions"}</h2>
        <p>${state.language === "de" ? "Scrolle durch die gesamte Prüfung. Jede Aussage zeigt deine Auswahl, die richtige Bewertung und die Begründung." : "Scroll through the complete exam. Every statement shows your selection, the correct evaluation, and its explanation."}</p>
      </div>
      <nav class="review-jump-nav" aria-label="${state.language === "de" ? "Ergebnisfragen" : "Result questions"}">
        ${result.details.map((detail, index) => `<a href="#exam-review-${index + 1}" class="${detail.correct ? "ok" : "fail"}">${index + 1}</a>`).join("")}
      </nav>
      <div class="exam-review-all">
        ${questions.map((question, index) => `<section id="exam-review-${index + 1}">${renderExamReviewQuestion(question, index)}</section>`).join("")}
      </div>
      <div class="review-end-actions">
        <button class="secondary-button" id="review-summary-bottom">${state.language === "de" ? "Zurück zur Ergebnisübersicht" : "Back to result summary"}</button>
      </div>
    `;
  } else {
    const index = Math.max(
      0,
      Math.min(
        Number(state.exam.reviewIndex) || 0,
        state.exam.questions.length - 1,
      ),
    );
    state.exam.reviewIndex = index;
    const question = questions[index];
    content.innerHTML = `
      ${toolbar}
      <div class="exam-layout exam-review-layout">
        <div>${renderExamReviewQuestion(question, index, true)}</div>
        <nav class="exam-nav review-exam-nav" aria-label="${state.language === "de" ? "Ergebnisfragen" : "Result questions"}">
          ${result.details.map((detail, questionIndex) => `
            <button data-review-nav-index="${questionIndex}" class="${questionIndex === index ? "active" : ""} ${detail.correct ? "review-ok" : "review-fail"}">${questionIndex + 1}</button>
          `).join("")}
        </nav>
      </div>
    `;
  }

  const showSummary = () => {
    state.exam.reviewMode = "summary";
    renderExam();
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  content.querySelector("#review-summary")?.addEventListener("click", showSummary);
  content.querySelector("#review-summary-bottom")?.addEventListener("click", showSummary);
  content.querySelector("#review-history")?.addEventListener("click", () => {
    navigate("history");
  });
  content.querySelector("#toggle-review-mode")?.addEventListener("click", () => {
    state.exam.reviewMode = mode === "single" ? "all" : "single";
    renderExam();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  content.querySelectorAll("[data-review-nav-index]").forEach((button) => {
    button.addEventListener("click", () => {
      state.exam.reviewIndex = Number(button.dataset.reviewNavIndex);
      renderExam();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });
  content.querySelectorAll("[data-review-direction]").forEach((button) => {
    button.addEventListener("click", () => {
      state.exam.reviewIndex += Number(button.dataset.reviewDirection);
      renderExam();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });
}

function formatExamHistoryDate(timestamp) {
  return new Intl.DateTimeFormat(
    state.language === "de" ? "de-DE" : "en-US",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(new Date(timestamp));
}

function formatExamDuration(milliseconds) {
  const totalMinutes = Math.max(1, Math.round(milliseconds / 60000));
  if (totalMinutes < 60) {
    return `${totalMinutes} ${state.language === "de" ? "Min." : "min"}`;
  }
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${hours} ${state.language === "de" ? "Std." : "h"}${minutes ? ` ${minutes} ${state.language === "de" ? "Min." : "min"}` : ""}`;
}

function resultForHistoryEntry(entry) {
  return scoreExam(entry.questions, entry.answers || {});
}

function openExamHistoryEntry(entryId, mode = "summary") {
  const entry = state.examHistory.find((item) => item.id === entryId);
  if (!entry) return;
  const questions = JSON.parse(JSON.stringify(entry.questions || []));
  if (!questions.length) {
    showToast(
      state.language === "de"
        ? "Diese gespeicherte Prüfung enthält keine lesbaren Fragen."
        : "This saved exam contains no readable questions.",
    );
    return;
  }
  state.exam = {
    questions,
    index: 0,
    answers: JSON.parse(JSON.stringify(entry.answers || {})),
    visited: new Set(questions.map((question) => question.id)),
    optionOrder: { ...(entry.optionOrder || {}) },
    startedAt: entry.startedAt,
    endsAt: entry.finishedAt,
    finished: true,
    result: resultForHistoryEntry(entry),
    reviewMode: mode,
    reviewIndex: 0,
    historyId: entry.id,
  };
  navigate("exam");
}

function renderExamHistory() {
  const entries = [...state.examHistory].sort(
    (a, b) => b.finishedAt - a.finishedAt,
  );
  if (!entries.length) {
    content.innerHTML = `
      <div class="empty-state history-empty">
        <h2>${state.language === "de" ? "Noch keine Prüfungen gespeichert" : "No saved exams yet"}</h2>
        <p>${state.language === "de" ? "Sobald du eine Prüfung abgibst, wird sie in diesem Browser gespeichert und erscheint hier mit vollständiger Auswertung." : "Once you submit an exam, it is saved in this browser and appears here with its complete review."}</p>
        <button class="primary-button" id="history-start-exam">${state.language === "de" ? "Erste Prüfung starten" : "Start first exam"}</button>
      </div>
    `;
    content.querySelector("#history-start-exam").addEventListener("click", () => {
      state.exam = null;
      navigate("exam");
    });
    return;
  }

  const results = entries.map(resultForHistoryEntry);
  const average = Math.round(
    results.reduce((sum, result) => sum + result.percentage, 0) /
      results.length,
  );
  const best = Math.max(...results.map((result) => result.percentage));
  const totalQuestions = results.reduce(
    (sum, result) => sum + result.maximum,
    0,
  );

  content.innerHTML = `
    <section class="history-hero">
      <div>
        <p class="eyebrow">${state.language === "de" ? "Lokal in diesem Browser gespeichert" : "Stored locally in this browser"}</p>
        <h2>${state.language === "de" ? "Deine bisherigen Prüfungen" : "Your previous exams"}</h2>
        <p>${state.language === "de" ? `Bis zu ${MAX_EXAM_HISTORY} abgegebene Prüfungen werden gespeichert. Serverneustarts und normales Neuladen löschen diesen Verlauf nicht. Er geht nur verloren, wenn du die Browserdaten für diese Seite löschst oder einen anderen Browser beziehungsweise eine andere Adresse verwendest.` : `Up to ${MAX_EXAM_HISTORY} submitted exams are saved. Server restarts and normal reloads do not remove this history. It is lost only if you clear this site's browser data or use another browser or address.`}</p>
      </div>
      <button class="primary-button" id="history-new-exam">${state.language === "de" ? "Neue Prüfung starten" : "Start new exam"}</button>
    </section>

    <div class="history-stats">
      <article><span>${state.language === "de" ? "Prüfungen" : "Exams"}</span><strong>${entries.length}</strong></article>
      <article><span>${state.language === "de" ? "Durchschnitt" : "Average"}</span><strong>${average}%</strong></article>
      <article><span>${state.language === "de" ? "Bestes Ergebnis" : "Best result"}</span><strong>${best}%</strong></article>
      <article><span>${state.language === "de" ? "Beantwortete Fragen" : "Answered questions"}</span><strong>${totalQuestions}</strong></article>
    </div>

    <div class="section-heading history-heading">
      <div>
        <p class="eyebrow">${entries.length} ${state.language === "de" ? "gespeicherte Versuche" : "saved attempts"}</p>
        <h3>${state.language === "de" ? "Neueste zuerst" : "Newest first"}</h3>
      </div>
      <button class="danger-button" id="clear-exam-history">${state.language === "de" ? "Verlauf löschen" : "Clear history"}</button>
    </div>

    <div class="exam-history-list">
      ${entries.map((entry) => {
        const result = resultForHistoryEntry(entry);
        const topicIds = [...new Set(entry.questions.map((question) => question.topic))];
        return `
          <article class="exam-history-card">
            <div class="history-score ${result.percentage >= 60 ? "ok" : "fail"}">
              <strong>${result.percentage}%</strong>
              <span>${result.points} / ${result.maximum}</span>
            </div>
            <div class="history-details">
              <p class="eyebrow">${escapeHtml(formatExamHistoryDate(entry.finishedAt))}</p>
              <h3>${state.language === "de" ? "Prüfungssimulation" : "Exam simulation"} · ${result.maximum} ${state.language === "de" ? "Fragen" : "questions"}</h3>
              <div class="history-meta">
                <span>${state.language === "de" ? "Dauer" : "Duration"}: ${escapeHtml(formatExamDuration(entry.durationMs || entry.finishedAt - entry.startedAt))}</span>
                <span>${state.language === "de" ? "Richtig" : "Correct"}: ${result.points}</span>
                <span>${state.language === "de" ? "Nicht exakt" : "Not exact"}: ${result.maximum - result.points}</span>
              </div>
              <div class="focus-chips">
                ${topicIds.map((topicId) => {
                  const topic = topicContent(topicById(topicId));
                  return `<span class="chip">${escapeHtml(topic?.shortTitle || topic?.title || topicId)}</span>`;
                }).join("")}
              </div>
            </div>
            <div class="history-actions">
              <button class="primary-button" data-history-open="${escapeHtml(entry.id)}">${state.language === "de" ? "Ergebnis öffnen" : "Open result"}</button>
              <button class="secondary-button" data-history-all="${escapeHtml(entry.id)}">${state.language === "de" ? "Alle Lösungen" : "All solutions"}</button>
              <button class="ghost-button" data-history-delete="${escapeHtml(entry.id)}">${state.language === "de" ? "Löschen" : "Delete"}</button>
            </div>
          </article>
        `;
      }).join("")}
    </div>
  `;

  content.querySelector("#history-new-exam").addEventListener("click", () => {
    state.exam = null;
    navigate("exam");
  });
  content.querySelector("#clear-exam-history").addEventListener("click", () => {
    if (
      !window.confirm(
        state.language === "de"
          ? "Wirklich alle gespeicherten Prüfungen und Ergebnisse löschen?"
          : "Delete all saved exams and results?",
      )
    ) return;
    state.examHistory = [];
    saveState();
    renderExamHistory();
  });
  content.querySelectorAll("[data-history-open]").forEach((button) => {
    button.addEventListener("click", () => {
      openExamHistoryEntry(button.dataset.historyOpen, "summary");
    });
  });
  content.querySelectorAll("[data-history-all]").forEach((button) => {
    button.addEventListener("click", () => {
      openExamHistoryEntry(button.dataset.historyAll, "all");
    });
  });
  content.querySelectorAll("[data-history-delete]").forEach((button) => {
    button.addEventListener("click", () => {
      const entry = state.examHistory.find(
        (item) => item.id === button.dataset.historyDelete,
      );
      if (
        !window.confirm(
          state.language === "de"
            ? `Prüfung vom ${formatExamHistoryDate(entry.finishedAt)} löschen?`
            : `Delete exam from ${formatExamHistoryDate(entry.finishedAt)}?`,
        )
      ) return;
      state.examHistory = state.examHistory.filter(
        (item) => item.id !== button.dataset.historyDelete,
      );
      persistExamHistory();
      renderExamHistory();
    });
  });
}

function renderGlossary() {
  if (state.selectedGlossaryTerm) {
    const entry = state.data.glossary.find(
      (item) => item.term === state.selectedGlossaryTerm,
    );
    if (entry) {
      renderGlossaryDetail(entry);
      return;
    }
    state.selectedGlossaryTerm = null;
  }

  const query = state.glossaryQuery.trim().toLowerCase();
  const allTags = [
    ...new Set(state.data.glossary.flatMap((entry) => entry.tags || [])),
  ].sort((a, b) => a.localeCompare(b));
  const entries = state.data.glossary.filter((entry) => {
    const topicMatch =
      state.glossaryTopic === "all" || entry.topic === state.glossaryTopic;
    const tagMatch =
      state.glossaryTag === "all" || (entry.tags || []).includes(state.glossaryTag);
    const en = entry.translations?.en || {};
    const detail = entry.detail || {};
    const text = [
      entry.term,
      entry.definition,
      (entry.aliases || []).join(" "),
      (entry.tags || []).join(" "),
      en.term || "",
      en.definition || "",
      localized(detail.summary || ""),
      (detail.related || []).join(" "),
    ]
      .join(" ")
      .toLowerCase();
    return topicMatch && tagMatch && (!query || text.includes(query));
  });
  content.innerHTML = `
    <div class="glossary-controls">
      <input id="glossary-search" type="search" placeholder="${state.language === "de" ? "Begriff oder Definition durchsuchen …" : "Search term or definition …"}" value="${escapeHtml(state.glossaryQuery)}">
      <select id="glossary-topic">
        <option value="all">${state.language === "de" ? "Alle Themen" : "All topics"}</option>
        ${state.data.topics.map((topic) => {
          const view = topicContent(topic);
          return `<option value="${escapeHtml(topic.id)}" ${state.glossaryTopic === topic.id ? "selected" : ""}>${escapeHtml(view.title)}</option>`;
        }).join("")}
      </select>
      <select id="glossary-tag">
        <option value="all">${state.language === "de" ? "Alle Tags" : "All tags"}</option>
        ${allTags.map((tag) => `<option value="${escapeHtml(tag)}" ${state.glossaryTag === tag ? "selected" : ""}>${escapeHtml(tag)}</option>`).join("")}
      </select>
    </div>
    <div class="section-heading">
      <div><p class="eyebrow">${entries.length} / ${state.data.glossary.length} ${state.language === "de" ? "Einträge" : "entries"}</p><h3>${state.language === "de" ? "Wichtige Begriffe" : "Key terms"}</h3></div>
    </div>
    <div class="glossary-grid">
      ${entries
        .map(
          (entry) => {
            const topic = topicContent(topicById(entry.topic));
            return `
            <article class="glossary-card" data-glossary-term="${escapeHtml(entry.term)}" tabindex="0">
              <h3>${escapeHtml(glossaryTerm(entry))}</h3>
              <p>${escapeHtml(glossaryDefinition(entry))}</p>
              <div class="tag-row">${(entry.tags || []).slice(0, 4).map((tag) => `<span class="chip">${escapeHtml(tag)}</span>`).join("")}</div>
              <small>${escapeHtml(topic?.title || entry.topic)}${entry.aliases?.length ? ` · ${state.language === "de" ? "auch" : "also"}: ${escapeHtml(entry.aliases.join(", "))}` : ""}</small>
            </article>
          `;
          },
        )
        .join("") || `<div class="empty-state">${state.language === "de" ? "Kein Begriff passt zu dieser Suche." : "No term matches this search."}</div>`}
    </div>
  `;
  content.querySelector("#glossary-search").addEventListener("input", (event) => {
    state.glossaryQuery = event.target.value;
    renderGlossary();
    const search = content.querySelector("#glossary-search");
    search.focus();
    search.setSelectionRange(search.value.length, search.value.length);
  });
  content.querySelector("#glossary-topic").addEventListener("change", (event) => {
    state.glossaryTopic = event.target.value;
    renderGlossary();
  });
  content.querySelector("#glossary-tag").addEventListener("change", (event) => {
    state.glossaryTag = event.target.value;
    renderGlossary();
  });
  content.querySelectorAll("[data-glossary-term]").forEach((card) => {
    const open = () => {
      state.selectedGlossaryTerm = card.dataset.glossaryTerm;
      renderGlossary();
      window.scrollTo({ top: 0, behavior: "smooth" });
    };
    card.addEventListener("click", open);
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") open();
    });
  });
}

function renderGlossaryDetail(entry) {
  const detail = entry.detail || {};
  const topic = topicContent(topicById(entry.topic));
  const list = (items = []) => items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  const localizedList = (value) => {
    if (!value) return [];
    if (Array.isArray(value)) return value;
    return value[state.language] || value.de || value.en || [];
  };
  const qa = detail.examQuestions || [];
  const keyPoints = localizedList(detail.keyPoints);
  const related = (detail.related || [])
    .map((term) => state.data.glossary.find((item) => item.term === term))
    .filter(Boolean);
  const sourceSectionIndex =
    typeof detail.sourceSectionIndex === "object"
      ? detail.sourceSectionIndex[state.language] ?? detail.sourceSectionIndex.de ?? 0
      : detail.sourceSectionIndex ?? 0;

  content.innerHTML = `
    <article class="summary-card" style="--topic-color:${escapeHtml(topic?.color || "#b8f34a")}">
      <header class="summary-hero">
        <button class="ghost-button" id="glossary-back">${state.language === "de" ? "← Zurück zum Glossar" : "← Back to glossary"}</button>
        <span class="topic-kicker">${state.language === "de" ? "Kategorie" : "Category"} · ${escapeHtml(topic?.title || entry.topic)}</span>
        <h2>${escapeHtml(glossaryTerm(entry))}</h2>
        <p>${escapeHtml(glossaryDefinition(entry))}</p>
        ${detail.expansion ? `<div class="formula-box">${state.language === "de" ? "Abkürzung" : "Expansion"}: ${escapeHtml(localized(detail.expansion))}</div>` : ""}
        <div class="focus-chips">${(entry.tags || []).map((tag) => `<button class="chip" data-detail-tag="${escapeHtml(tag)}">${escapeHtml(tag)}</button>`).join("")}</div>
      </header>
      <div class="summary-body">
        <div class="beginner-overview">
          <section class="beginner-card">
            <span>${state.language === "de" ? "Ohne Vorwissen" : "No prior knowledge needed"}</span>
            <h3>${state.language === "de" ? "Einfach erklärt" : "In simple terms"}</h3>
            <p>${escapeHtml(localized(detail.simpleExplanation || detail.summary || ""))}</p>
          </section>
          <section class="takeaway-card">
            <span>${state.language === "de" ? "Kurzfassung" : "Short version"}</span>
            <h3>${state.language === "de" ? "Für die Klausur merken" : "Remember for the exam"}</h3>
            <p>${escapeHtml(localized(detail.examTakeaway || detail.summary || ""))}</p>
          </section>
        </div>
        <section class="summary-section">
          <h3>${state.language === "de" ? "Auf einen Blick" : "At a glance"}</h3>
          <div>
            <p class="detail-lead">${escapeHtml(localized(detail.summary || ""))}</p>
            ${keyPoints.length ? `<ul>${list(keyPoints)}</ul>` : ""}
          </div>
        </section>
        <section class="summary-section">
          <h3>${state.language === "de" ? "Vollständige Erklärung" : "Complete explanation"}</h3>
          <div><ul>${list(localizedList(detail.details))}</ul></div>
        </section>
        <section class="summary-section">
          <h3>${state.language === "de" ? "Konkrete Beispiele" : "Concrete examples"}</h3>
          <div><ul>${list(localizedList(detail.examples))}</ul></div>
        </section>
        <section class="summary-section">
          <h3>${state.language === "de" ? "Verwechslungen & Grenzen" : "Misconceptions & limits"}</h3>
          <div><ul>${list(localizedList(detail.watchOut))}</ul></div>
        </section>
        <section class="summary-section">
          <h3>${state.language === "de" ? "Prüfungsfragen mit Musterantwort" : "Exam questions with model answers"}</h3>
          <div class="exam-answer-list">
            ${qa.map((item) => `
              <div class="exam-answer-card">
                <p class="eyebrow">${state.language === "de" ? "Frage" : "Question"}${item.source?.pages ? ` · ${escapeHtml(item.source.pages)}` : ""}</p>
                <strong>${escapeHtml(localized(item.q))}</strong>
                <div class="model-answer">
                  <span>${state.language === "de" ? "Musterantwort" : "Model answer"}</span>
                  <p>${escapeHtml(localized(item.a))}</p>
                </div>
                ${item.questionId ? `<button class="ghost-button compact" data-detail-question="${escapeHtml(item.questionId)}">${state.language === "de" ? "Diese Frage interaktiv üben" : "Practice this question"}</button>` : ""}
              </div>
            `).join("")}
          </div>
        </section>
        <section class="summary-section">
          <h3>${state.language === "de" ? "Im Lernstoff" : "In the study notes"}</h3>
          <div>
            <p>${state.language === "de" ? "Der Begriff gehört fachlich zu folgendem Kapitel:" : "This concept belongs to the following chapter:"}</p>
            <button class="secondary-button" id="open-source-section">
              ${escapeHtml(topic?.title || entry.topic)} · ${escapeHtml(localized(detail.sourceSection || ""))}
            </button>
            ${detail.sourceDeck ? `<p class="source-note">${state.language === "de" ? "Quelle" : "Source"}: ${escapeHtml(detail.sourceDeck)}</p>` : ""}
          </div>
        </section>
        <section class="summary-section">
          <h3>${state.language === "de" ? "Verwandte Begriffe" : "Related terms"}</h3>
          <div class="focus-chips">
            ${related.map((item) => `<button class="chip" data-related-term="${escapeHtml(item.term)}">${escapeHtml(glossaryTerm(item))}</button>`).join("") || `<span class="chip">${state.language === "de" ? "Keine direkten Verweise" : "No direct references"}</span>`}
          </div>
        </section>
      </div>
    </article>
  `;

  content.querySelector("#glossary-back").addEventListener("click", () => {
    state.selectedGlossaryTerm = null;
    renderGlossary();
  });
  content.querySelectorAll("[data-related-term]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedGlossaryTerm = button.dataset.relatedTerm;
      renderGlossary();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });
  content.querySelectorAll("[data-detail-tag]").forEach((button) => {
    button.addEventListener("click", () => {
      state.glossaryTag = button.dataset.detailTag;
      state.selectedGlossaryTerm = null;
      renderGlossary();
    });
  });
  content.querySelector("#open-source-section")?.addEventListener("click", () => {
    state.learnTopic = entry.topic;
    state.learnSection = Number(sourceSectionIndex);
    navigate("learn");
  });
  content.querySelectorAll("[data-detail-question]").forEach((button) => {
    button.addEventListener("click", () => {
      startQuestionSet([button.dataset.detailQuestion]);
    });
  });
}

function renderSlides() {
  const slides = state.data.slides || [];
  const selected =
    slides.find((slide) => slide.id === state.selectedSlide) || slides[0];
  if (!selected) {
    content.innerHTML = `<div class="empty-state">${state.language === "de" ? "Keine Slides gefunden." : "No slides found."}</div>`;
    return;
  }
  state.selectedSlide = selected.id;
  content.innerHTML = `
    <div class="slides-layout">
      <aside class="panel">
        <p class="eyebrow">${state.language === "de" ? "Lecture slides" : "Lecture slides"}</p>
        <h3>${state.language === "de" ? "PDF auswählen" : "Choose PDF"}</h3>
        <div class="slide-list">
          ${slides
            .map(
              (slide) => `
                <button class="slide-button ${slide.id === selected.id ? "active" : ""}" data-slide="${escapeHtml(slide.id)}">
                  <strong>${escapeHtml(slide.title)}</strong><br>
                  <span>${escapeHtml(slide.file)}</span>
                </button>
              `,
            )
            .join("")}
        </div>
        <div class="hero-actions">
          <a class="secondary-button" href="${escapeHtml(selected.path)}" target="_blank" rel="noreferrer">${state.language === "de" ? "In neuem Tab öffnen" : "Open in new tab"}</a>
        </div>
      </aside>
      <section>
        <iframe class="pdf-frame" title="${escapeHtml(selected.title)}" src="${escapeHtml(selected.path)}"></iframe>
      </section>
    </div>
  `;
  content.querySelectorAll("[data-slide]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedSlide = button.dataset.slide;
      renderSlides();
    });
  });
}

function validateImportedPayload(payload) {
  if (payload.version !== 1 || !Array.isArray(payload.questions)) {
    throw new Error("Erwartet werden version: 1 und ein questions-Array.");
  }
  const known = new Set(state.data.questions.map((question) => question.id));
  const validTopics = new Set(state.data.topics.map((topic) => topic.id));
  for (const question of payload.questions) {
    if (
      !question.id ||
      !question.topic ||
      !question.prompt ||
      !Array.isArray(question.options) ||
      question.options.length < 2
    ) {
      throw new Error("Jede Frage benötigt id, topic, prompt und mindestens zwei Optionen.");
    }
    if (!validTopics.has(question.topic)) {
      throw new Error(`${question.id}: Unbekanntes Thema ${question.topic}.`);
    }
    if (!Number.isInteger(question.difficulty) || question.difficulty < 1 || question.difficulty > 5) {
      throw new Error(`${question.id}: difficulty muss zwischen 1 und 5 liegen.`);
    }
    if (known.has(question.id)) {
      throw new Error(`Die ID ${question.id} existiert bereits.`);
    }
    if (
      !question.options.every(
        (option) =>
          option.id &&
          option.text &&
          typeof option.correct === "boolean",
      )
    ) {
      throw new Error(`${question.id}: Optionen benötigen id, text und correct.`);
    }
    const optionIds = question.options.map((option) => option.id);
    if (new Set(optionIds).size !== optionIds.length) {
      throw new Error(`${question.id}: Option-IDs müssen eindeutig sein.`);
    }
    question._sourceFile = "Database import";
    question._importedAt = Date.now();
    question.status = question.status || "active";
    question._status = question.status;
    question._languages = question.languages || [
      "de",
      ...(question.prompt?.en || question.options.some((option) => option.text?.en)
        ? ["en"]
        : []),
    ];
    known.add(question.id);
  }
  return payload.questions;
}

async function importQuestionFile(file) {
  try {
    const payload = JSON.parse(await file.text());
    const imported = validateImportedPayload(payload);
    state.customQuestions = [...customQuestions(), ...imported];
    await saveState();
    state.data.questions.push(...imported);
    const source = state.data.sources.find(
      (entry) => entry.file === "Database import",
    );
    if (source) source.count += imported.length;
    document.querySelector("#sidebar-question-count").textContent =
      sidebarCountLabel();
    showToast(state.language === "de" ? `${imported.length} Fragen importiert.` : `${imported.length} questions imported.`);
    renderLibrary();
  } catch (error) {
    showToast(state.language === "de" ? `Import fehlgeschlagen: ${error.message}` : `Import failed: ${error.message}`);
  }
}

function setQuestionStatus(questionId, status, persist = true) {
  state.questionOverrides[questionId] = {
    ...(state.questionOverrides[questionId] || {}),
    status,
    changedAt: Date.now(),
  };
  if (persist) saveState();
}

function renderLibrary() {
  const schemaExample = `{
  "version": 1,
  "label": "Eigene Fragen",
  "questions": [{
    "id": "custom-unique-id",
    "topic": "nosql",
    "difficulty": 3,
    "status": "active",
    "languages": ["de", "en"],
    "prompt": {
      "de": "Welche Aussagen sind korrekt?",
      "en": "Which statements are correct?"
    },
    "options": [
      {
        "id": "a",
        "text": {
          "de": "Aussage",
          "en": "Statement"
        },
        "correct": true,
        "explanation": {
          "de": "Begründung",
          "en": "Explanation"
        }
      },
      {
        "id": "b",
        "text": {
          "de": "Weitere Aussage",
          "en": "Another statement"
        },
        "correct": false,
        "explanation": {
          "de": "Begründung",
          "en": "Explanation"
        }
      }
    ],
    "explanation": {
      "de": "Gesamterklärung",
      "en": "Overall explanation"
    },
    "source": {"deck": "Eigene Quelle", "pages": "S. 1"},
    "tags": ["Beispiel"]
  }]
}`;
  const statusCounts = state.data.questions.reduce(
    (acc, question) => {
      acc[questionLifecycle(question)] += 1;
      return acc;
    },
    { active: 0, archived: 0, deleted: 0 },
  );
  const sampleRows = state.data.questions
    .slice(0, 80)
    .map((question) => {
      const status = questionLifecycle(question);
      const topic = topicContent(topicById(question.topic));
      return `
        <div class="source-row">
          <div>
            <strong>${escapeHtml(localized(question.prompt))}</strong><br>
            <span>${escapeHtml(topic?.shortTitle || topic?.title || question.topic)} · ${escapeHtml(question.id)} · ${escapeHtml(status)}</span>
          </div>
          <button class="ghost-button" data-question-status="${status === "active" ? "archived" : "active"}" data-question-id="${escapeHtml(question.id)}">
            ${status === "active" ? (state.language === "de" ? "Archivieren" : "Archive") : (state.language === "de" ? "Wiederherstellen" : "Restore")}
          </button>
        </div>
      `;
    })
    .join("");

  content.innerHTML = `
    <div class="library-grid">
      <section class="panel">
        <p class="eyebrow">${state.language === "de" ? "Automatisch geladene Dateien" : "Automatically loaded files"}</p>
        <h2>${state.data.questions.length} ${state.language === "de" ? "Fragen im Pool" : "questions in the pool"}</h2>
        <p>${state.language === "de" ? "Beim Neuladen scannt der Server alle" : "On reload, the server scans all"} <code>*.json</code> ${state.language === "de" ? "Dateien in" : "files in"} <code>content/questions/</code>. ${state.language === "de" ? "Archivierte oder gelöschte Fragen bleiben erhalten, werden aber nicht trainiert." : "Archived or deleted questions are retained but not used for practice."}</p>
        <div class="stats-grid">
          <article class="stat-card"><span>${state.language === "de" ? "Aktiv" : "Active"}</span><strong>${statusCounts.active}</strong></article>
          <article class="stat-card"><span>${state.language === "de" ? "Archiviert" : "Archived"}</span><strong>${statusCounts.archived}</strong></article>
          <article class="stat-card"><span>${state.language === "de" ? "Als gelöscht markiert" : "Marked deleted"}</span><strong>${statusCounts.deleted}</strong></article>
          <article class="stat-card"><span>EN</span><strong>${state.data.questions.filter((question) => supportsLanguage(question, "en") && questionLifecycle(question) === "active").length}</strong></article>
        </div>
        <div class="source-list">
          ${state.data.sources.map((source) => `<div class="source-row"><strong>${escapeHtml(source.label)}</strong><span>${source.count} ${state.language === "de" ? "Fragen" : "questions"} · ${escapeHtml(source.file)}</span></div>`).join("")}
        </div>
        ${
          state.data.errors.length
            ? `<div class="error-list">${state.data.errors.map((error) => `<div class="pitfall-box">${escapeHtml(error)}</div>`).join("")}</div>`
            : ""
        }
        <div class="hero-actions">
          <button class="primary-button" id="reload-content">${state.language === "de" ? "Ordner neu laden" : "Reload folder"}</button>
          <button class="danger-button" id="archive-imports">${state.language === "de" ? "Datenbank-Importe archivieren" : "Archive database imports"}</button>
        </div>
      </section>
      <section class="panel">
        <p class="eyebrow">${state.language === "de" ? "Ohne Server-Neustart" : "Without server restart"}</p>
        <h3>${state.language === "de" ? "JSON-Datei direkt importieren" : "Import JSON file directly"}</h3>
        <label class="drop-zone" id="drop-zone">
          <input id="question-file" type="file" accept=".json,application/json">
          <span><strong>${state.language === "de" ? "Datei auswählen oder hier ablegen" : "Choose a file or drop it here"}</strong><br>${state.language === "de" ? "Die Fragen werden dauerhaft in SQLite gespeichert." : "Questions are stored permanently in SQLite."}</span>
        </label>
      </section>
    </div>
    <div class="section-heading"><div><p class="eyebrow">Soft delete</p><h3>${state.language === "de" ? "Fragen verwalten" : "Manage questions"}</h3></div></div>
    <section class="panel">
      <p>${state.language === "de" ? "Die Liste zeigt die ersten 80 Fragen. Archivieren blendet eine Frage aus Übung und Prüfung aus, löscht aber weder Datei noch Fortschritt." : "This list shows the first 80 questions. Archiving hides a question from practice and exams but keeps file data and progress."}</p>
      <div class="source-list">${sampleRows}</div>
    </section>
    <div class="section-heading"><div><p class="eyebrow">Version 1</p><h3>${state.language === "de" ? "Fragenformat" : "Question format"}</h3></div></div>
    <section class="panel">
      <p>${state.language === "de" ? "Gültige Themen-IDs" : "Valid topic IDs"}: ${state.data.topics.map((topic) => `<code>${escapeHtml(topic.id)}</code>`).join(" ")}</p>
      <pre>${escapeHtml(schemaExample)}</pre>
      <p>${state.language === "de" ? "Die vollständige Spezifikation und ein kopierbares Beispiel stehen zusätzlich in" : "The full specification and a copyable example are available in"} <code>QUESTION_FORMAT.md</code> ${state.language === "de" ? "und" : "and"} <code>examples/questions.example.json</code>.</p>
    </section>
  `;
  content.querySelector("#question-file").addEventListener("change", (event) => {
    if (event.target.files[0]) importQuestionFile(event.target.files[0]);
  });
  const dropZone = content.querySelector("#drop-zone");
  ["dragenter", "dragover"].forEach((name) =>
    dropZone.addEventListener(name, (event) => {
      event.preventDefault();
      dropZone.classList.add("dragging");
    }),
  );
  ["dragleave", "drop"].forEach((name) =>
    dropZone.addEventListener(name, (event) => {
      event.preventDefault();
      dropZone.classList.remove("dragging");
    }),
  );
  dropZone.addEventListener("drop", (event) => {
    if (event.dataTransfer.files[0]) importQuestionFile(event.dataTransfer.files[0]);
  });
  content.querySelector("#reload-content").addEventListener("click", async () => {
    await loadContent();
    showToast(state.language === "de" ? "Fragenordner wurde neu eingelesen." : "Question folder was reloaded.");
    renderLibrary();
  });
  content.querySelector("#archive-imports").addEventListener("click", async () => {
    state.data.questions
      .filter((question) => question._sourceFile === "Database import")
      .forEach((question) =>
        setQuestionStatus(question.id, "archived", false),
      );
    await saveState();
    showToast(state.language === "de" ? "Datenbank-Importe wurden archiviert." : "Database imports were archived.");
    renderLibrary();
  });
  content.querySelectorAll("[data-question-status]").forEach((button) => {
    button.addEventListener("click", () => {
      setQuestionStatus(button.dataset.questionId, button.dataset.questionStatus);
      showToast(state.language === "de" ? "Fragenstatus aktualisiert." : "Question status updated.");
      renderLibrary();
    });
  });
}

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => navigate(button.dataset.view));
});
document.querySelector("#mobile-menu").addEventListener("click", () => {
  sidebar.classList.toggle("open");
});
document.querySelectorAll("[data-language]").forEach((button) => {
  button.addEventListener("click", () => {
    if (button.dataset.language === state.language) return;
    state.language = button.dataset.language;
    state.practice.queue = [];
    state.practice.index = 0;
    state.practice.feedback = null;
    state.practice.selected = [];
    state.exam = null;
    saveState();
    render();
  });
});
document.querySelector("#reset-progress").addEventListener("click", () => {
  if (
    window.confirm(
      state.language === "de"
        ? "Gesamten Lernfortschritt und alle Wiederholungsintervalle löschen?"
        : "Delete all learning progress and review intervals?",
    )
  ) {
    state.progress = {};
    saveState();
    showToast(state.language === "de" ? "Fortschritt wurde zurückgesetzt." : "Progress was reset.");
    render();
  }
});

try {
  await loadState();
  updateStaticLanguage();
  await loadContent();
  render();
} catch (error) {
  content.innerHTML = `
    <div class="empty-state">
      <h2>Inhalte konnten nicht geladen werden</h2>
      <p>Starte die App im Projektordner mit <code>uv --cache-dir /tmp/adbs-uv-cache run python server.py</code> und öffne danach <code>http://127.0.0.1:8000</code>.</p>
      <p>${escapeHtml(error.message)}</p>
    </div>
  `;
}
