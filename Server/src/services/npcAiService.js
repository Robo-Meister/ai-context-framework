const fs = require('fs');
const path = require('path');

const npcPath = path.join(__dirname, '../../data/npcs.json');
let npcData = {};

function loadNpcData() {
  try {
    const raw = fs.readFileSync(npcPath, 'utf-8');
    npcData = JSON.parse(raw);
  } catch (err) {
    npcData = {};
  }
}

loadNpcData();

function getPersonality(id) {
  return (npcData[id] && npcData[id].personality) || null;
}

async function sendRequest(npcId, context) {
  const personality = getPersonality(npcId);
  const payload = { npcId, context, personality };
  // Here we'd normally forward payload to the Python service via HTTP
  return payload;
}

module.exports = { sendRequest, loadNpcData };
