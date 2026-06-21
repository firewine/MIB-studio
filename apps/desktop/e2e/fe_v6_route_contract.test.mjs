import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { startStaticServer } from "../scripts/static-server.mjs";
import { startMockApi } from "./mockApi.mjs";

const chromePath = process.env.CHROME_BIN || "/usr/bin/google-chrome";

test("FE v6 route contract builder renders, edits, and passes keyboard/a11y smoke", async () => {
  const staticPort = 5196;
  const apiPort = 8910;
  const cdpPort = 9246;
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
    await click(client, '[data-nav="/projects/new"]');
    await waitFor(client, 'document.body.innerText.includes("Create route contract project")');
    await click(client, '[data-action="create-project"]');
    await waitFor(client, 'document.body.innerText.includes("support-router")');
    await navigate(client, `http://127.0.0.1:${staticPort}/projects/proj_1/define`);
    await waitFor(client, 'document.body.innerText.includes("Toolbox") && document.body.innerText.includes("output schema locked")');

    await click(client, '[data-action="select-palette"][data-palette="route"]');
    await waitFor(client, 'document.body.innerText.includes("route among labels")');
    await click(client, '[data-action="add-preset"][data-preset="finance"]');
    await waitFor(client, 'document.body.innerText.includes("investment_advice_block")');
    await click(client, '[data-action="select-inspector-tab"][data-tab="contract"]');
    await waitFor(client, 'document.body.innerText.includes("support_router.v1")');
    await click(client, '[data-action="select-contract-tab"][data-contract-tab="output"]');
    await waitFor(client, 'document.body.innerText.includes("MIB Router Output") && document.body.innerText.includes("investment_advice_block")');
    await click(client, '[data-action="compile-contract"]');
    await waitFor(client, 'document.body.innerText.includes("Contract compiled")');
    await click(client, '[data-action="test-route"]');
    await waitFor(client, 'document.body.innerText.includes("Test route: investment_advice_block")');

    const smoke = await evaluate(client, `(() => {
      const unnamedButtons = [...document.querySelectorAll("button")].filter((button) => {
        const name = button.textContent.trim() || button.getAttribute("aria-label") || button.getAttribute("title");
        return !name;
      }).length;
      document.querySelector('[data-action="compile-contract"]').focus();
      return {
        unnamedButtons,
        hasCurrentPage: Boolean(document.querySelector('[aria-current="page"]')),
        hasStatusRegion: Boolean(document.querySelector('[role="status"]')),
        focusedAction: document.activeElement?.dataset?.action || "",
      };
    })()`);
    assert.deepEqual(smoke, {
      unnamedButtons: 0,
      hasCurrentPage: true,
      hasStatusRegion: true,
      focusedAction: "compile-contract",
    });
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
