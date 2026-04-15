import { chromium } from 'playwright';
import { createServer } from 'http';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const siteDir = resolve(process.argv[2] || 'article/_site');
const file = process.argv[3] || 'v3_report.html';

const server = createServer((req, res) => {
  let path = req.url === '/' ? `/${file}` : req.url;
  try {
    const content = readFileSync(resolve(siteDir, '.' + path));
    const ext = path.split('.').pop();
    const types = { html: 'text/html', js: 'application/javascript', css: 'text/css', json: 'application/json', woff2: 'font/woff2', woff: 'font/woff', png: 'image/png', svg: 'image/svg+xml' };
    res.writeHead(200, { 'Content-Type': types[ext] || 'application/octet-stream' });
    res.end(content);
  } catch {
    console.log(`404: ${req.url}`);
    res.writeHead(404);
    res.end('Not found');
  }
});

server.listen(0, async () => {
  const port = server.address().port;
  const url = `http://localhost:${port}/${file}`;
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const errors = [];
  const warnings = [];

  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
    if (msg.type() === 'warning') warnings.push(msg.text());
  });
  page.on('pageerror', err => errors.push(`PAGE ERROR: ${err.message}`));

  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(5000);
  } catch (e) {
    errors.push(`Navigation error: ${e.message}`);
  }

  console.log(`\n--- ERRORS (${errors.length}) ---`);
  errors.forEach(e => console.log(e));
  console.log(`\n--- WARNINGS (${warnings.length}) ---`);
  warnings.forEach(w => console.log(w));
  if (errors.length === 0 && warnings.length === 0) console.log('\nAll clean.');

  await browser.close();
  server.close();
});
