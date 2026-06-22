import assert from "node:assert/strict";
import test from "node:test";
import { ApiClientError, createApiClient } from "./apiClient.mjs";

test("createApiClient attaches bearer and idempotency headers", async () => {
  const seen = {};
  const api = createApiClient({ baseUrl: "http://local.test/", token: "secret" }, async (url, init) => {
    seen.url = url;
    seen.init = init;
    return response(202, { job_id: "job_1", status: "SUCCEEDED" });
  });

  await api.request("submitHardwareScan", {
    body: { dry_run: true, target_backend: "auto" },
    idempotencyKey: "idem-1",
  });

  assert.equal(seen.url, "http://local.test/hardware-doctor/scan");
  assert.equal(seen.init.headers.Authorization, "Bearer secret");
  assert.equal(seen.init.headers["Idempotency-Key"], "idem-1");
  assert.equal(seen.init.headers["Content-Type"], "application/json");
});

test("createApiClient builds path and query params", async () => {
  let requestedUrl = "";
  const api = createApiClient({ baseUrl: "http://local.test", token: "secret" }, async (url) => {
    requestedUrl = url;
    return response(200, { items: [] });
  });
  await api.request("listDatasets", { params: { id: "proj 1", limit: 20 } });
  assert.equal(requestedUrl, "http://local.test/projects/proj%201/datasets?limit=20");
});

test("createApiClient maps train workflow job and model-run routes", async () => {
  const seen = [];
  const api = createApiClient({ baseUrl: "http://local.test", token: "secret" }, async (url, init) => {
    seen.push({ url, init });
    return response(200, { items: [] });
  });

  await api.request("listModelRuns", { params: { id: "proj 1", backend: "cuda", status: "QUEUED" } });
  await api.request("submitProjectJob", {
    params: { id: "proj 1" },
    body: { type: "train", params: { dataset_id: "dataset_1", base_model: "google/gemma-2b-it", backend: "cuda", training_preset: "balanced", seed: 123 } },
    idempotencyKey: "train-1",
  });

  assert.equal(seen[0].url, "http://local.test/projects/proj%201/model-runs?backend=cuda&status=QUEUED");
  assert.equal(seen[1].url, "http://local.test/projects/proj%201/jobs");
  assert.equal(seen[1].init.headers["Idempotency-Key"], "train-1");
  assert.equal(JSON.parse(seen[1].init.body).type, "train");
});

test("createApiClient maps Benchmark workflow routes", async () => {
  const seen = [];
  const api = createApiClient({ baseUrl: "http://local.test", token: "secret" }, async (url, init) => {
    seen.push({ url, init });
    return response(200, { items: [], hash_status: "MISSING" });
  });

  await api.request("listEvalSets", { params: { id: "proj 1", purpose: "benchmark_gold" } });
  await api.request("listBenchmarks", { params: { id: "proj 1", status: "COMPLETED" } });
  await api.request("getBenchmark", { params: { id: "bench 1" } });
  await api.request("getBenchmarkReport", { params: { id: "bench 1" } });
  await api.request("submitProjectJob", {
    params: { id: "proj 1" },
    body: { type: "benchmark", params: { eval_set_id: "eval_1", targets: [], seeds: [42, 123, 456] } },
    idempotencyKey: "benchmark-1",
  });

  assert.equal(seen[0].url, "http://local.test/projects/proj%201/eval-sets?purpose=benchmark_gold");
  assert.equal(seen[1].url, "http://local.test/projects/proj%201/benchmarks?status=COMPLETED");
  assert.equal(seen[2].url, "http://local.test/benchmarks/bench%201");
  assert.equal(seen[3].url, "http://local.test/benchmarks/bench%201/report");
  assert.equal(seen[4].url, "http://local.test/projects/proj%201/jobs");
  assert.equal(seen[4].init.headers["Idempotency-Key"], "benchmark-1");
  assert.equal(JSON.parse(seen[4].init.body).type, "benchmark");
});

test("createApiClient maps Package and Playground workflow routes", async () => {
  const seen = [];
  const api = createApiClient({ baseUrl: "http://local.test", token: "secret" }, async (url, init) => {
    seen.push({ url, init });
    return response(200, { items: [], verifier_status: "PASS" });
  });

  await api.request("listAgentPackages", { params: { id: "proj 1" } });
  await api.request("createAgentPackage", {
    params: { id: "proj 1" },
    body: {
      agent_slug: "support_router",
      model_run_id: "model_run_1",
      benchmark_id: "benchmark_1",
      fallback: { enabled: false, provider: "none", condition: { type: "disabled" } },
    },
  });
  await api.request("getAgentPackage", { params: { agent_package_id: "pkg 1" } });
  await api.request("runPlayground", {
    params: { agent_package_id: "pkg 1" },
    body: { input: { text: "Need support", allowed_routes: ["technical_support", "human_review"] } },
  });

  assert.equal(seen[0].url, "http://local.test/projects/proj%201/agent-packages");
  assert.equal(seen[1].url, "http://local.test/projects/proj%201/agent-packages");
  assert.equal(seen[1].init.method, "POST");
  assert.equal(JSON.parse(seen[1].init.body).fallback.condition.type, "disabled");
  assert.equal(seen[2].url, "http://local.test/agent-packages/pkg%201");
  assert.equal(seen[3].url, "http://local.test/agent-packages/pkg%201/playground-runs");
});

test("createApiClient maps Export workflow routes", async () => {
  const seen = [];
  const api = createApiClient({ baseUrl: "http://local.test", token: "secret" }, async (url, init) => {
    seen.push({ url, init });
    return response(200, { job_id: "job_export_1", status: "QUEUED" });
  });

  await api.request("createExport", {
    params: { id: "proj 1" },
    body: { agent_package_id: "pkg 1", export_type: "zip" },
    idempotencyKey: "export-1",
  });
  await api.request("getExport", { params: { job_id: "job export 1" } });
  await api.request("revealExportArtifact", { params: { job_id: "job export 1" } });

  assert.equal(seen[0].url, "http://local.test/projects/proj%201/export");
  assert.equal(seen[0].init.method, "POST");
  assert.equal(seen[0].init.headers["Idempotency-Key"], "export-1");
  assert.equal(JSON.parse(seen[0].init.body).export_type, "zip");
  assert.equal(seen[1].url, "http://local.test/exports/job%20export%201");
  assert.equal(seen[2].url, "http://local.test/exports/job%20export%201/reveal");
});

test("createApiClient raises typed API errors", async () => {
  const api = createApiClient({ baseUrl: "http://local.test", token: "secret" }, async () =>
    response(409, { error_code: "MILESTONE_LOCKED", message: "locked", details: {}, trace_id: "t1" }),
  );
  await assert.rejects(() => api.request("getJob", { params: { job_id: "job_1" } }), (error) => {
    assert.equal(error instanceof ApiClientError, true);
    assert.equal(error.status, 409);
    assert.equal(error.payload.error_code, "MILESTONE_LOCKED");
    return true;
  });
});

function response(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status >= 400 ? "error" : "ok",
    headers: new Map(),
    async json() {
      return body;
    },
  };
}
