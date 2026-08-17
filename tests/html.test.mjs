import test from "node:test";
import assert from "node:assert/strict";

import { escapeHtml } from "../assets/js/core/html.js";

test("all five HTML entities are escaped", () => {
  assert.equal(
    escapeHtml(`<a href="x" title='y'>Tom & Jerry</a>`),
    "&lt;a href=&quot;x&quot; title=&#039;y&#039;&gt;Tom &amp; Jerry&lt;/a&gt;",
  );
});

test("ampersands are escaped before the other entities", () => {
  assert.equal(escapeHtml("&lt;"), "&amp;lt;");
});

test("missing input becomes an empty string", () => {
  assert.equal(escapeHtml(), "");
  assert.equal(escapeHtml(""), "");
});

test("falsy non-string values are stringified, not dropped", () => {
  assert.equal(escapeHtml(0), "0");
  assert.equal(escapeHtml(false), "false");
});
