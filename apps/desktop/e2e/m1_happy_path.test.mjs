import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawn } from "node:child_process";
import test from "node:test";
import { startStaticServer } from "../scripts/static-server.mjs";
import { startMockApi } from "./mockApi.mjs";

const chromePath = process.env.CHROME_BIN || "/usr/bin/google-chrome";

test("M1 desktop shell happy path reaches project, dataset, hardware, and job monitor", async () => {
  const staticServer = await startStaticServer({ rootDir: "apps/desktop", port: 5173 });
  const mockApi = await startMockApi({ port: 8910 });
  const userDataDir = mkdtempSync(join(tmpdir(), "mib-chrome-"));
  const chrome = spawn(chromePath, [
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--remote-debugging-port=9223",
    `--user-data-dir=${userDataDir}`,
    "about:blank",
  ]);
  let client;

  try {
    client = await openPage("http://127.0.0.1:5173/projects");
    await waitFor(client, 'document.body.innerText.includes("No projects yet")');
    await click(client, '[data-nav="/projects/new"]');
    await waitFor(client, 'document.body.innerText.includes("Create route contract project")');
    await click(client, '[data-action="create-project"]');
    await waitFor(client, 'document.body.innerText.includes("Project dashboard") || document.body.innerText.includes("support-router")');
    await click(client, '[data-nav="/projects/proj_1/define"]');
    await waitFor(client, 'document.body.innerText.includes("Route contract")');
    await click(client, '[data-action="save-routes"]');
    await waitFor(client, 'document.body.innerText.includes("Contract saved")');
    await click(client, '[data-nav="/projects/proj_1/datasets/new"]');
    await waitFor(client, 'document.body.innerText.includes("20/20 valid")');
    await click(client, '[data-action="build-dataset"]');
    await waitFor(client, 'document.body.innerText.includes("Dataset build result")');
    await click(client, '[data-action="approve-dataset"]');
    await waitFor(client, 'document.body.innerText.includes("Dataset approved")');
    await navigate(client, "http://127.0.0.1:5173/hardware");
    await waitFor(client, 'document.body.innerText.includes("Hardware Doctor")');
    await click(client, '[data-action="scan-hardware"]');
    await waitFor(client, 'document.body.innerText.includes("G2") && document.body.innerText.includes("SUCCEEDED")');
    await navigate(client, "http://127.0.0.1:5173/jobs/job_hw_1");
    await waitFor(client, 'document.body.innerText.includes("Job monitor")');
    const text = await evaluate(client, "document.body.innerText");
    assert.match(text, /SUCCEEDED|EVENT_GAP/);
  } finally {
    client?.close();
    chrome.kill("SIGTERM");
    await waitForProcessExit(chrome);
    staticServer.close();
    mockApi.server.close();
    rmSync(userDataDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
  }
});

async function openPage(url) {
  await waitForHttp("http://127.0.0.1:9223/json/version");
  const target = await fetch(`http://127.0.0.1:9223/json/new?${encodeURIComponent(url)}`, { method: "PUT" }).then((response) => response.json());
  return connectCdp(target.webSocketDebuggerUrl);
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
  throw new Error(`Timed out waiting for ${expression}`);
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
