import { supportedQuestionLanguages } from "../question-language.js";

// These keys are still ADBS-branded because renaming them would orphan the
// progress of anyone who studied before the platform became multi-course.
export const STORAGE_KEY = "adbs-exam-prep-state-v1";
export const CUSTOM_KEY = "adbs-exam-prep-custom-questions-v1";
export const OVERRIDES_KEY = "adbs-exam-prep-question-overrides-v1";
export const LANGUAGE_KEY = "adbs-exam-prep-language-v1";
export const EXAM_HISTORY_KEY = "adbs-exam-prep-exam-history-v1";

export const LEGACY_COURSE_ID = "adbs";
export const LEGACY_EXAM_ID = "practical-test-3-2026";
export const MAX_EXAM_HISTORY = 25;

const LEGACY_KEYS = [
  STORAGE_KEY,
  CUSTOM_KEY,
  OVERRIDES_KEY,
  LANGUAGE_KEY,
  EXAM_HISTORY_KEY,
];

export function sanitizeExamHistory(value) {
  if (!Array.isArray(value)) return [];
  return value
    .filter(
      (entry) =>
        entry &&
        entry.id &&
        Array.isArray(entry.questions) &&
        entry.answers &&
        entry.finishedAt,
    )
    .sort((a, b) => b.finishedAt - a.finishedAt)
    .slice(0, MAX_EXAM_HISTORY);
}

export function buildStatePayload(state) {
  return {
    version: 2,
    courseId: state.courseId,
    examId: state.examId,
    progress: state.progress,
    questionOverrides: state.questionOverrides,
    customQuestions: state.customQuestions,
    language: state.language,
    examHistory: state.examHistory.slice(0, MAX_EXAM_HISTORY),
  };
}

export function normalizeCustomQuestions(questions = []) {
  return questions.map((question) => {
    const status = question.status || question._status || "active";
    return {
      status,
      ...question,
      _status: status,
      _sourceFile: question._sourceFile || "Database import",
      _languages: supportedQuestionLanguages(question),
    };
  });
}

export function applyStoredState(state, stored) {
  state.courseId = stored.courseId || state.courseId;
  state.examId = stored.examId || state.examId;
  state.progress = stored.progress || {};
  state.questionOverrides = stored.questionOverrides || {};
  state.customQuestions = normalizeCustomQuestions(stored.customQuestions);
  state.language = stored.language || "de";
  state.examHistory = sanitizeExamHistory(stored.examHistory);
}

function parseStored(storage, key, fallback) {
  try {
    return JSON.parse(storage.getItem(key) || fallback);
  } catch {
    return JSON.parse(fallback);
  }
}

export function legacyBrowserState(storage = globalThis.localStorage) {
  const stored = parseStored(storage, STORAGE_KEY, "{}");
  const legacy = {
    progress: stored?.progress || {},
    questionOverrides: parseStored(storage, OVERRIDES_KEY, "{}"),
    examHistory: sanitizeExamHistory(parseStored(storage, EXAM_HISTORY_KEY, "[]")),
    customQuestions: parseStored(storage, CUSTOM_KEY, "[]"),
    language: storage.getItem(LANGUAGE_KEY) || "de",
  };
  legacy.hasData = Boolean(
    Object.keys(legacy.progress).length ||
      Object.keys(legacy.questionOverrides).length ||
      legacy.customQuestions.length ||
      legacy.examHistory.length ||
      storage.getItem(LANGUAGE_KEY),
  );
  return legacy;
}

export function clearLegacyBrowserState(storage = globalThis.localStorage) {
  LEGACY_KEYS.forEach((key) => storage.removeItem(key));
}
