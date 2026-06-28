import test from "node:test";
import assert from "node:assert/strict";

import {
  buildExam,
  buildSplitExam,
  exactMatch,
  questionStatus,
  scoreExam,
  scoreQuestion,
  selectQuestions,
  updateProgress,
} from "../engine.mjs";

const options = [
  { id: "a", correct: true },
  { id: "b", correct: false },
  { id: "c", correct: true },
];

test("exactMatch enforces all-or-nothing scoring", () => {
  assert.equal(exactMatch(["a", "c"], options), true);
  assert.equal(exactMatch(["a"], options), false);
  assert.equal(exactMatch(["a", "b", "c"], options), false);
  assert.equal(exactMatch([], options), false);
});

test("exactMatch supports a question with zero correct options", () => {
  const noneCorrect = [
    { id: "a", correct: false },
    { id: "b", correct: false },
  ];
  assert.equal(exactMatch([], noneCorrect), true);
  assert.equal(exactMatch(["a"], noneCorrect), false);
});

test("progress advances on correct answers and falls back on errors", () => {
  const now = 1_000_000;
  const first = updateProgress({}, true, now);
  assert.equal(first.box, 1);
  assert.equal(first.streak, 1);
  assert.ok(first.dueAt > now);

  const second = updateProgress(first, true, now + 10);
  assert.equal(second.box, 2);
  assert.equal(second.streak, 2);

  const failed = updateProgress(second, false, now + 20);
  assert.equal(failed.box, 0);
  assert.equal(failed.streak, 0);
  assert.equal(failed.wrong, 1);
});

test("question filters include due and last-wrong questions", () => {
  const questions = [
    { id: "new", topic: "a", difficulty: 1 },
    { id: "due", topic: "a", difficulty: 2 },
    { id: "wrong", topic: "b", difficulty: 3 },
  ];
  const progress = {
    due: { attempts: 1, dueAt: 50, lastResult: true, box: 1 },
    wrong: { attempts: 1, dueAt: 999999, lastResult: false, box: 0 },
  };
  const result = selectQuestions(
    questions,
    progress,
    { topics: [], difficulties: [], status: "due" },
    100,
  );
  assert.deepEqual(
    result.map((question) => question.id).sort(),
    ["due", "wrong"],
  );
  assert.equal(questionStatus(progress.wrong, 100), "wrong");
});

test("exam generation respects requested maximum and spreads topics", () => {
  const questions = Array.from({ length: 15 }, (_, index) => ({
    id: `q${index}`,
    topic: `t${index % 3}`,
    difficulty: (index % 5) + 1,
    options,
  }));
  const exam = buildExam(questions, 9, () => 0.42);
  assert.equal(exam.length, 9);
  assert.equal(new Set(exam.map((question) => question.id)).size, 9);
  assert.equal(new Set(exam.map((question) => question.topic)).size, 3);
});

test("split exam generation respects configured topic groups", () => {
  const questions = [
    ...Array.from({ length: 8 }, (_, index) => ({
      id: `p${index}`,
      topic: "paper",
      difficulty: 3,
      options,
    })),
    ...Array.from({ length: 8 }, (_, index) => ({
      id: `l${index}`,
      topic: index % 2 ? "lecture-a" : "lecture-b",
      difficulty: 3,
      options,
    })),
  ];
  const exam = buildSplitExam(
    questions,
    10,
    [
      { topicIds: ["paper"], ratio: 0.5 },
      { excludeTopicIds: ["paper"], ratio: 0.5 },
    ],
    () => 0.42,
  );

  assert.equal(exam.length, 10);
  assert.equal(exam.filter((question) => question.topic === "paper").length, 5);
  assert.equal(exam.filter((question) => question.topic !== "paper").length, 5);
});

test("scoreExam awards one point only for exact selections", () => {
  const questions = [
    { id: "q1", options },
    { id: "q2", options },
  ];
  const result = scoreExam(questions, {
    q1: ["a", "c"],
    q2: ["a"],
  });
  assert.deepEqual(
    {
      points: result.points,
      maximum: result.maximum,
      percentage: result.percentage,
    },
    { points: 1, maximum: 2, percentage: 50 },
  );
});

test("scoreQuestion supports signed selection scoring", () => {
  const question = { id: "q1", options };
  const result = scoreQuestion(question, ["a", "b"], {
    type: "signed-selection",
    correctSelected: 1,
    incorrectSelected: -1,
  });

  assert.deepEqual(
    {
      points: result.points,
      maximum: result.maximum,
      correct: result.correct,
      selectedCorrect: result.selectedCorrect,
      selectedIncorrect: result.selectedIncorrect,
      missedCorrect: result.missedCorrect,
    },
    {
      points: 0,
      maximum: 2,
      correct: false,
      selectedCorrect: 1,
      selectedIncorrect: 1,
      missedCorrect: 1,
    },
  );
});

test("scoreExam sums signed selection points and maximum", () => {
  const questions = [
    { id: "q1", options },
    { id: "q2", options },
  ];
  const result = scoreExam(
    questions,
    {
      q1: ["a", "c"],
      q2: ["a", "b"],
    },
    {
      type: "signed-selection",
      correctSelected: 1,
      incorrectSelected: -1,
    },
  );

  assert.deepEqual(
    {
      points: result.points,
      maximum: result.maximum,
      percentage: result.percentage,
      correct: result.details.map((entry) => entry.correct),
    },
    { points: 2, maximum: 4, percentage: 50, correct: [true, false] },
  );
});
