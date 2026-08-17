import test from "node:test";
import assert from "node:assert/strict";

import {
  CUSTOM_KEY,
  EXAM_HISTORY_KEY,
  LANGUAGE_KEY,
  MAX_EXAM_HISTORY,
  OVERRIDES_KEY,
  STORAGE_KEY,
  applyStoredState,
  buildStatePayload,
  clearLegacyBrowserState,
  legacyBrowserState,
  normalizeCustomQuestions,
  sanitizeExamHistory,
} from "../assets/js/state/persistence.js";

function fakeStorage(entries = {}) {
  const map = new Map(Object.entries(entries));
  return {
    map,
    getItem: (key) => (map.has(key) ? map.get(key) : null),
    removeItem: (key) => map.delete(key),
  };
}

function examEntry(id, finishedAt) {
  return { id, finishedAt, questions: [], answers: {} };
}

function emptyState() {
  return {
    courseId: "adbs",
    examId: "practical-test-3-2026",
    progress: { q1: {} },
    questionOverrides: { q1: "archived" },
    customQuestions: [],
    language: "en",
    examHistory: [],
  };
}

test("the persisted payload is version 2", () => {
  const payload = buildStatePayload(emptyState());
  assert.equal(payload.version, 2);
  assert.equal(payload.courseId, "adbs");
  assert.equal(payload.examId, "practical-test-3-2026");
});

test("both the payload and the restore path cap history at 25 entries", () => {
  assert.equal(MAX_EXAM_HISTORY, 25);
  const history = Array.from({ length: 26 }, (_, i) => examEntry(`e${i}`, i));

  const state = { ...emptyState(), examHistory: history };
  assert.equal(buildStatePayload(state).examHistory.length, 25);

  const restored = emptyState();
  applyStoredState(restored, { examHistory: history });
  assert.equal(restored.examHistory.length, 25);
});

test("restoring keeps the current course and exam when the payload omits them", () => {
  const state = emptyState();
  applyStoredState(state, {});
  assert.equal(state.courseId, "adbs");
  assert.equal(state.examId, "practical-test-3-2026");
});

test("restoring resets language to German and clears progress when omitted", () => {
  const state = emptyState();
  applyStoredState(state, {});
  assert.equal(state.language, "de");
  assert.deepEqual(state.progress, {});
  assert.deepEqual(state.questionOverrides, {});
  assert.deepEqual(state.examHistory, []);
});

test("history is sorted newest first and incomplete entries are dropped", () => {
  const sanitized = sanitizeExamHistory([
    examEntry("old", 100),
    examEntry("new", 300),
    { id: "no-questions", answers: {}, finishedAt: 400 },
    { id: "not-an-array", questions: "nope", answers: {}, finishedAt: 400 },
    { questions: [], answers: {}, finishedAt: 400 },
    { id: "no-answers", questions: [], finishedAt: 400 },
    { id: "unfinished", questions: [], answers: {} },
    null,
    examEntry("middle", 200),
  ]);
  assert.deepEqual(sanitized.map((entry) => entry.id), ["new", "middle", "old"]);
});

test("history that is not an array becomes an empty list", () => {
  assert.deepEqual(sanitizeExamHistory(undefined), []);
  assert.deepEqual(sanitizeExamHistory(null), []);
  assert.deepEqual(sanitizeExamHistory({}), []);
});

test("custom questions get a status, a source label, and language metadata", () => {
  const [normalized] = normalizeCustomQuestions([
    { id: "q1", question: "Was ist NoSQL?", options: [] },
  ]);
  assert.equal(normalized._status, "active");
  assert.equal(normalized.status, "active");
  assert.equal(normalized._sourceFile, "Database import");
  assert.ok(Array.isArray(normalized._languages));
});

test("an explicit status wins over the internal one, and the source label is kept", () => {
  const [normalized] = normalizeCustomQuestions([
    { id: "q1", status: "archived", _status: "active", _sourceFile: "import.json" },
  ]);
  assert.equal(normalized._status, "archived");
  assert.equal(normalized._sourceFile, "import.json");
});

test("normalizing an absent list yields an empty list", () => {
  assert.deepEqual(normalizeCustomQuestions(), []);
});

test("legacy browser state survives malformed JSON in every key", () => {
  const storage = fakeStorage({
    [STORAGE_KEY]: "{not json",
    [OVERRIDES_KEY]: "{not json",
    [EXAM_HISTORY_KEY]: "[not json",
    [CUSTOM_KEY]: "[not json",
  });
  const legacy = legacyBrowserState(storage);
  assert.deepEqual(legacy.progress, {});
  assert.deepEqual(legacy.questionOverrides, {});
  assert.deepEqual(legacy.examHistory, []);
  assert.deepEqual(legacy.customQuestions, []);
  assert.equal(legacy.language, "de");
});

test("a literal null in the state key does not throw", () => {
  const legacy = legacyBrowserState(fakeStorage({ [STORAGE_KEY]: "null" }));
  assert.deepEqual(legacy.progress, {});
});

test("an empty browser has no legacy data", () => {
  const legacy = legacyBrowserState(fakeStorage());
  assert.equal(legacy.hasData, false);
  assert.equal(legacy.language, "de");
});

test("a stored language alone is enough to count as legacy data", () => {
  const legacy = legacyBrowserState(fakeStorage({ [LANGUAGE_KEY]: "en" }));
  assert.equal(legacy.hasData, true);
  assert.equal(legacy.language, "en");
});

test("legacy progress is read from the nested progress field", () => {
  const storage = fakeStorage({
    [STORAGE_KEY]: JSON.stringify({ progress: { q1: { correct: 2 } } }),
  });
  const legacy = legacyBrowserState(storage);
  assert.deepEqual(legacy.progress, { q1: { correct: 2 } });
  assert.equal(legacy.hasData, true);
});

test("clearing legacy state removes exactly the five browser keys", () => {
  const storage = fakeStorage({
    [STORAGE_KEY]: "{}",
    [CUSTOM_KEY]: "[]",
    [OVERRIDES_KEY]: "{}",
    [LANGUAGE_KEY]: "de",
    [EXAM_HISTORY_KEY]: "[]",
    "unrelated-key": "keep me",
  });
  clearLegacyBrowserState(storage);
  assert.deepEqual([...storage.map.keys()], ["unrelated-key"]);
});
