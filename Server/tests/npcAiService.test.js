const http = require('http');

function loadService() {
  delete require.cache[require.resolve('../src/services/npcAiService')];
  return require('../src/services/npcAiService');
}

describe('npcAiService.sendRequest', () => {
  test('returns payload when endpoint is unset', async () => {
    delete process.env.CAI_ENGINE_ENDPOINT;
    const { sendRequest } = loadService();
    const payload = await sendRequest('npc1', { msg: 'hi' });
    expect(payload).toEqual({ npcId: 'npc1', context: { msg: 'hi' }, personality: 'aggressive' });
  });
});
