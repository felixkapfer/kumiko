import test from "node:test";
import assert from "node:assert/strict";

import {
  applyExamDefaults,
  clampInteger,
  dueLabel,
  examSetupValues,
  examSplitGroups,
  examSplitSummary,
  formatPoints,
  fullCreditLabel,
  scoringConfig,
  scoringNote,
  scoringShortLabel,
  signedSelectionScoring,
} from "../assets/js/core/exam-config.js";

// ADBS: no examConfig at all, scoring falls back to exact-match.
const ADBS = { questions: new Array(140) };

// AIR: signed-selection, official 100 questions / 120 min, 50/50 paper split.
const AIR = {
  questions: new Array(130),
  scoring: {
    type: "signed-selection",
    labels: { de: { short: "Signierte Auswahl" }, en: { short: "Signed selection" } },
  },
  examConfig: {
    official: { questionCount: 100, durationMinutes: 120 },
    defaults: { questionCount: 40, durationMinutes: 60 },
    split: [
      { label: { de: "Paper", en: "Paper" }, ratio: 0.5, officialCount: 50, topicIds: ["paper-llm-judges"] },
      { label: { de: "Vorlesung", en: "Lecture" }, ratio: 0.5, officialCount: 50, excludeTopicIds: ["paper-llm-judges"] },
    ],
  },
};

test("a course without a scoring block defaults to exact-match", () => {
  assert.deepEqual(scoringConfig(ADBS), { type: "exact-match" });
  assert.equal(signedSelectionScoring(ADBS), false);
  assert.equal(signedSelectionScoring(AIR), true);
  assert.deepEqual(scoringConfig(undefined), { type: "exact-match" });
});

test("clampInteger keeps values inside the range and survives junk input", () => {
  assert.equal(clampInteger("30", 20, 1, 100), 30);
  assert.equal(clampInteger("500", 20, 1, 100), 100);
  assert.equal(clampInteger("0", 20, 1, 100), 1);
  assert.equal(clampInteger("abc", 20, 1, 100), 20);
  assert.equal(clampInteger(undefined, 20, 1, 100), 20);
  // The fallback is clamped too, never returned raw.
  assert.equal(clampInteger("abc", 999, 1, 100), 100);
});

test("official counts apply only when the requested count matches the official one", () => {
  const official = examSplitGroups(AIR, 100);
  assert.deepEqual(official.map((g) => g.count), [50, 50]);

  const custom = examSplitGroups(AIR, 40);
  assert.deepEqual(custom.map((g) => g.count), [undefined, undefined]);
  assert.deepEqual(custom.map((g) => g.ratio), [0.5, 0.5]);
});

test("a course without a split produces no groups", () => {
  assert.deepEqual(examSplitGroups(ADBS, 20), []);
  assert.equal(examSplitSummary(ADBS, "de"), "");
});

test("the split summary is localized and shows official counts", () => {
  assert.equal(examSplitSummary(AIR, "en"), "Paper: 50% / 50 · Lecture: 50% / 50");
  assert.equal(examSplitSummary(AIR, "de"), "Paper: 50% / 50 · Vorlesung: 50% / 50");
});

test("exam setup values clamp against the questions actually available", () => {
  const setup = { count: "20", duration: "40" };
  const values = examSetupValues(ADBS, setup, 71);
  assert.equal(values.available, 71);
  assert.equal(values.count, 20);
  assert.equal(values.duration, 40);

  // Asking for more questions than exist clamps down to what is available.
  assert.equal(examSetupValues(ADBS, { count: "500", duration: "40" }, 71).count, 71);
  // Duration is capped at 240 minutes.
  assert.equal(examSetupValues(ADBS, { count: "20", duration: "9999" }, 71).duration, 240);
  // With no questions available the count floor is still 1, never 0.
  assert.equal(examSetupValues(ADBS, { count: "20", duration: "40" }, 0).count, 1);
});

test("course defaults seed the exam setup and never exceed the question pool", () => {
  const setup = { count: "20", duration: "40" };
  applyExamDefaults(setup, AIR);
  assert.deepEqual(setup, { count: "40", duration: "60" });

  // A default larger than the pool is capped at the pool size.
  const small = { count: "20", duration: "40" };
  applyExamDefaults(small, { questions: new Array(12), examConfig: { defaults: { questionCount: 40 } } });
  assert.equal(small.count, "12");

  // A course without defaults leaves the setup untouched.
  const untouched = { count: "20", duration: "40" };
  applyExamDefaults(untouched, ADBS);
  assert.deepEqual(untouched, { count: "20", duration: "40" });
});

test("points are signed only under signed-selection scoring", () => {
  assert.equal(formatPoints(3, AIR), "+3");
  assert.equal(formatPoints(-2, AIR), "-2");
  assert.equal(formatPoints(0, AIR), "0");
  assert.equal(formatPoints(3, ADBS), "3");
  assert.equal(formatPoints(-2, ADBS), "-2");
});

test("scoring labels come from the course when present, otherwise from defaults", () => {
  assert.equal(scoringShortLabel(AIR, "en"), "Signed selection");
  assert.equal(scoringShortLabel(ADBS, "de"), "Alles-oder-nichts-Wertung");
  assert.equal(scoringShortLabel(ADBS, "en"), "All-or-nothing scoring");
  // AIR defines no note, so it falls back to the generic one.
  assert.match(scoringNote(AIR, "en"), /^Select exactly all correct statements/);
  assert.match(scoringNote(ADBS, "de"), /^Markiere exakt alle richtigen Aussagen/);
});

test("full credit wording differs per scoring model", () => {
  assert.equal(fullCreditLabel(AIR, "de"), "maximal");
  assert.equal(fullCreditLabel(AIR, "en"), "maximum");
  assert.equal(fullCreditLabel(ADBS, "de"), "exakt richtig");
  assert.equal(fullCreditLabel(ADBS, "en"), "exactly correct");
});

test("English due labels bucket by minutes, hours, then days", () => {
  const now = Date.now();
  assert.equal(dueLabel(now - 1000, "en"), "now");
  assert.equal(dueLabel(null, "en"), "now");
  assert.equal(dueLabel(now + 30 * 60000, "en"), "in 30 min");
  assert.equal(dueLabel(now + 5 * 3600000, "en"), "in 5 h");
  assert.equal(dueLabel(now + 5 * 86400000, "en"), "in 5 days");
});
