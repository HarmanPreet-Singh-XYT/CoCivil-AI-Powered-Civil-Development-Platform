import test from 'node:test';
import assert from 'node:assert/strict';

import { parseChatCommand } from './chatCommands.js';

test('parseChatCommand identifies upload plan generation commands', () => {
  assert.deepEqual(parseChatCommand('generate plan from upload'), { type: 'plan_from_upload' });
  assert.deepEqual(parseChatCommand('Create a plan from upload'), { type: 'plan_from_upload' });
});

test('parseChatCommand identifies upload response generation commands', () => {
  assert.deepEqual(parseChatCommand('generate response from upload'), { type: 'response_from_upload' });
  assert.deepEqual(parseChatCommand('build a response from upload'), { type: 'response_from_upload' });
});

test('parseChatCommand preserves text for normal plan generation commands', () => {
  assert.deepEqual(parseChatCommand('generate a plan for a six-storey mixed-use building'), {
    type: 'plan',
    query: 'a six-storey mixed-use building',
  });
});

test('parseChatCommand returns none for standard assistant prompts', () => {
  assert.deepEqual(parseChatCommand('what is the zoning here?'), { type: 'none' });
});
