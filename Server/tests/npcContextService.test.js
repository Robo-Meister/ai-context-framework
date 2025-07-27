const { addEntry, getRecentHistory, clearHistory } = require('../npcContextService');

describe('npcContextService', () => {
  beforeEach(() => {
    clearHistory();
  });

  test('addEntry and getRecentHistory store and retrieve entries', () => {
    addEntry('npc1', { text: 'hello' });
    addEntry('npc1', { text: 'world' });

    const history = getRecentHistory('npc1');
    expect(history).toHaveLength(2);
    expect(history[0]).toEqual({ text: 'hello' });
    expect(history[1]).toEqual({ text: 'world' });
  });

  test('getRecentHistory respects limit', () => {
    addEntry('npc2', 'a');
    addEntry('npc2', 'b');
    addEntry('npc2', 'c');

    const history = getRecentHistory('npc2', 2);
    expect(history).toEqual(['b', 'c']);
  });

  test('getRecentHistory returns empty array when no history', () => {
    const history = getRecentHistory('unknown');
    expect(history).toEqual([]);
  });

  test('entries are kept separate per NPC', () => {
    addEntry('npc1', 1);
    addEntry('npc2', 2);
    const h1 = getRecentHistory('npc1');
    const h2 = getRecentHistory('npc2');
    expect(h1).toEqual([1]);
    expect(h2).toEqual([2]);
  });

  test('addEntry ignores empty npcId', () => {
    addEntry('', 'x');
    expect(getRecentHistory('')).toEqual([]);
  });
});
