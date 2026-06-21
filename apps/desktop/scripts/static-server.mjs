import { createServer } from "node:http";
import { createReadStream, existsSync, statSync } from "node:fs";
import { extname, join, normalize, resolve } from "node:path";

const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
};

export function startStaticServer({ rootDir, port = 5173 }) {
  const root = resolve(rootDir);
  const server = createServer((request, response) => {
    const url = new URL(request.url || "/", `http://${request.headers.host || "127.0.0.1"}`);
    const filePath = resolvePath(root, url.pathname);
    response.setHeader("Access-Control-Allow-Origin", "*");
    if (!filePath) {
      response.writeHead(404);
      response.end("not found");
      return;
    }
    response.writeHead(200, { "content-type": mimeTypes[extname(filePath)] || "application/octet-stream" });
    createReadStream(filePath).pipe(response);
  });
  return new Promise((resolveServer) => {
    server.listen(port, "127.0.0.1", () => resolveServer(server));
  });
}

function resolvePath(root, pathname) {
  const normalized = normalize(decodeURIComponent(pathname)).replace(/^(\.\.[/\\])+/, "");
  const candidate = join(root, normalized === "/" ? "index.html" : normalized);
  if (candidate.startsWith(root) && existsSync(candidate) && statSync(candidate).isFile()) return candidate;
  const fallback = join(root, "index.html");
  return existsSync(fallback) ? fallback : null;
}
