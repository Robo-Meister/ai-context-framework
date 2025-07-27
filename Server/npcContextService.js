const historyMap = new Map();

function addEntry(npcId, entry) {
  if (!npcId) return; // ignore invalid ids
  if (!historyMap.has(npcId)) {
    historyMap.set(npcId, []);
  }
  historyMap.get(npcId).push(entry);
}

function getRecentHistory(npcId, limit = 10) {
  const history = historyMap.get(npcId) || [];
  return history.slice(-limit);
}

function clearHistory() {
  historyMap.clear();
}

module.exports = { addEntry, getRecentHistory, clearHistory };
