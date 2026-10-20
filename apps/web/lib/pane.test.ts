import assert from "node:assert/strict";
import { test } from "node:test";

import { clampPaneWidth, paneLimits, parseStoredWidth, stepPaneWidth } from "./pane.ts";

test("the panel never takes so much that the list gets under 360 px", () => {
  assert.deepEqual(paneLimits(1000), { min: 360, max: 640 });
});

test("on a wide screen the panel stops at 720 px", () => {
  assert.deepEqual(paneLimits(1800), { min: 360, max: 720 });
});

test("on a narrow screen the minimum wins", () => {
  assert.deepEqual(paneLimits(700), { min: 360, max: 360 });
});

test("a width is kept within the limits and in whole pixels", () => {
  const limits = paneLimits(1300);
  assert.equal(clampPaneWidth(200, limits), 360);
  assert.equal(clampPaneWidth(500.6, limits), 501);
  assert.equal(clampPaneWidth(2000, limits), 720);
});

test("the arrows move the edge, and the panel is on the right", () => {
  const limits = paneLimits(1300);
  assert.equal(stepPaneWidth(500, "ArrowLeft", false, limits), 516);
  assert.equal(stepPaneWidth(500, "ArrowRight", false, limits), 484);
  assert.equal(stepPaneWidth(500, "ArrowLeft", true, limits), 564);
  assert.equal(stepPaneWidth(500, "ArrowRight", true, limits), 436);
  assert.equal(stepPaneWidth(710, "ArrowLeft", true, limits), 720);
  assert.equal(stepPaneWidth(370, "ArrowRight", true, limits), 360);
});

test("Home and End go to the limits; other keys do nothing", () => {
  const limits = paneLimits(1300);
  assert.equal(stepPaneWidth(500, "Home", false, limits), 360);
  assert.equal(stepPaneWidth(500, "End", false, limits), 720);
  assert.equal(stepPaneWidth(500, "a", false, limits), undefined);
  assert.equal(stepPaneWidth(500, "ArrowUp", false, limits), undefined);
});

test("only a sensible stored width is used", () => {
  assert.equal(parseStoredWidth("480"), 480);
  assert.equal(parseStoredWidth(null), null);
  assert.equal(parseStoredWidth(""), null);
  assert.equal(parseStoredWidth("ancho"), null);
  assert.equal(parseStoredWidth("480.5"), null);
  assert.equal(parseStoredWidth("100"), null);
  assert.equal(parseStoredWidth("5000"), null);
});
