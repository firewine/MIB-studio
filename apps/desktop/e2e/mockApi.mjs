import { createServer } from "node:http";

export function startMockApi({ port = 8910 } = {}) {
  const state = {
    projects: [],
    datasets: [],
    hardware: null,
    job: null,
  };
  const server = createServer(async (request, response) => {
    const url = new URL(request.url || "/", `http://${request.headers.host || "127.0.0.1"}`);
    response.setHeader("Access-Control-Allow-Origin", "*");
    response.setHeader("Access-Control-Allow-Headers", "authorization,content-type,idempotency-key");
    response.setHeader("Access-Control-Allow-Methods", "GET,POST,PATCH,DELETE,OPTIONS");
    if (request.method === "OPTIONS") return json(response, 204);
    try {
      await route(request, response, url, state);
    } catch (error) {
      json(response, 500, { error_code: "MOCK_ERROR", message: error.message, details: {}, trace_id: "mock" });
    }
  });
  return new Promise((resolve) => {
    server.listen(port, "127.0.0.1", () => resolve({ server, state }));
  });
}

async function route(request, response, url, state) {
  if (url.pathname === "/healthz") return json(response, 200, { status: "ok", version: "test" });
  if (url.pathname === "/presets") return json(response, 200, { items: [preset()], next_cursor: null });
  if (url.pathname === "/projects" && request.method === "GET") return json(response, 200, { items: state.projects, next_cursor: null });
  if (url.pathname === "/projects" && request.method === "POST") {
    const body = await readJson(request);
    const project = { id: "proj_1", name: body.name, preset_id: body.preset_id, routes: body.routes.map((item, index) => ({ id: `route_${index}`, ...item, created_at: now() })), archived_at: null, route_taxonomy_locked: false, created_at: now(), updated_at: now() };
    state.projects = [project];
    return json(response, 201, project);
  }
  const projectMatch = url.pathname.match(/^\/projects\/([^/]+)$/);
  if (projectMatch && request.method === "GET") return json(response, 200, state.projects[0]);
  if (projectMatch && request.method === "PATCH") {
    const body = await readJson(request);
    state.projects[0] = { ...state.projects[0], routes: body.routes.map((item, index) => ({ id: `route_${index}`, ...item, created_at: now() })), updated_at: now() };
    return json(response, 200, state.projects[0]);
  }
  const datasetsMatch = url.pathname.match(/^\/projects\/([^/]+)\/datasets$/);
  if (datasetsMatch && request.method === "GET") return json(response, 200, { items: state.datasets, next_cursor: null });
  if (datasetsMatch && request.method === "POST") {
    const body = await readJson(request);
    const dataset = datasetRead(datasetsMatch[1], body.examples);
    state.datasets = [dataset];
    state.datasetWithExamples = { ...dataset, examples: body.examples.map((item, index) => exampleRead(item, index)), next_cursor: null };
    return json(response, 201, dataset);
  }
  const datasetMatch = url.pathname.match(/^\/datasets\/([^/]+)$/);
  if (datasetMatch && request.method === "GET") return json(response, 200, state.datasetWithExamples);
  if (datasetMatch && request.method === "PATCH") {
    state.datasetWithExamples.status = "APPROVED";
    state.datasets[0].status = "APPROVED";
    return json(response, 200, state.datasets[0]);
  }
  if (url.pathname === "/hardware-doctor/result" && !state.hardware) return json(response, 404, { error_code: "HARDWARE_PROFILE_NOT_FOUND", message: "No profile", details: {}, trace_id: "mock" });
  if (url.pathname === "/hardware-doctor/result") return json(response, 200, state.hardware);
  if (url.pathname === "/hardware-doctor/scan") {
    state.job = { job_id: "job_hw_1", status: "SUCCEEDED", type: "hardware_scan", events_url: "/jobs/job_hw_1/events", created_resource_type: "hardware_scan", created_resource_id: "hw_1", idempotency_replayed: false };
    state.hardware = hardwareRead();
    return json(response, 202, state.job);
  }
  const jobMatch = url.pathname.match(/^\/jobs\/([^/]+)$/);
  if (jobMatch) return json(response, 200, { id: jobMatch[1], job_id: jobMatch[1], project_id: null, type: "hardware_scan", status: "SUCCEEDED", resource_class: "cpu_shared", priority: 0, params_json: {}, progress_json: {}, attempt_count: 0, events_url: `/jobs/${jobMatch[1]}/events`, created_at: now(), started_at: now(), ended_at: now() });
  json(response, 404, { error_code: "NOT_FOUND", message: url.pathname, details: {}, trace_id: "mock" });
}

function preset() {
  return { id: "router.basic.v1", name: "Router Basic", preset_type: "router", version: 1, schema_refs: {}, config_json: {}, created_at: now() };
}

function datasetRead(projectId, examples) {
  return { id: "dataset_1", project_id: projectId, status: "BUILT", version: 1, path: "datasets/dataset_1.jsonl", sample_count: examples.length, sha256: "a".repeat(64), schema_version: "router.dataset.v1", route_snapshot_sha256: "b".repeat(64), created_at: now(), frozen_at: null };
}

function exampleRead(item, index) {
  return { id: `example_${index}`, dataset_id: "dataset_1", source: item.source, input: item.input, output: item.output, review_status: "APPROVED", approved: true, validation_errors: [], created_at: now() };
}

function hardwareRead() {
  return { id: "hw_1", machine_id: "mock-machine", os: "Linux", cpu: "Mock CPU", gpu_vendor: "nvidia", gpu_name: "RTX Mock", vram_gb: 24, unified_ram_gb: null, ram_gb: 64, cuda_status: "ok", mlx_status: "na", capability_gate: "G2", backend_recommendation: "cuda", training_enabled: true, training_disabled_reason_code: "NONE", training_disabled_reason_message: "Training is enabled for this hardware gate.", allowed_backends: ["cuda"], unlock_requirements: [], dry_run_result_json: { gate: "G2" }, created_at: now() };
}

function readJson(request) {
  return new Promise((resolve, reject) => {
    let body = "";
    request.on("data", (chunk) => {
      body += chunk;
    });
    request.on("end", () => resolve(body ? JSON.parse(body) : {}));
    request.on("error", reject);
  });
}

function json(response, status, body = null) {
  response.writeHead(status, { "content-type": "application/json" });
  response.end(body === null ? "" : JSON.stringify(body));
}

function now() {
  return "2026-06-21T00:00:00.000Z";
}
