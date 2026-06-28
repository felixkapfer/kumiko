import test from "node:test";
import assert from "node:assert/strict";

import { changeLanguage } from "../assets/js/language-state.js";


test("language changes preserve an active exam and all answers", () => {
  const exam = {
    index: 4,
    questions: [{ id: "q1" }, { id: "q2" }],
    answers: { q1: ["a", "c"], q2: ["b"] },
    visited: new Set(["q1", "q2"]),
    optionOrder: { "exam:q1": ["c", "a", "b"] },
    startedAt: 1000,
    endsAt: 9000,
    finished: false,
  };
  const examSetup = { count: "30", duration: "60" };
  const state = { language: "de", exam, examSetup };

  assert.equal(changeLanguage(state, "en"), true);
  assert.equal(state.language, "en");
  assert.strictEqual(state.exam, exam);
  assert.deepEqual(state.exam.answers, {
    q1: ["a", "c"],
    q2: ["b"],
  });
  assert.deepEqual([...state.exam.visited], ["q1", "q2"]);
  assert.equal(state.exam.index, 4);
  assert.equal(state.exam.endsAt, 9000);
  assert.strictEqual(state.examSetup, examSetup);
  assert.deepEqual(state.examSetup, { count: "30", duration: "60" });
});


test("language changes preserve the active practice session", () => {
  const practice = {
    queue: ["q1", "q2", "q1"],
    index: 1,
    feedback: { correct: false },
    selected: ["a"],
    optionOrder: { "practice:q2": ["b", "a"] },
    sessionCorrect: 2,
    sessionAnswered: 3,
  };
  const state = { language: "en", practice };

  assert.equal(changeLanguage(state, "de"), true);
  assert.strictEqual(state.practice, practice);
  assert.deepEqual(state.practice.queue, ["q1", "q2", "q1"]);
  assert.deepEqual(state.practice.selected, ["a"]);
  assert.deepEqual(state.practice.feedback, { correct: false });
  assert.equal(state.practice.index, 1);
});


test("selecting the current language is a no-op", () => {
  const state = { language: "de", exam: { index: 2 } };

  assert.equal(changeLanguage(state, "de"), false);
  assert.deepEqual(state, { language: "de", exam: { index: 2 } });
});
