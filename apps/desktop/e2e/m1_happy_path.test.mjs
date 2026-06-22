import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawn } from "node:child_process";
import test from "node:test";
import { startStaticServer } from "../scripts/static-server.mjs";
import { startMockApi } from "./mockApi.mjs";

const chromePath = process.env.CHROME_BIN || "/usr/bin/google-chrome";

test("M1 desktop shell happy path reaches project, dataset, hardware, train, benchmark, and job monitor", async () => {
  const staticPort = 5173;
  const apiPort = 8910;
  const cdpPort = 9223;
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
    await navigate(client, `http://127.0.0.1:${staticPort}/projects/proj_1/training`);
    await waitFor(client, 'document.body.innerText.includes("Train workflow") && document.body.innerText.includes("Start train")');
    await click(client, '[data-action="start-train"]');
    await waitFor(client, 'document.body.innerText.includes("Training job accepted: QUEUED") && document.body.innerText.includes("model_run_1")');
    await navigate(client, `http://127.0.0.1:${staticPort}/jobs/job_train_1`);
    await waitFor(client, 'document.body.innerText.includes("Job monitor")');
    let text = await evaluate(client, "document.body.innerText");
    assert.match(text, /QUEUED|EVENT_GAP/);
    await navigate(client, `http://127.0.0.1:${staticPort}/settings/teacher`);
    await waitFor(client, 'document.body.innerText.includes("Teacher provider")');
    await fill(client, '[data-field="credential-api-key"]', "test-key");
    await click(client, '[data-action="save-credential"]');
    await waitFor(client, 'document.body.innerText.includes("Teacher credential saved")');
    await navigate(client, `http://127.0.0.1:${staticPort}/projects/proj_1/benchmarks/new`);
    await waitFor(client, 'document.body.innerText.includes("Benchmark workflow") && document.body.innerText.includes("Run benchmark")');
    await click(client, '[data-action="run-benchmark"]');
    await waitFor(client, 'document.body.innerText.includes("Benchmark job accepted: QUEUED") && document.body.innerText.includes("mock-only") && document.body.innerText.includes("benchmark report")');
    await navigate(client, `http://127.0.0.1:${staticPort}/jobs/job_benchmark_1`);
    await waitFor(client, 'document.body.innerText.includes("Job monitor")');
    text = await evaluate(client, "document.body.innerText");
    assert.match(text, /benchmark|QUEUED|EVENT_GAP/);
  } finally {
    client?.close();
    if (chrome.exitCode === null && !chrome.signalCode) chrome.kill("SIGTERM");
    if (!(await waitForProcessExit(chrome, 3000)) && chrome.exitCode === null && !chrome.signalCode) {
      chrome.kill("SIGKILL");
      await waitForProcessExit(chrome, 3000);
    }
    staticServer.close();
    mockApi.server.close();
    try {
      rmSync(userDataDir, { recursive: true, force: true, maxRetries: 20, retryDelay: 200 });
    } catch (error) {
      if (!["EBUSY", "ENOTEMPTY"].includes(error.code)) throw error;
    }
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

async function fill(client, selector, value) {
  await evaluate(client, `(() => {
    const field = document.querySelector(${JSON.stringify(selector)});
    field.value = ${JSON.stringify(value)};
    field.dispatchEvent(new Event("input", { bubbles: true }));
  })()`);
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

function waitForProcessExit(child, timeoutMs = 1000) {
  if (child.exitCode !== null || child.signalCode) return Promise.resolve(true);
  return new Promise((resolve) => {
    const timer = setTimeout(() => resolve(false), timeoutMs);
    child.once("exit", () => {
      clearTimeout(timer);
      resolve(true);
    });
  });
}
