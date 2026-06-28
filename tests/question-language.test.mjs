import test from "node:test";
import assert from "node:assert/strict";

import {
  questionSupportsLanguage,
  supportedQuestionLanguages,
} from "../assets/js/question-language.js";


function bilingualQuestion() {
  return {
    prompt: { de: "Frage?", en: "Question?" },
    explanation: { de: "Erklärung", en: "Explanation" },
    options: [
      {
        text: { de: "Ja", en: "Yes" },
        explanation: { de: "Richtig", en: "Correct" },
      },
      {
        text: { de: "Nein", en: "No" },
        explanation: { de: "Falsch", en: "Incorrect" },
      },
    ],
  };
}


test("a complete question supports German and English", () => {
  const question = bilingualQuestion();

  assert.equal(questionSupportsLanguage(question, "de"), true);
  assert.equal(questionSupportsLanguage(question, "en"), true);
  assert.deepEqual(supportedQuestionLanguages(question), ["de", "en"]);
});


test("language metadata cannot hide a missing option translation", () => {
  const question = bilingualQuestion();
  question.languages = ["de", "en"];
  delete question.options[1].explanation.en;

  assert.equal(questionSupportsLanguage(question, "de"), true);
  assert.equal(questionSupportsLanguage(question, "en"), false);
  assert.deepEqual(supportedQuestionLanguages(question), ["de"]);
});


test("legacy string fields are German-only", () => {
  const question = {
    prompt: "Frage?",
    explanation: "Erklärung",
    options: [
      { text: "Ja", explanation: "Richtig" },
      { text: "Nein", explanation: "Falsch" },
    ],
  };

  assert.equal(questionSupportsLanguage(question, "de"), true);
  assert.equal(questionSupportsLanguage(question, "en"), false);
});
