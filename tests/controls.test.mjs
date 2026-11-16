import test from 'node:test';
import assert from 'node:assert/strict';
import {steppedValue} from '../frontend/controls.js';

test('numeric buttons clamp at limits and support ten steps', () => {
  assert.equal(steppedValue(99, 1, 1, 0, 100, true), 100);
  assert.equal(steppedValue(2, 1, -1, 0, 100, true), 0);
  assert.equal(steppedValue(40, 1, 1, 0, 100, true), 50);
});
test('decimal controls avoid floating point drift; any uses one step', () => {
  assert.equal(steppedValue(0.2, 0.1, 1), 0.3);
  assert.equal(steppedValue(82.25, 'any', 1), 83.25);
});
