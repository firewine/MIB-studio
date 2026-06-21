import { startStaticServer } from "./static-server.mjs";

const server = await startStaticServer({ rootDir: "apps/desktop", port: Number(process.env.PORT || 5173) });
const address = server.address();
const port = typeof address === "object" && address ? address.port : 5173;
console.log(`MIB desktop shell dev server http://127.0.0.1:${port}`);

