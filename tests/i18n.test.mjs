import test from "node:test";
import assert from "node:assert/strict";

import {
  difficultyLabel,
  glossaryDefinition,
  glossaryTerm,
  isKnownView,
  translate,
  translated,
  viewTitleFor,
} from "../assets/js/core/i18n.js";

const NAV_VIEWS = [
  "dashboard",
  "learn",
  "coding",
  "practice",
  "exam",
  "history",
  "glossary",
  "slides",
  "library",
];

test("isKnownView accepts every view the sidebar can reach", () => {
  for (const view of NAV_VIEWS) {
    assert.equal(isKnownView(view), true, `${view} should be a known view`);
  }
});

test("isKnownView rejects unknown views and prototype keys", () => {
  assert.equal(isKnownView("nope"), false);
  assert.equal(isKnownView(""), false);
  assert.equal(isKnownView(undefined), false);
  assert.equal(isKnownView("constructor"), false);
});

test("translate falls back through language, then German, then the raw key", () => {
  assert.equal(translate("nav.dashboard", "en"), "Dashboard");
  assert.equal(translate("nav.dashboard", "de"), "Überblick");
  assert.equal(translate("nav.dashboard", "fr"), "Überblick");
  assert.equal(translate("does.not.exist", "de"), "does.not.exist");
});

test("translated handles bilingual objects, strings, arrays, and nullish input", () => {
  assert.equal(translated({ de: "Hallo", en: "Hello" }, "en"), "Hello");
  assert.equal(translated({ de: "Hallo" }, "en"), "Hallo");
  assert.equal(translated({ en: "Hello" }, "de"), "Hello");
  assert.equal(translated("plain", "en"), "plain");
  assert.equal(translated(null, "de"), "");
  assert.equal(translated(undefined, "de"), "");
  const list = ["a", "b"];
  assert.strictEqual(translated(list, "de"), list);
});

test("translated keeps an empty string rather than falling through to another language", () => {
  assert.equal(translated({ de: "", en: "Hello" }, "de"), "");
});

test("viewTitleFor lets course navigation override the built-in title", () => {
  const navigation = { coding: { de: "Paper", en: "Paper" } };
  assert.equal(viewTitleFor("coding", "en", navigation), "Paper");
  assert.equal(viewTitleFor("coding", "en"), "Cypher examples");
  assert.equal(viewTitleFor("coding", "de", {}), "Cypher-Beispiele");
});

test("viewTitleFor falls back to German, then to the raw view name", () => {
  assert.equal(viewTitleFor("glossary", "fr"), "Glossar");
  assert.equal(viewTitleFor("unknown-view", "de"), "unknown-view");
});

test("glossary term and definition prefer the English translation only in English", () => {
  const entry = {
    term: "Schlüssel",
    definition: "Ein eindeutiger Bezeichner.",
    translations: { en: { term: "Key", definition: "A unique identifier." } },
  };
  assert.equal(glossaryTerm(entry, "en"), "Key");
  assert.equal(glossaryTerm(entry, "de"), "Schlüssel");
  assert.equal(glossaryDefinition(entry, "en"), "A unique identifier.");
  assert.equal(glossaryDefinition(entry, "de"), "Ein eindeutiger Bezeichner.");
});

test("glossary entries without a translation fall back to the German source", () => {
  const entry = { term: "Sharding", definition: "Horizontale Partitionierung." };
  assert.equal(glossaryTerm(entry, "en"), "Sharding");
  assert.equal(glossaryDefinition(entry, "en"), "Horizontale Partitionierung.");
});

test("difficultyLabel is language specific and falls back for unknown levels", () => {
  assert.equal(difficultyLabel(3, "en"), "Medium");
  assert.notEqual(difficultyLabel(3, "de"), "Medium");
  assert.equal(difficultyLabel(99, "en"), undefined);
});
