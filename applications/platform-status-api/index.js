
const express = require('express');

const app = express();
const port = 3000;

app.get('/api/status', (req, res) => {
  res.json({
    application: 'Platform Status API',
    version: '1.0.0',
    status: 'healthy'
  });
});

// Start de server alleen wanneer we index.js direct uitvoeren.
if (require.main === module) {
  app.listen(port, () => {
    console.log(`Platform Status API draait op poort ${port}`);
  });
}

// Hiermee kunnen onze tests de Express-app gebruiken.
module.exports = app;

