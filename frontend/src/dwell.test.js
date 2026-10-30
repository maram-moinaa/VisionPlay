import assert from "node:assert/strict";
import test from "node:test";

import { DwellSelector } from "./dwell.js";

test("selects after the configured 1.5 second dwell", () => {
  const dwell = new DwellSelector(1500);
  assert.equal(dwell.update("a", 1000).selected, false);
  assert.equal(dwell.update("a", 2499).selected, false);
  assert.equal(dwell.update("a", 2500).selected, true);
});

test("leaving or entering another card restarts the timer", () => {
  const dwell = new DwellSelector(1500);
  dwell.update("a", 0);
  dwell.update(null, 800);
  assert.equal(dwell.update("a", 1000).progress, 0);
  dwell.update("b", 1800);
  assert.equal(dwell.update("b", 3299).selected, false);
  assert.equal(dwell.update("b", 3300).selected, true);
});

test("a card only fires once while the cursor stays inside it", () => {
  const dwell = new DwellSelector(1500);
  assert.equal(dwell.update("a", 0).selected, false);
  assert.equal(dwell.update("a", 1500).selected, true);
  assert.equal(dwell.update("a", 2000).selected, false);
  assert.equal(dwell.update("a", 3000).selected, false);
});
