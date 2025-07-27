const { spawn } = require('child_process');
const http = require('http');
const https = require('https');
const { URL } = require('url');

const endpoint = process.env.CAI_ENGINE_ENDPOINT;

function httpRequest(url, data) {
  const opts = new URL(url);
  const lib = opts.protocol === 'https:' ? https : http;
  const options = {
    hostname: opts.hostname,
    port: opts.port,
    path: opts.pathname + opts.search,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  };
  return new Promise((resolve, reject) => {
    const req = lib.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => (body += chunk));
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try {
            resolve(JSON.parse(body));
          } catch (e) {
            reject(e);
          }
        } else {
          reject(new Error('Request failed: ' + res.statusCode));
        }
      });
    });
    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}

async function suggest(history, actions, goalState) {
  if (endpoint) {
    const payload = JSON.stringify({
      history: history || [],
      current_actions: actions || [],
      goal_state: goalState,
    });
    return httpRequest(new URL('/suggest', endpoint).toString(), payload);
  }

  return new Promise((resolve, reject) => {
    const proc = spawn('python3', ['cai_bridge.py']);
    let out = '';
    proc.stdout.on('data', (d) => (out += d));
    proc.stderr.on('data', (d) => console.error(d.toString()));
    proc.on('close', (code) => {
      if (code !== 0) return reject(new Error('cai_bridge.py failed'));
      try {
        resolve(JSON.parse(out));
      } catch (e) {
        reject(e);
      }
    });
    proc.stdin.write(
      JSON.stringify({
        history: history || [],
        current_actions: actions || [],
        goal_state: goalState,
      })
    );
    proc.stdin.end();
  });
}

module.exports = { suggest };
