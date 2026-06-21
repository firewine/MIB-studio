import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";

const source = "apps/desktop";
const dist = join(source, "dist");
rmSync(dist, { recursive: true, force: true });
mkdirSync(dist, { recursive: true });
cpSync(join(source, "index.html"), join(dist, "index.html"));
cpSync(join(source, "src"), join(dist, "src"), { recursive: true });

const required = [
  join(dist, "index.html"),
  join(dist, "src/main.mjs"),
  join(dist, "src/lib/appModel.mjs"),
  join(dist, "src/lib/apiClient.mjs"),
  join(dist, "src/styles.css"),
];
const missing = required.filter((path) => !existsSync(path));
if (missing.length) {
  console.error(JSON.stringify({ status: "failed", missing }));
  process.exit(1);
}
console.log(JSON.stringify({ status: "ok", outDir: dist, files: required.length }));
