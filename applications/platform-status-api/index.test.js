
const { test } = require('node:test');
const assert = require('node:assert/strict');
const app = require('./index');

async function request(path) {
  const server = app.listen(0);

  try {
    await new Promise(resolve => server.once('listening', resolve));

    const address = server.address();
    return await fetch(`http://127.0.0.1:${address.port}${path}`);
  } finally {
    server.close();
  }
}

test('GET /api/status geeft HTTP 200 en healthy terug', async () => {
  const response = await request('/api/status');

  assert.equal(response.status, 200);

  const body = await response.json();
  assert.equal(body.status, 'healthy');
});

test('GET /api/onbekend geeft HTTP 404 terug', async () => {
  const response = await request('/api/onbekend');

  assert.equal(response.status, 404);
});

