import assert from "node:assert/strict";
import { test } from "node:test";

import { parseDraft, serializeDraft } from "./onboarding-draft.ts";

const OWNER = "8a1f4c2e-0000-4000-8000-000000000001";
const draft = { property: { name: "Casa La Soledad" }, units: [{ name: "Apto 1" }] };

test("a saved draft comes back as it was, for the same owner", () => {
  assert.deepEqual(parseDraft(serializeDraft(draft, OWNER), OWNER), draft);
});

test("another owner on the same device does not get it", () => {
  const other = "8a1f4c2e-0000-4000-8000-000000000002";
  assert.equal(parseDraft(serializeDraft(draft, OWNER), other), null);
});

test("nothing saved, or something unreadable, is no draft", () => {
  assert.equal(parseDraft(null, OWNER), null);
  assert.equal(parseDraft("", OWNER), null);
  assert.equal(parseDraft("{no es json", OWNER), null);
  assert.equal(parseDraft("42", OWNER), null);
  assert.equal(parseDraft(JSON.stringify({ owner: OWNER }), OWNER), null);
});

test("a draft saved in another shape is dropped", () => {
  const old = JSON.stringify({ version: 0, owner: OWNER, draft });
  assert.equal(parseDraft(old, OWNER), null);
});
