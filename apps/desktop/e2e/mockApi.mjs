import { createServer } from "node:http";

export function startMockApi({ port = 8910 } = {}) {
  const state = {
    projects: [],
    datasets: [],
    modelRuns: [],
    evalSets: [],
    benchmarks: [],
    benchmarkReports: new Map(),
    agentPackages: [],
    hardware: null,
    job: null,
    credentials: [],
    teacherPacket: null,
  };
  const server = createServer(async (request, response) => {
    const url = new URL(request.url || "/", `http://${request.headers.host || "127.0.0.1"}`);
    response.setHeader("Access-Control-Allow-Origin", "*");
    response.setHeader("Access-Control-Allow-Headers", "authorization,content-type,idempotency-key");
    response.setHeader("Access-Control-Allow-Methods", "GET,POST,PATCH,PUT,DELETE,OPTIONS");
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
  if (url.pathname === "/credentials" && request.method === "GET") return json(response, 200, { items: state.credentials });
  const credentialMatch = url.pathname.match(/^\/credentials\/([^/]+)$/);
  if (credentialMatch && request.method === "PUT") {
    const body = await readJson(request);
    state.credentials = [credentialRead(credentialMatch[1], body.base_url)];
    return json(response, 204);
  }
  if (credentialMatch && request.method === "DELETE") {
    state.credentials = state.credentials.map((item) => ({ ...item, is_revoked: true }));
    return json(response, 204);
  }
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
  const modelRunsMatch = url.pathname.match(/^\/projects\/([^/]+)\/model-runs$/);
  if (modelRunsMatch && request.method === "GET") return json(response, 200, { items: state.modelRuns, next_cursor: null });
  const evalSetsMatch = url.pathname.match(/^\/projects\/([^/]+)\/eval-sets$/);
  if (evalSetsMatch && request.method === "GET") return json(response, 200, { items: state.evalSets, next_cursor: null });
  const benchmarksMatch = url.pathname.match(/^\/projects\/([^/]+)\/benchmarks$/);
  if (benchmarksMatch && request.method === "GET") return json(response, 200, { items: state.benchmarks, next_cursor: null });
  const agentPackagesMatch = url.pathname.match(/^\/projects\/([^/]+)\/agent-packages$/);
  if (agentPackagesMatch && request.method === "GET") return json(response, 200, { items: state.agentPackages, next_cursor: null });
  if (agentPackagesMatch && request.method === "POST") {
    const body = await readJson(request);
    const agentPackage = agentPackageRead(agentPackagesMatch[1], body);
    state.agentPackages = [agentPackage];
    return json(response, 201, agentPackage);
  }
  const projectJobsMatch = url.pathname.match(/^\/projects\/([^/]+)\/jobs$/);
  if (projectJobsMatch && request.method === "POST") {
    const body = await readJson(request);
    if (body.type === "train") {
      state.job = trainJobAccepted(projectJobsMatch[1], body);
      state.modelRuns = [modelRunRead(projectJobsMatch[1], body, state.job.job_id)];
      return json(response, 202, state.job);
    }
    if (body.type === "benchmark") {
      state.job = benchmarkJobAccepted(projectJobsMatch[1], body);
      const benchmark = benchmarkRead(projectJobsMatch[1], body, state.job.job_id);
      state.benchmarks = [benchmark];
      state.benchmarkReports.set(benchmark.id, benchmarkReportRead(benchmark));
      return json(response, 202, state.job);
    }
    return json(response, 409, { error_code: "MILESTONE_LOCKED", message: "Only train and benchmark are unlocked in this mock.", details: {}, trace_id: "mock" });
  }
  const benchmarkReportMatch = url.pathname.match(/^\/benchmarks\/([^/]+)\/report$/);
  if (benchmarkReportMatch && request.method === "GET") {
    const report = state.benchmarkReports.get(benchmarkReportMatch[1]);
    return report ? json(response, 200, report) : json(response, 404, { error_code: "BENCHMARK_NOT_FOUND", message: "No benchmark report", details: {}, trace_id: "mock" });
  }
  const benchmarkMatch = url.pathname.match(/^\/benchmarks\/([^/]+)$/);
  if (benchmarkMatch && request.method === "GET") {
    const benchmark = state.benchmarks.find((item) => item.id === benchmarkMatch[1]);
    return benchmark ? json(response, 200, benchmark) : json(response, 404, { error_code: "BENCHMARK_NOT_FOUND", message: "No benchmark", details: {}, trace_id: "mock" });
  }
  const playgroundMatch = url.pathname.match(/^\/agent-packages\/([^/]+)\/playground-runs$/);
  if (playgroundMatch && request.method === "POST") {
    const agentPackage = state.agentPackages.find((item) => item.id === playgroundMatch[1]);
    return agentPackage ? json(response, 200, playgroundRunRead(agentPackage)) : json(response, 404, { error_code: "AGENT_PACKAGE_NOT_FOUND", message: "No package", details: {}, trace_id: "mock" });
  }
  const agentPackageMatch = url.pathname.match(/^\/agent-packages\/([^/]+)$/);
  if (agentPackageMatch && request.method === "GET") {
    const agentPackage = state.agentPackages.find((item) => item.id === agentPackageMatch[1]);
    return agentPackage ? json(response, 200, agentPackage) : json(response, 404, { error_code: "AGENT_PACKAGE_NOT_FOUND", message: "No package", details: {}, trace_id: "mock" });
  }
  const datasetMatch = url.pathname.match(/^\/datasets\/([^/]+)$/);
  if (datasetMatch && request.method === "GET") return json(response, 200, state.datasetWithExamples);
  if (datasetMatch && request.method === "PATCH") {
    state.datasetWithExamples.status = "APPROVED";
    state.datasetWithExamples.frozen_at = now();
    state.datasets[0].status = "APPROVED";
    state.datasets[0].frozen_at = now();
    state.evalSets = [evalSetRead(state.datasets[0].project_id, state.datasets[0].id)];
    state.datasetWithExamples.examples = state.datasetWithExamples.examples.map((example) => ({ ...example, approved: true, review_status: "APPROVED" }));
    return json(response, 200, state.datasets[0]);
  }
  const previewMatch = url.pathname.match(/^\/projects\/([^/]+)\/teacher-packets\/preview$/);
  if (previewMatch && request.method === "POST") {
    const body = await readJson(request);
    state.teacherPacket = teacherPacketRead(state, previewMatch[1], body);
    return json(response, 200, state.teacherPacket);
  }
  const approvalMatch = url.pathname.match(/^\/teacher-packets\/([^/]+)\/approve$/);
  if (approvalMatch && request.method === "POST") {
    state.teacherPacket = { ...state.teacherPacket, approved_at: now() };
    return json(response, 200, {
      approval_id: approvalMatch[1],
      project_id: state.teacherPacket.project_id,
      packet_sha256: state.teacherPacket.packet_sha256,
      approved_at: state.teacherPacket.approved_at,
      expires_at: state.teacherPacket.expires_at,
    });
  }
  if (url.pathname === "/hardware-doctor/result" && !state.hardware) return json(response, 404, { error_code: "HARDWARE_PROFILE_NOT_FOUND", message: "No profile", details: {}, trace_id: "mock" });
  if (url.pathname === "/hardware-doctor/result") return json(response, 200, state.hardware);
  if (url.pathname === "/hardware-doctor/scan") {
    state.job = { job_id: "job_hw_1", status: "SUCCEEDED", type: "hardware_scan", events_url: "/jobs/job_hw_1/events", created_resource_type: "hardware_scan", created_resource_id: "hw_1", idempotency_replayed: false };
    state.hardware = hardwareRead();
    return json(response, 202, state.job);
  }
  const jobMatch = url.pathname.match(/^\/jobs\/([^/]+)$/);
  if (jobMatch && state.job?.job_id === jobMatch[1]) return json(response, 200, jobRead(state.job));
  json(response, 404, { error_code: "NOT_FOUND", message: url.pathname, details: {}, trace_id: "mock" });
}

function preset() {
  return { id: "router.basic.v1", name: "Router Basic", preset_type: "router", version: 1, schema_refs: {}, config_json: {}, created_at: now() };
}

function datasetRead(projectId, examples) {
  return { id: "dataset_1", project_id: projectId, status: "BUILT", version: 1, path: "datasets/dataset_1.jsonl", sample_count: examples.length, sha256: "a".repeat(64), schema_version: "router.dataset.v1", route_snapshot_sha256: "b".repeat(64), created_at: now(), frozen_at: null };
}

function exampleRead(item, index) {
  return { id: `example_${index}`, dataset_id: "dataset_1", source: item.source, input: item.input, output: item.output, review_status: "PENDING", approved: false, validation_errors: [], created_at: now() };
}

function credentialRead(provider, baseUrl) {
  return { id: `cred_${provider}`, provider, base_url_origin: baseUrl.replace(/\/v1$/, ""), keychain_ref: `keyring://MIB%20Studio/credential:${provider}:mock`, is_revoked: false, expires_at: null, created_at: now(), last_used_at: null };
}

function teacherPacketRead(state, projectId, body) {
  return {
    id: "packet_1",
    project_id: projectId,
    packet_sha256: "c".repeat(64),
    packet_preview: {
      rules: state.projects[0]?.routes || [],
      schema: { type: "object", required: ["route", "confidence"] },
      anonymized_examples: body.example_ids.map((id, index) => ({ example_id: id, input: { text: `masked ${index}` }, output: { route: "support" } })),
      instruction: body.instruction,
    },
    pii_summary: {
      policy_version: "pii.v1",
      example_count: body.example_ids.length,
      masked_count: 20,
      entity_counts: { email: 10, phone: 10 },
      transmitted: ["rule schema", "output schema", "anonymized_examples", "generation instruction"],
      not_transmitted: ["raw CSV", "file paths", "personal identifiers", "unapproved samples"],
    },
    expires_at: "2026-06-21T00:30:00.000Z",
    approved_at: null,
  };
}

function trainJobAccepted(projectId, body) {
  return {
    job_id: "job_train_1",
    project_id: projectId,
    status: "QUEUED",
    type: "train",
    events_url: "/jobs/job_train_1/events",
    created_resource_type: "model_run",
    created_resource_id: "model_run_1",
    idempotency_replayed: false,
    params_json: body.params,
  };
}

function modelRunRead(projectId, body, jobId) {
  return {
    id: "model_run_1",
    job_id: jobId,
    project_id: projectId,
    dataset_id: body.params.dataset_id,
    base_model: body.params.base_model,
    backend: body.params.backend,
    method: body.params.backend === "mlx" ? "mlx_lora" : "qlora",
    adapter_path: "adapters/model_run_1",
    status: "SUCCEEDED",
    adapter_sha256: "e".repeat(64),
    artifact_manifest_sha256: "f".repeat(64),
    seed: body.params.seed,
    config_hash: "d".repeat(64),
    best_checkpoint_id: null,
    resumable: false,
    started_at: null,
    ended_at: null,
    created_at: now(),
  };
}

function evalSetRead(projectId, datasetId) {
  return {
    id: "eval_set_1",
    project_id: projectId,
    dataset_id: datasetId,
    purpose: "benchmark_gold",
    version: 1,
    path: "eval_sets/eval_set_1.jsonl",
    sha256: "8".repeat(64),
    sample_count: 200,
    route_snapshot_sha256: "b".repeat(64),
    labeler_ids_json: ["domain_labeler", "security_labeler", "tie_breaker"],
    kappa: 0.81,
    frozen_at: now(),
    created_at: now(),
  };
}

function benchmarkJobAccepted(projectId, body) {
  return {
    job_id: "job_benchmark_1",
    project_id: projectId,
    status: "QUEUED",
    type: "benchmark",
    events_url: "/jobs/job_benchmark_1/events",
    created_resource_type: "benchmark",
    created_resource_id: "benchmark_1",
    idempotency_replayed: false,
    params_json: body.params,
  };
}

function benchmarkRead(projectId, body, jobId) {
  return {
    id: "benchmark_1",
    project_id: projectId,
    job_id: jobId,
    eval_set_id: body.params.eval_set_id,
    status: "COMPLETED",
    report_sha256: "9".repeat(64),
    hash_status: "VALID",
    parity_status: "PASS",
    created_at: now(),
    completed_at: now(),
  };
}

function benchmarkReportRead(benchmark) {
  return {
    benchmark_id: benchmark.id,
    report_sha256: benchmark.report_sha256,
    hash_status: "VALID",
    report: {
      schema_version: "benchmark_report.v1",
      source: "mock_browser",
      mock_only: true,
      eval_set: { purpose: "benchmark_gold", sample_count: 200 },
      targets: [
        { target_key: "ft_cuda", target_status: "COMPLETED", mean_metrics: { route_accuracy: 0.918, latency_p50_ms: 420, effective_cost_per_task_usd: 0.00012 } },
        { target_key: "teacher_gpt", target_status: "COMPLETED", mean_metrics: { route_accuracy: 0.947, latency_p50_ms: 2900, effective_cost_per_task_usd: 0.001 } },
        { target_key: "prompt_gemma", target_status: "COMPLETED", mean_metrics: { route_accuracy: 0.729, latency_p50_ms: 390, effective_cost_per_task_usd: 0.0001 } },
        { target_key: "rule_router", target_status: "COMPLETED", mean_metrics: { route_accuracy: 0.704, latency_p50_ms: 12, effective_cost_per_task_usd: 0 } },
      ],
    },
  };
}

function agentPackageRead(projectId, body) {
  const contractYaml = [
    "agent_id: support_router.v1",
    "agent_type: router",
    "runtime:",
    "  engine: local_playground_mock",
    "adapter:",
    `  model_run_id: ${body.model_run_id}`,
    "  sha256: " + "e".repeat(64),
    "benchmark_report:",
    `  id: ${body.benchmark_id}`,
    "fallback:",
    "  enabled: false",
  ].join("\n");
  return {
    id: "agent_package_1",
    agent_id: "support_router.v1",
    project_id: projectId,
    model_run_id: body.model_run_id,
    benchmark_id: body.benchmark_id,
    route_catalog_sha256: "b".repeat(64),
    contract_version: 1,
    contract_yaml: contractYaml,
    contract_sha256: "7".repeat(64),
    created_at: now(),
  };
}

function playgroundRunRead(agentPackage) {
  return {
    output: {
      route: "technical_support",
      task_type: "generate_report",
      requires_calculation: false,
      requires_human_review: false,
      confidence: 0.94,
      agent_id: agentPackage.agent_id,
    },
    verifier_status: "PASS",
    verifier_errors: [],
    fallback_required: false,
    fallback_used: false,
    audit_event_id: "audit_playground_1",
  };
}

function jobRead(job) {
  return {
    id: job.job_id,
    job_id: job.job_id,
    project_id: job.project_id || null,
    type: job.type,
    status: job.status,
    resource_class: job.type === "train" ? "gpu_exclusive" : "cpu_shared",
    priority: 0,
    params_json: job.params_json || {},
    progress_json: {},
    attempt_count: 0,
    events_url: `/jobs/${job.job_id}/events`,
    created_at: now(),
    started_at: job.status === "QUEUED" ? null : now(),
    ended_at: job.status === "QUEUED" ? null : now(),
  };
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
