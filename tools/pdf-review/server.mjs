// Development/test server. End users open the built HTML directly.
import http from 'node:http';
import { readFile } from 'node:fs/promises';
const page = new URL('../../downloads/pdf-review.html', import.meta.url);
const port = Number(process.env.PDF_REVIEW_PORT || 4178);
const server = http.createServer(async (request, response) => {
  if (request.url !== '/' && request.url !== '/pdf-review.html') {
    response.writeHead(404).end();
    return;
  }
  try {
    const html = await readFile(page);
    response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' });
    response.end(html);
  } catch {
    response.writeHead(503).end('Build the review page first.');
  }
});
server.listen(port, '127.0.0.1', () => console.log(`PDF review: http://127.0.0.1:${server.address().port}`));
