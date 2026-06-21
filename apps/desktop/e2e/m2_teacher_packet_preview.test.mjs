import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { startStaticServer } from "../scripts/static-server.mjs";
import { startMockApi } from "./mockApi.mjs";

const chromePath = process.env.CHROME_BIN || "/usr/bin/google-chrome";

test("M2 teacher packet preview can save credential, preview packet, and approve", async () => {
  const staticPort = 5184;
  const apiPort = 8910;
  const cdpPort = 9234;
  const staticServer = await startStaticServer({ rootDir: "apps/desktop", port: staticPort });
  const mockApi = await startMockApi({ port: apiPort });
  const userDataDir = mkdtempSync(join(tmpdir(), "mib-chrome-"));
  const chrome = spawn(chromePath, [
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    `--remote-debugging-port=${cdpPort}`,
    `--user-data-dir=${userDataDir}`,
    "about:blank",
  ]);
  let client;

  try {
    client = await openPage(`http://127.0.0.1:${staticPort}/projects`, cdpPort, apiPort);
    await waitFor(client, 'document.body.innerText.includes("No projects yet")');
    await click(client, '[data-nav="/settings"]');
    await waitFor(client, 'document.body.innerText.includes("Teacher provider")');
    await click(client, '[data-nav="/settings/teacher"]');
    await waitFor(client, 'document.body.innerText.includes("BYO OpenAI-compatible key")');
    await setValue(client, '[data-field="credential-api-key"]', "fake-key");
    await click(client, '[data-action="save-credential"]');
    await waitFor(client, 'document.body.innerText.includes("Credential connected") || document.body.innerText.includes("Teacher credential saved")');

    await navigate(client, `http://127.0.0.1:${staticPort}/projects/new`);
    await waitFor(client, 'document.body.innerText.includes("Create route contract project")');
    await click(client, '[data-action="create-project"]');
    await waitFor(client, 'document.body.innerText.includes("Project dashboard") || document.body.innerText.includes("support-router")');
    await navigate(client, `http://127.0.0.1:${staticPort}/projects/proj_1/datasets/new`);
    await waitFor(client, 'document.body.innerText.includes("20/20 valid")');
    await click(client, '[data-action="build-dataset"]');
    await waitFor(client, 'document.body.innerText.includes("Dataset build result")');
    await click(client, '[data-action="approve-dataset"]');
    await waitFor(client, 'document.body.innerText.includes("20/20") || document.body.innerText.includes("Dataset approved")');
    await click(client, '[data-action="preview-teacher-packet"]');
    await waitFor(client, 'document.body.innerText.includes("Teacher Packet Preview created") && document.body.innerText.includes("Not sent")');
    await click(client, '[data-action="approve-teacher-packet"]');
    await waitFor(client, 'document.body.innerText.includes("Teacher Packet approved")');

    const text = await evaluate(client, "document.body.innerText");
    assert.match(text, /raw CSV/);
    assert.match(text, /personal identifiers/);
    assert.doesNotMatch(text, /fake-key/);
  } finally {
    client?.close();
    chrome.kill("SIGTERM");
    await waitForProcessExit(chrome);
    staticServer.close();
    mockApi.server.close();
    rmSync(userDataDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
  }
});

async function openPage(url, port, apiPort) {
  await waitForHttp(`http://127.0.0.1:${port}/json/version`);
  const target = await fetch(`http://127.0.0.1:${port}/json/new?about%3Ablank`, { method: "PUT" }).then((response) => response.json());
  const client = await connectCdp(target.webSocketDebuggerUrl);
  await client.send("Page.addScriptToEvaluateOnNewDocument", {
    source: `window.MIB_BOOTSTRAP = { baseUrl: "http://127.0.0.1:${apiPort}", token: "test-token" };`,
  });
  await client.send("Page.navigate", { url });
  return client;
}

function connectCdp(wsUrl) {
  const socket = new WebSocket(wsUrl);
  let id = 0;
  const pending = new Map();
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      message.error ? reject(new Error(message.error.message)) : resolve(message.result);
    }
  });
  return new Promise((resolve) => {
    socket.addEventListener("open", () => {
      resolve({
        send(method, params = {}) {
          const callId = ++id;
          socket.send(JSON.stringify({ id: callId, method, params }));
          return new Promise((resolveCall, rejectCall) => pending.set(callId, { resolve: resolveCall, reject: rejectCall }));
        },
        close() {
          socket.close();
        },
      });
    });
  });
}

async function click(client, selector) {
  await evaluate(client, `document.querySelector(${JSON.stringify(selector)}).click()`);
}

async function setValue(client, selector, value) {
  await evaluate(
    client,
    `{
      const input = document.querySelector(${JSON.stringify(selector)});
      input.value = ${JSON.stringify(value)};
      input.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: ${JSON.stringify(value)} }));
    }`,
  );
}

async function navigate(client, url) {
  await client.send("Page.navigate", { url });
}

async function waitFor(client, expression, timeoutMs = 5000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await evaluate(client, expression)) return;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  const text = await evaluate(client, "document.body.innerText");
  throw new Error(`Timed out waiting for ${expression}\n${text}`);
}

async function evaluate(client, expression) {
  const result = await client.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  return result.result.value;
}

async function waitForHttp(url, timeoutMs = 5000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
  throw new Error(`Timed out waiting for ${url}`);
}

function waitForProcessExit(child) {
  if (child.exitCode !== null || child.signalCode) return Promise.resolve();
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, 1000);
    child.once("exit", () => {
      clearTimeout(timer);
      resolve();
    });
  });
}
