import {
  addRoute,
  addRoutePreset,
  applyRoutePatch,
  createContract,
  createSeedExamples,
  initialRoutes,
  paletteCategories,
  parseAppRoute,
  routesFromProject,
  routesToProjectInput,
  validateRoutes,
  workflowSteps,
} from "./lib/appModel.mjs";
import { ApiClientError, createApiClient, idempotencyKey, resolveBootstrap } from "./lib/apiClient.mjs";
import { routeContractPage } from "./lib/routeContractView.mjs";

const root = document.getElementById("root");
const state = {
  api: null,
  bootstrap: null,
  path: normalizePath(location.pathname),
  projects: [],
  presets: [],
  selectedProject: null,
  datasets: [],
  dataset: null,
  modelRuns: [],
  evalSets: [],
  benchmarks: [],
  benchmarkReport: null,
  agentPackages: [],
  playgroundResult: null,
  hardware: null,
  lastJob: null,
  credentials: [],
  teacherPacket: null,
  teacherApproval: null,
  teacherInstruction: "Generate schema-valid router examples without personal data.",
  routes: [...initialRoutes],
  examples: [],
  online: false,
  loading: true,
  apiError: null,
  notice: null,
  selectedRoute: 0,
  selectedPaletteCategory: "input",
  inspectorTab: "route",
  contractTab: "agent",
  routeTestResult: null,
};

start();

async function start() {
  state.bootstrap = await resolveBootstrap();
  state.api = createApiClient(state.bootstrap);
  await refresh();
  addEventListener("popstate", () => {
    state.path = normalizePath(location.pathname);
    void loadRouteData();
  });
  root.addEventListener("click", onClick);
  root.addEventListener("input", onInput);
  render();
}

async function refresh() {
  if (!state.api) return;
  state.loading = true;
  state.apiError = null;
  try {
    await state.api.request("healthz");
    const [projects, presets, hardware, credentials] = await Promise.all([
      state.api.request("listProjects", { params: { include_archived: false } }).catch(() => ({ items: [] })),
      state.api.request("listPresets").catch(() => ({ items: [] })),
      getHardware(),
      state.api.request("listCredentials").catch(() => ({ items: [] })),
    ]);
    state.projects = projects.items || [];
    state.presets = presets.items || [];
    state.hardware = hardware;
    state.credentials = credentials.items || [];
    state.online = true;
    await loadRouteData();
  } catch (error) {
    state.online = false;
    state.apiError = errorText(error);
  } finally {
    state.loading = false;
  }
}

async function loadRouteData() {
  const route = parseAppRoute(state.path);
  state.selectedProject = "projectId" in route ? state.projects.find((project) => project.id === route.projectId) || null : state.projects[0] || null;
  if (state.selectedProject) {
    state.datasets = (await state.api.request("listDatasets", { params: { id: state.selectedProject.id } }).catch(() => ({ items: [] }))).items || [];
    if (["projectDashboard", "projectTraining", "projectBenchmark", "projectPackage"].includes(route.name)) {
      state.modelRuns = (await state.api.request("listModelRuns", { params: { id: state.selectedProject.id } }).catch(() => ({ items: [] }))).items || [];
    }
    if (["projectDashboard", "projectBenchmark", "projectPackage"].includes(route.name)) {
      state.benchmarks = (await state.api.request("listBenchmarks", { params: { id: state.selectedProject.id } }).catch(() => ({ items: [] }))).items || [];
    }
    if (route.name === "projectBenchmark") {
      state.evalSets = (await state.api.request("listEvalSets", { params: { id: state.selectedProject.id, purpose: "benchmark_gold" } }).catch(() => ({ items: [] }))).items || [];
      const latest = latestBenchmark();
      state.benchmarkReport = latest ? await state.api.request("getBenchmarkReport", { params: { id: latest.id } }).catch(() => null) : null;
    } else {
      state.benchmarkReport = null;
    }
    if (["projectDashboard", "projectPackage"].includes(route.name)) {
      state.agentPackages = (await state.api.request("listAgentPackages", { params: { id: state.selectedProject.id } }).catch(() => ({ items: [] }))).items || [];
    }
    if (route.name !== "projectPackage") {
      state.playgroundResult = null;
    }
  }
  if (route.name === "projectDefine" && state.selectedProject) state.routes = routesFromProject(state.selectedProject);
  if (route.name === "datasetNew" && state.selectedProject) state.examples = createSeedExamples(routesFromProject(state.selectedProject));
  if (route.name === "datasetDetail") state.dataset = await state.api.request("getDataset", { params: { id: route.datasetId } });
  if (route.name !== "datasetDetail") {
    state.teacherPacket = null;
    state.teacherApproval = null;
  }
  if (route.name === "job" && state.lastJob?.job_id === route.jobId) state.notice = "poll fallback uses last accepted job snapshot";
  render();
}

async function getHardware() {
  try {
    return await state.api.request("getHardwareDoctorResult");
  } catch (error) {
    if (error instanceof ApiClientError && error.payload.error_code === "HARDWARE_PROFILE_NOT_FOUND") return null;
    throw error;
  }
}

function navigate(path) {
  const next = normalizePath(path);
  history.pushState({}, "", next);
  state.path = next;
  void loadRouteData();
}

async function onClick(event) {
  const target = event.target.closest("[data-action],[data-nav],[data-route-index]");
  if (!target) return;
  if (target.dataset.nav) return navigate(target.dataset.nav);
  if (target.dataset.routeIndex !== undefined) {
    state.selectedRoute = Number(target.dataset.routeIndex);
    return render();
  }
  const action = target.dataset.action;
  try {
    if (action === "refresh") await refresh();
    if (action === "create-project") await createProject();
    if (action === "save-routes") await saveRoutes();
    if (action === "build-dataset") await buildDataset();
    if (action === "approve-dataset") await approveDataset();
    if (action === "preview-teacher-packet") await previewTeacherPacket();
    if (action === "approve-teacher-packet") await approveTeacherPacket();
    if (action === "save-credential") await saveCredential();
    if (action === "delete-credential") await deleteCredential();
    if (action === "scan-hardware") await scanHardware();
    if (action === "start-train") await startTrain();
    if (action === "run-benchmark") await runBenchmark();
    if (action === "build-package") await buildPackage();
    if (action === "run-playground") await runPlayground();
    if (action === "poll-job") await pollJob();
    if (action === "select-palette") selectPalette(target.dataset.palette);
    if (action === "insert-block") insertBlock(target.dataset.blockLabel);
    if (action === "select-inspector-tab") selectInspectorTab(target.dataset.tab);
    if (action === "select-contract-tab") selectContractTab(target.dataset.contractTab);
    if (action === "apply-route") applySelectedRouteFromDom();
    if (action === "add-route") addDraftRoute();
    if (action === "add-preset") addPresetRoutes(target.dataset.preset);
    if (action === "compile-contract") compileContract();
    if (action === "test-route") testSelectedRoute();
    if (action === "download-contract") downloadContract();
    state.apiError = null;
  } catch (error) {
    state.apiError = errorText(error);
  }
  render();
}

function onInput(event) {
  const field = event.target.dataset.field;
  if (!field) return;
  if (field === "project-name") state.projectName = event.target.value;
  if (field === "teacher-instruction") state.teacherInstruction = event.target.value;
  if (field === "credential-base-url") state.credentialBaseUrl = event.target.value;
  if (field === "credential-api-key") state.credentialApiKey = event.target.value;
  const selected = state.routes[state.selectedRoute];
  if (!selected) return;
  if (field === "route-id") selected.route_id = event.target.value;
  if (field === "route-desc") selected.description = event.target.value;
  if (field === "task-type") selected.task_type = event.target.value;
  if (field === "examples") selected.examples = event.target.value.split("\n").map((item) => item.trim()).filter(Boolean);
  if (field === "calculation") selected.requires_calculation = event.target.checked;
  if (field === "unsafe") selected.is_unsafe = event.target.checked;
  if (field === "review") selected.requires_human_review = event.target.checked;
  if (field === "default-route") {
    state.routes = applyRoutePatch(state.routes, state.selectedRoute, { is_default: event.target.checked });
  }
  render();
}

async function createProject() {
  const checks = validateRoutes(initialRoutes);
  if (!checks.every((check) => check.ok)) return;
  const project = await state.api.request("createProject", {
    body: {
      name: state.projectName || "support-router",
      preset_id: state.presets[0]?.id || "router.basic.v1",
      routes: routesToProjectInput(initialRoutes),
    },
  });
  await refresh();
  navigate(`/projects/${project.id}`);
}

async function saveRoutes() {
  if (!state.selectedProject || !validateRoutes(state.routes).every((check) => check.ok)) return;
  await state.api.request("updateProject", {
    params: { id: state.selectedProject.id },
    body: { routes: routesToProjectInput(state.routes) },
  });
  state.notice = "Contract saved.";
  state.selectedProject = { ...state.selectedProject, routes: routesToProjectInput(state.routes) };
}

async function buildDataset() {
  if (!state.selectedProject || state.examples.length < 20) return;
  const dataset = await state.api.request("createDataset", {
    params: { id: state.selectedProject.id },
    body: { status: "BUILT", examples: state.examples },
  });
  await refresh();
  navigate(`/datasets/${dataset.id}`);
}

async function approveDataset() {
  if (!state.dataset) return;
  await state.api.request("updateDataset", {
    params: { id: state.dataset.id },
    body: { status: "APPROVED", approved_example_ids: state.dataset.examples.slice(0, 20).map((example) => example.id) },
  });
  state.notice = "Dataset approved.";
  state.dataset = await state.api.request("getDataset", { params: { id: state.dataset.id } });
  state.datasets = state.datasets.map((dataset) => (dataset.id === state.dataset.id ? { ...dataset, status: "APPROVED", frozen_at: state.dataset.frozen_at } : dataset));
}

async function startTrain() {
  if (!state.selectedProject) return;
  const dataset = approvedDataset();
  if (!dataset) {
    state.notice = "Training requires an approved dataset.";
    return;
  }
  if (!state.hardware?.training_enabled) {
    state.notice = "Training requires a G1/G2 Hardware Doctor result.";
    return;
  }
  const backend = trainingBackend();
  state.lastJob = await state.api.request("submitProjectJob", {
    params: { id: state.selectedProject.id },
    body: {
      type: "train",
      params: {
        preset_id: state.selectedProject.preset_id || "router.basic.v1",
        dataset_id: dataset.id,
        base_model: "google/gemma-2b-it",
        backend,
        training_preset: "balanced",
        seed: 123,
      },
    },
    idempotencyKey: idempotencyKey(`train-${dataset.id}`),
  });
  state.modelRuns = (await state.api.request("listModelRuns", { params: { id: state.selectedProject.id } }).catch(() => ({ items: state.modelRuns }))).items || [];
  state.notice = `Training job accepted: ${state.lastJob.status}.`;
}

async function runBenchmark() {
  if (!state.selectedProject) return;
  const modelRun = completedModelRun();
  const evalSet = benchmarkEvalSet();
  const credential = teacherCredential();
  if (!modelRun) {
    state.notice = "Benchmark requires a completed model run.";
    return;
  }
  if (!evalSet) {
    state.notice = "Benchmark requires a frozen benchmark_gold EvalSet.";
    return;
  }
  if (!credential) {
    state.notice = "Benchmark requires a teacher credential baseline.";
    return;
  }
  state.lastJob = await state.api.request("submitProjectJob", {
    params: { id: state.selectedProject.id },
    body: {
      type: "benchmark",
      params: {
        eval_set_id: evalSet.id,
        targets: benchmarkTargets(modelRun, credential),
        seeds: [42, 123, 456],
      },
    },
    idempotencyKey: idempotencyKey(`benchmark-${modelRun.id}-${evalSet.id}`),
  });
  state.benchmarks = (await state.api.request("listBenchmarks", { params: { id: state.selectedProject.id } }).catch(() => ({ items: state.benchmarks }))).items || [];
  const latest = latestBenchmark();
  state.benchmarkReport = latest ? await state.api.request("getBenchmarkReport", { params: { id: latest.id } }).catch(() => null) : null;
  state.notice = `Benchmark job accepted: ${state.lastJob.status}.`;
}

async function buildPackage() {
  if (!state.selectedProject) return;
  const modelRun = completedModelRun();
  const benchmark = validBenchmark();
  if (!modelRun || !benchmark) {
    state.notice = "Package requires a completed model run and valid benchmark report.";
    return;
  }
  const created = await state.api.request("createAgentPackage", {
    params: { id: state.selectedProject.id },
    body: {
      agent_slug: "support_router",
      model_run_id: modelRun.id,
      benchmark_id: benchmark.id,
      fallback: {
        enabled: false,
        provider: "none",
        condition: { type: "disabled" },
      },
    },
  });
  state.agentPackages = [created, ...state.agentPackages.filter((item) => item.id !== created.id)];
  state.notice = `Package built: ${created.agent_id}.`;
}

async function runPlayground() {
  const agentPackage = latestAgentPackage();
  if (!agentPackage) {
    state.notice = "Playground requires an agent package.";
    return;
  }
  state.playgroundResult = await state.api.request("runPlayground", {
    params: { agent_package_id: agentPackage.id },
    body: {
      input: {
        text: "The app keeps freezing and I need support.",
        allowed_routes: routesFromProject(state.selectedProject).map((route) => route.route_id),
      },
    },
  });
  state.notice = `Playground result: ${state.playgroundResult.verifier_status}.`;
}

function approvedDataset() {
  return state.datasets.find((dataset) => dataset.status === "APPROVED" || dataset.frozen_at) || null;
}

function completedModelRun() {
  return state.modelRuns.find((run) => run.status === "SUCCEEDED" && run.adapter_sha256 && run.artifact_manifest_sha256) || null;
}

function benchmarkEvalSet() {
  return state.evalSets.find((item) => ["benchmark_gold", "finance_reference"].includes(item.purpose)) || null;
}

function latestBenchmark() {
  return state.benchmarks[0] || null;
}

function validBenchmark() {
  return state.benchmarks.find((item) => item.status === "COMPLETED" && item.hash_status === "VALID") || null;
}

function latestAgentPackage() {
  return state.agentPackages[0] || null;
}

function teacherCredential() {
  return state.credentials.find((item) => !item.is_revoked) || null;
}

function trainingBackend() {
  const recommended = state.hardware?.backend_recommendation;
  if (recommended === "cuda" || recommended === "mlx") return recommended;
  const allowed = state.hardware?.allowed_backends || [];
  if (allowed.includes("cuda")) return "cuda";
  if (allowed.includes("mlx")) return "mlx";
  return "cuda";
}

function benchmarkTargets(modelRun, credential) {
  return [
    {
      target_key: "prompt_gemma",
      target_type: "prompt_only",
      backend: "prompt_only",
      base_model: modelRun.base_model,
      prompt_template_sha256: "410ca967a64b6a71d53d82cd9102f0767c5d94d4af27640826fb60feced9e9dd",
    },
    {
      target_key: `ft_${modelRun.backend}`,
      target_type: "fine_tuned",
      backend: modelRun.backend,
      model_run_id: modelRun.id,
    },
    {
      target_key: "teacher_gpt",
      target_type: "teacher",
      backend: "teacher",
      credential_id: credential.id,
      teacher_base_url_origin: credential.base_url_origin || "https://teacher.example.test",
    },
    {
      target_key: "rule_router",
      target_type: "rule_based",
      backend: "rule_based",
      routing_rules_path: "rules/router.routing_rules.v1.yaml",
      routing_rules_sha256: "1b9501f1ba0bbd527beacab98e34d5355d676c0ba60b151a22be87e369232934",
    },
  ];
}

async function previewTeacherPacket() {
  if (!state.dataset) return;
  const approved = state.dataset.examples.filter((example) => example.approved).slice(0, 50);
  if (approved.length < 20) {
    state.notice = "Teacher packet requires at least 20 approved examples.";
    return;
  }
  state.teacherPacket = await state.api.request("previewTeacherPacket", {
    params: { id: state.dataset.project_id },
    body: {
      dataset_id: state.dataset.id,
      example_ids: approved.map((example) => example.id),
      instruction: state.teacherInstruction,
    },
  });
  state.teacherApproval = null;
  state.notice = "Teacher Packet Preview created.";
}

async function approveTeacherPacket() {
  if (!state.teacherPacket) return;
  state.teacherApproval = await state.api.request("approveTeacherPacket", { params: { id: state.teacherPacket.id } });
  state.teacherPacket = { ...state.teacherPacket, approved_at: state.teacherApproval.approved_at };
  state.notice = "Teacher Packet approved for one generation job.";
}

async function saveCredential() {
  await state.api.request("upsertCredential", {
    params: { provider: "openai_compatible" },
    body: {
      base_url: state.credentialBaseUrl || "https://api.openai.com/v1",
      api_key: state.credentialApiKey || "",
    },
  });
  state.credentialApiKey = "";
  state.notice = "Teacher credential saved to OS keychain.";
  await refresh();
}

async function deleteCredential() {
  await state.api.request("deleteCredential", { params: { provider: "openai_compatible" } });
  state.notice = "Teacher credential revoked.";
  await refresh();
}

async function scanHardware() {
  state.lastJob = await state.api.request("submitHardwareScan", {
    body: { dry_run: true, target_backend: "auto" },
    idempotencyKey: idempotencyKey("hardware"),
  });
  state.hardware = await getHardware();
  state.notice = `Hardware scan ${state.lastJob.status}.`;
}

async function pollJob() {
  const route = parseAppRoute(state.path);
  if (route.name !== "job") return;
  try {
    state.lastJob = await state.api.request("getJob", { params: { job_id: route.jobId } });
    state.notice = "Job polling refreshed.";
  } catch (error) {
    state.notice = `EVENT_GAP: ${errorText(error)}`;
  }
}

function selectPalette(paletteId) {
  if (paletteCategories.some((category) => category.id === paletteId)) state.selectedPaletteCategory = paletteId;
}

function insertBlock(label) {
  state.notice = `v6 route contract block inserted: ${label}`;
}

function selectInspectorTab(tabId) {
  if (["route", "checks", "contract"].includes(tabId)) state.inspectorTab = tabId;
}

function selectContractTab(tabId) {
  if (["agent", "input", "output", "rules"].includes(tabId)) {
    state.contractTab = tabId;
    state.inspectorTab = "contract";
  }
}

function applySelectedRouteFromDom() {
  const routeId = readField("route-id").trim();
  const patch = {
    route_id: routeId || `route_${state.selectedRoute + 1}`,
    description: readField("route-desc").trim() || "Untitled route",
    task_type: readField("task-type"),
    examples: readField("examples")
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean),
    requires_calculation: readChecked("calculation"),
    requires_human_review: readChecked("review"),
    is_unsafe: readChecked("unsafe"),
    is_default: readChecked("default-route"),
  };
  state.routes = applyRoutePatch(state.routes, state.selectedRoute, patch);
  state.notice = "Route updated.";
}

function addDraftRoute() {
  state.routes = addRoute(state.routes);
  state.selectedRoute = state.routes.length - 1;
  state.inspectorTab = "route";
  state.notice = "Route added.";
}

function addPresetRoutes(presetId) {
  const before = state.routes.length;
  state.routes = addRoutePreset(state.routes, presetId);
  state.selectedRoute = Math.max(0, state.routes.length - 1);
  state.notice = state.routes.length > before ? `${presetId} preset added.` : `${presetId} preset already present.`;
}

function compileContract() {
  const issues = validateRoutes(state.routes).filter((check) => !check.ok);
  state.inspectorTab = issues.length ? "checks" : "contract";
  state.notice = issues.length ? `Contract has ${issues.length} issue(s).` : "Contract compiled.";
}

function testSelectedRoute() {
  const route = state.routes[state.selectedRoute] || state.routes[0];
  state.routeTestResult = {
    route: route.route_id,
    task_type: route.task_type,
    confidence: route.is_unsafe ? 0.91 : 0.82,
    verifier_status: route.is_unsafe ? "blocked_by_unsafe_route_guard" : "schema_valid",
  };
  state.notice = `Test route: ${route.route_id}.`;
}

function downloadContract() {
  const contract = createContract(state.routes);
  const blob = new Blob([JSON.stringify(contract, null, 2)], { type: "application/json" });
  const anchor = document.createElement("a");
  anchor.href = URL.createObjectURL(blob);
  anchor.download = "support_router.agent_contract.json";
  anchor.click();
  URL.revokeObjectURL(anchor.href);
  state.notice = "Contract download started.";
}

function readField(field) {
  return root.querySelector(`[data-field="${field}"]`)?.value || "";
}

function readChecked(field) {
  return Boolean(root.querySelector(`[data-field="${field}"]`)?.checked);
}

function render() {
  const route = parseAppRoute(state.path);
  root.innerHTML = `
    <div class="app-shell">
      ${sidebar()}
      ${topbar(route)}
      <main class="main-panel">${state.apiError ? `<div class="api-banner">${escapeHtml(state.apiError)}</div>` : ""}${page(route)}</main>
    </div>`;
}

function sidebar() {
  const project = state.selectedProject;
  const steps = workflowSteps(project, state.path, Boolean(approvedDataset()), Boolean(state.hardware?.training_enabled), Boolean(completedModelRun()), Boolean(validBenchmark()), Boolean(latestAgentPackage()));
  return `<aside class="sidebar">
    <div class="brand"><div class="brand-mark">MIB</div><div><strong>MIB Studio</strong><span>MicroAgent Inventor Blocks</span></div></div>
    <section class="project-switcher"><small>Project</small><strong>${escapeHtml(project?.name || "No project")}</strong><span>${project ? `${project.routes.length} routes - router` : `${state.projects.length} saved`}</span><div class="switcher-actions"><button class="icon-button" title="Refresh" data-action="refresh">R</button><button class="icon-button" title="Create" data-nav="/projects/new">+</button></div></section>
    <section class="workflow"><div class="nav-section">Workflow</div><div class="workflow-list">${steps
      .map((step, index) => `<button class="workflow-step ${step.state}" ${step.state === "current" ? 'aria-current="step"' : ""} title="${escapeHtml(step.reason || step.label)}" data-nav="${step.state === "locked" ? state.path : step.path}"><span class="step-index">${step.state === "locked" ? "L" : index + 1}</span><span><span class="step-label">${step.label}</span><small>${step.state}</small></span></button>`)
      .join("")}</div></section>
    <nav class="side-nav"><button class="${state.path.startsWith("/projects") && !state.path.includes("define") ? "active" : ""}" ${state.path.startsWith("/projects") && !state.path.includes("define") ? 'aria-current="page"' : ""} data-nav="/projects"><span class="nav-icon">P</span>Projects</button><button class="${state.path.includes("/define") ? "active" : ""}" ${state.path.includes("/define") ? 'aria-current="page"' : ""} data-nav="${project ? `/projects/${project.id}/define` : "/projects/new"}"><span class="nav-icon">D</span>Define</button><button class="${state.path.includes("datasets") ? "active" : ""}" ${state.path.includes("datasets") ? 'aria-current="page"' : ""} data-nav="${project ? `/projects/${project.id}/datasets/new` : "/projects/new"}"><span class="nav-icon">E</span>Data</button><button class="${state.path === "/hardware" ? "active" : ""}" ${state.path === "/hardware" ? 'aria-current="page"' : ""} data-nav="/hardware"><span class="nav-icon">H</span>Hardware</button><button class="${state.path.startsWith("/settings") ? "active" : ""}" ${state.path.startsWith("/settings") ? 'aria-current="page"' : ""} data-nav="/settings"><span class="nav-icon">S</span>Settings</button></nav>
  </aside>`;
}

function topbar(route) {
  const teacherConnected = state.credentials.some((item) => !item.is_revoked);
  return `<header class="topbar"><div class="command-bar">cmd ${breadcrumb(route)} <code>Ctrl+K</code></div><div class="connection-row"><span class="top-chip ${state.online ? "ok" : "bad"}">${state.online ? "local daemon" : "offline"}</span><span class="top-chip ${teacherConnected ? "ok" : ""}">${teacherConnected ? "teacher keychain" : "teacher setup"}</span><span class="top-chip mono">${escapeHtml((state.bootstrap?.baseUrl || "").replace("http://", ""))}</span></div><button class="top-chip clickable gate-${String(state.hardware?.capability_gate || "unknown").toLowerCase()}" data-nav="/hardware">${state.hardware?.capability_gate || "unknown"} - ${state.hardware?.backend_recommendation || "scan"}</button><button class="top-chip clickable" ${state.lastJob ? `data-nav="/jobs/${state.lastJob.job_id}"` : ""}>${state.lastJob ? state.lastJob.status : "no jobs"}</button></header>`;
}

function page(route) {
  if (route.name === "projects") return projectsPage();
  if (route.name === "projectNew") return createProjectPage();
  if (route.name === "projectDashboard") return dashboardPage();
  if (route.name === "projectDefine") return definePage();
  if (route.name === "datasetNew") return examplesPage();
  if (route.name === "datasetDetail") return datasetPage();
  if (route.name === "projectTraining") return trainingPage();
  if (route.name === "projectBenchmark") return benchmarkPage();
  if (route.name === "projectPackage") return packagePage();
  if (route.name === "hardware") return hardwarePage();
  if (route.name === "job") return jobPage(route.jobId);
  if (route.name === "settings") return settingsPage();
  if (route.name === "teacherSettings") return teacherSettingsPage();
  return lockedPage(route.path || "Teacher settings", "This route is present in the M1 shell and unlocks in a later milestone.");
}

function projectsPage() {
  const body = state.loading
    ? statePanel("loading", "Loading projects", "Reading project rows from the local daemon.")
    : state.projects.length === 0
      ? statePanel("empty", "No projects yet", "Start with a support-router project, then define routes and build the first 20 examples.", `<button class="button" data-action="refresh">Retry</button>`)
      : `<div class="item-grid">${state.projects.map((project) => `<button class="project-row" data-nav="/projects/${project.id}"><span><strong>${escapeHtml(project.name)}</strong><small>${escapeHtml(project.preset_id)}</small></span><span class="pill blue">${project.routes.length} routes</span></button>`).join("")}</div>`;
  return pageShell("Projects", "Router projects", "Create or resume a local route-contract project.", `<button class="button primary" data-nav="/projects/new">+ New project</button>`, body);
}

function createProjectPage() {
  const checks = validateRoutes(initialRoutes);
  const disabled = checks.every((check) => check.ok) ? "" : "disabled";
  return pageShell("Project wizard", "Create route contract project", "M1 projects start from a locked router preset and validated route labels.", `<button class="button primary" data-action="create-project" ${disabled}>Create</button>`, `<div class="two-column"><section class="surface"><label class="field"><span>Project name</span><input data-field="project-name" value="${escapeHtml(state.projectName || "support-router")}"></label></section><section class="surface"><h2>Validation</h2>${checksHtml(checks)}</section></div>`);
}

function dashboardPage() {
  const project = state.selectedProject;
  return pageShell("Workbench", project?.name || "Project dashboard", "Restart-safe summary for the route contract, examples, hardware preflight, and later locked workflow steps.", `<button class="button" data-action="refresh">Refresh</button>`, `<div class="metric-grid">${metric("route contract", `${project?.routes.length || 0} routes`, "ok")}${metric("datasets", `${state.datasets.length} saved`, state.datasets.length ? "ok" : "warn")}${metric("train runs", `${state.modelRuns.length} queued`, state.modelRuns.length ? "ok" : "blue")}${metric("benchmarks", `${state.benchmarks.length} saved`, state.benchmarks.length ? "ok" : "blue")}${metric("packages", `${state.agentPackages.length} built`, state.agentPackages.length ? "ok" : "blue")}</div><div class="action-grid"><button class="action-tile" data-nav="/projects/${project?.id}/define"><strong>Define routes</strong><span>Open the v6 route contract builder.</span></button><button class="action-tile" data-nav="/projects/${project?.id}/datasets/new"><strong>Build examples</strong><span>Create the first approved-ready dataset.</span></button><button class="action-tile" data-nav="/projects/${project?.id}/training"><strong>Train</strong><span>Submit a LoRA job after dataset approval and Hardware Doctor.</span></button><button class="action-tile" data-nav="/projects/${project?.id}/benchmarks/new"><strong>AgentBench</strong><span>Compare the completed small agent against baselines.</span></button><button class="action-tile" data-nav="/projects/${project?.id}/packages"><strong>Package</strong><span>Build an Agent Package and verify it in Playground.</span></button></div>`);
}

function definePage() {
  const checks = validateRoutes(state.routes);
  return routeContractPage({ state, checks, pageShell, noticeHtml: notice(), checksHtml, escapeHtml });
}

function examplesPage() {
  const valid = state.examples.filter((item) => typeof item.input.text === "string" && typeof item.output.route === "string").length;
  return pageShell("Data", "Example grid", "Build a persisted JSONL dataset from at least 20 schema-valid user examples.", `<button class="button primary" data-action="build-dataset" ${valid >= 20 ? "" : "disabled"}>Build dataset</button>`, `<div class="split-toolbar"><span class="pill ${valid >= 20 ? "ok" : "warn"}">${valid}/20 valid</span></div>${examplesTable(state.examples)}`);
}

function datasetPage() {
  const dataset = state.dataset;
  const rows = dataset?.examples || [];
  const approved = rows.filter((example) => example.approved).length;
  const actions = `<button class="button primary" data-action="approve-dataset" ${rows.length >= 20 && dataset?.status !== "APPROVED" ? "" : "disabled"}>Approve 20</button><button class="button" data-action="preview-teacher-packet" ${approved >= 20 ? "" : "disabled"}>Preview teacher packet</button>`;
  return pageShell("Dataset", "Dataset build result", "Review persisted examples, validation status, hash, and approval readiness.", actions, `${notice()}<div class="metric-grid">${metric("status", dataset?.status || "loading", "blue")}${metric("approved", `${approved}/${rows.length}`, approved >= 20 ? "ok" : "warn")}${metric("sha256", (dataset?.sha256 || "pending").slice(0, 10), "blue")}</div>${teacherPacketPanel()}${dataset ? examplesTable(rows.map((example) => ({ input: example.input, output: example.output, source: example.source }))) : ""}`);
}

function hardwarePage() {
  const profile = state.hardware;
  return pageShell("Hardware", "Hardware Doctor", "Run a local dry-run scan and gate training access with G0, G1, or G2 hardware status.", `<button class="button" data-action="refresh">Refresh</button><button class="button primary" data-action="scan-hardware">Run dry-run</button>`, `${notice()}<div class="metric-grid">${metric("gate", profile?.capability_gate || "unknown", profile?.training_enabled ? "ok" : "warn")}${metric("backend", profile?.backend_recommendation || "scan required", "blue")}${metric("memory", profile ? `${profile.vram_gb || profile.unified_ram_gb || profile.ram_gb}GB` : "unknown", "ok")}</div><section class="surface"><h2>Training preflight</h2>${profile ? `<p>${escapeHtml(profile.training_disabled_reason_message)}</p><button class="button primary" ${profile.training_enabled && state.selectedProject ? `data-nav="/projects/${state.selectedProject.id}/training"` : "disabled"}>Open Train</button>` : statePanel("empty", "No scan yet", "Run a dry-run scan to create the first HardwareProfile.")}</section>`);
}

function trainingPage() {
  const dataset = approvedDataset();
  const hardwareReady = Boolean(state.hardware?.training_enabled);
  const canStart = Boolean(state.selectedProject && dataset && hardwareReady);
  const backend = trainingBackend();
  const action = `<button class="button primary" data-action="start-train" ${canStart ? "" : "disabled"}>Start train</button>`;
  const gatePanel = `<div class="metric-grid">${metric("dataset", dataset?.id || "approval required", dataset ? "ok" : "warn")}${metric("hardware", state.hardware?.capability_gate || "scan required", hardwareReady ? "ok" : "warn")}${metric("backend", hardwareReady ? backend : "locked", hardwareReady ? "blue" : "warn")}${metric("model runs", String(state.modelRuns.length), state.modelRuns.length ? "ok" : "blue")}</div>`;
  const request = {
    type: "train",
    params: {
      preset_id: state.selectedProject?.preset_id || "router.basic.v1",
      dataset_id: dataset?.id || null,
      base_model: "google/gemma-2b-it",
      backend,
      training_preset: "balanced",
      seed: 123,
    },
  };
  return pageShell(
    "Train",
    "Train workflow",
    "Submit a queued LoRA training job through the local daemon after dataset approval and Hardware Doctor readiness.",
    action,
    `${notice()}${gatePanel}<div class="two-column"><section class="surface"><h2>Submission contract</h2><pre class="codebox">${escapeHtml(JSON.stringify(request, null, 2))}</pre></section><section class="surface"><h2>Gate status</h2><div class="compact-list"><div class="check-line"><span class="check ${dataset ? "ok" : "bad"}">${dataset ? "ok" : "!"}</span>Approved dataset</div><div class="check-line"><span class="check ${hardwareReady ? "ok" : "bad"}">${hardwareReady ? "ok" : "!"}</span>${escapeHtml(state.hardware?.training_disabled_reason_message || "Hardware Doctor scan required.")}</div></div></section></div>${modelRunsHtml()}`,
  );
}

function modelRunsHtml() {
  if (!state.modelRuns.length) return statePanel("empty", "No model runs yet", "Start train to create the first queued model run.");
  return `<div class="table-surface"><table><thead><tr><th>Model run</th><th>Status</th><th>Backend</th><th>Seed</th><th>Adapter</th></tr></thead><tbody>${state.modelRuns
    .map((run) => `<tr><td class="mono">${escapeHtml(run.id)}</td><td><span class="pill ${run.status === "SUCCEEDED" ? "ok" : "blue"}">${escapeHtml(run.status)}</span></td><td>${escapeHtml(run.backend)} / ${escapeHtml(run.method)}</td><td>${escapeHtml(run.seed)}</td><td>${escapeHtml(run.adapter_path || "pending")}</td></tr>`)
    .join("")}</tbody></table></div>`;
}

function benchmarkPage() {
  const modelRun = completedModelRun();
  const evalSet = benchmarkEvalSet();
  const credential = teacherCredential();
  const latest = latestBenchmark();
  const canRun = Boolean(modelRun && evalSet && credential);
  const action = `<button class="button primary" data-action="run-benchmark" ${canRun ? "" : "disabled"}>Run benchmark</button>`;
  const reportStatus = state.benchmarkReport?.hash_status || latest?.hash_status || "MISSING";
  const gatePanel = `<div class="metric-grid">${metric("model run", modelRun?.id || "completed run required", modelRun ? "ok" : "warn")}${metric("eval set", evalSet?.id || "benchmark_gold required", evalSet ? "ok" : "warn")}${metric("teacher", credential ? "credential ready" : "credential required", credential ? "ok" : "warn")}${metric("benchmark report", reportStatus, reportStatus === "VALID" ? "ok" : "blue")}</div>`;
  const request = {
    type: "benchmark",
    params: {
      eval_set_id: evalSet?.id || null,
      targets: modelRun && credential ? benchmarkTargets(modelRun, credential) : [],
      seeds: [42, 123, 456],
    },
  };
  return pageShell(
    "AgentBench",
    "Benchmark workflow",
    "Queue a reproducible benchmark job and read only daemon-generated benchmark report data.",
    action,
    `${notice()}${gatePanel}<div class="two-column"><section class="surface"><h2>Submission contract</h2><pre class="codebox">${escapeHtml(JSON.stringify(request, null, 2))}</pre></section><section class="surface"><h2>Evidence boundary</h2><div class="compact-list"><div class="check-line"><span class="check ok">ok</span>UI never edits benchmark numbers.</div><div class="check-line"><span class="check ${state.benchmarkReport ? "ok" : "bad"}">${state.benchmarkReport ? "ok" : "!"}</span>${state.benchmarkReport ? "benchmark report loaded" : "report appears after worker completion"}</div><div class="check-line"><span class="check bad">!</span>mock-only browser report is not release evidence.</div></div></section></div>${benchmarksHtml()}${benchmarkReportHtml()}`,
  );
}

function benchmarksHtml() {
  if (!state.benchmarks.length) return statePanel("empty", "No benchmarks yet", "Run benchmark after a completed model run and frozen benchmark EvalSet.");
  return `<div class="table-surface"><table><thead><tr><th>Benchmark</th><th>Status</th><th>Hash</th><th>Parity</th><th>Eval set</th></tr></thead><tbody>${state.benchmarks
    .map((item) => `<tr><td class="mono">${escapeHtml(item.id)}</td><td><span class="pill ${item.status === "COMPLETED" ? "ok" : "blue"}">${escapeHtml(item.status)}</span></td><td>${escapeHtml(item.hash_status)}</td><td>${escapeHtml(item.parity_status)}</td><td class="mono">${escapeHtml(item.eval_set_id)}</td></tr>`)
    .join("")}</tbody></table></div>`;
}

function benchmarkReportHtml() {
  const report = state.benchmarkReport?.report;
  if (!report) return "";
  const mockOnly = report.mock_only || report.source === "mock_browser";
  const targets = report.targets || [];
  return `<section class="surface"><div class="split-toolbar"><h2>benchmark report</h2>${mockOnly ? '<span class="pill warn">mock-only</span>' : '<span class="pill ok">daemon report</span>'}</div><div class="metric-grid">${metric("schema", report.schema_version || "unknown", "blue")}${metric("targets", String(targets.length), "ok")}${metric("report sha", (state.benchmarkReport.report_sha256 || "missing").slice(0, 10), state.benchmarkReport.hash_status === "VALID" ? "ok" : "warn")}</div><div class="table-surface"><table><thead><tr><th>Target</th><th>Status</th><th>Route accuracy</th><th>Latency p50</th><th>Cost</th></tr></thead><tbody>${targets
    .map((target) => `<tr><td class="mono">${escapeHtml(target.target_key)}</td><td>${escapeHtml(target.target_status || "COMPLETED")}</td><td>${escapeHtml(metricValue(target, "route_accuracy"))}</td><td>${escapeHtml(metricValue(target, "latency_p50_ms"))}</td><td>${escapeHtml(metricValue(target, "effective_cost_per_task_usd"))}</td></tr>`)
    .join("")}</tbody></table></div></section>`;
}

function metricValue(target, key) {
  const value = target.mean_metrics?.[key] ?? target.metrics?.[key];
  if (value === undefined || value === null) return "not reported";
  return typeof value === "number" ? Number(value).toFixed(key.includes("cost") ? 6 : 3) : String(value);
}

function packagePage() {
  const modelRun = completedModelRun();
  const benchmark = validBenchmark();
  const agentPackage = latestAgentPackage();
  const canBuild = Boolean(modelRun && benchmark);
  const canRun = Boolean(agentPackage);
  const actions = `<button class="button primary" data-action="build-package" ${canBuild ? "" : "disabled"}>Build package</button><button class="button" data-action="run-playground" ${canRun ? "" : "disabled"}>Run playground</button>`;
  const gatePanel = `<div class="metric-grid">${metric("model run", modelRun?.id || "completed run required", modelRun ? "ok" : "warn")}${metric("benchmark", benchmark?.id || "valid report required", benchmark ? "ok" : "warn")}${metric("package", agentPackage?.agent_id || "not built", agentPackage ? "ok" : "blue")}${metric("playground", state.playgroundResult?.verifier_status || "not run", state.playgroundResult?.verifier_status === "PASS" ? "ok" : "blue")}</div>`;
  return pageShell(
    "Package",
    "Package workflow",
    "Build an immutable Agent Package from the completed model run and valid benchmark report, then run local Playground verification.",
    actions,
    `${notice()}${gatePanel}<div class="two-column"><section class="surface"><h2>Package contract</h2>${agentPackage ? `<pre class="codebox">${escapeHtml(agentPackage.contract_yaml)}</pre>` : statePanel("empty", "No package yet", "Build package after a completed model run and valid benchmark report.")}</section><section class="surface"><h2>Playground result</h2>${playgroundResultHtml()}</section></div>${agentPackagesHtml()}`,
  );
}

function playgroundResultHtml() {
  const result = state.playgroundResult;
  if (!result) return statePanel("empty", "No run yet", "Run Playground after package build.");
  return `<div class="metric-grid">${metric("verifier", result.verifier_status, result.verifier_status === "PASS" ? "ok" : "warn")}${metric("fallback", result.fallback_used ? "used" : result.fallback_required ? "required" : "not required", result.fallback_required ? "warn" : "ok")}${metric("audit", result.audit_event_id ? result.audit_event_id.slice(0, 8) : "missing", result.audit_event_id ? "ok" : "warn")}</div><pre class="codebox">${escapeHtml(JSON.stringify(result.output, null, 2))}</pre>`;
}

function agentPackagesHtml() {
  if (!state.agentPackages.length) return "";
  return `<div class="table-surface"><table><thead><tr><th>Agent</th><th>Version</th><th>Contract</th><th>Benchmark</th></tr></thead><tbody>${state.agentPackages
    .map((item) => `<tr><td class="mono">${escapeHtml(item.agent_id)}</td><td>${escapeHtml(item.contract_version)}</td><td class="mono">${escapeHtml(item.contract_sha256.slice(0, 12))}</td><td class="mono">${escapeHtml(item.benchmark_id)}</td></tr>`)
    .join("")}</tbody></table></div>`;
}

function jobPage(jobId) {
  const snapshot = state.lastJob?.job_id === jobId ? state.lastJob : null;
  return pageShell("Jobs", "Job monitor", "Poll job state and keep an event-gap banner visible when the stream is incomplete or locked.", `<button class="button" data-action="poll-job">Poll</button>`, `${notice()}<div class="metric-grid">${metric("job", jobId.slice(0, 8), "blue")}${metric("status", snapshot?.status || "unknown", snapshot?.status === "SUCCEEDED" ? "ok" : "warn")}${metric("type", snapshot?.type || "locked", "blue")}</div><section class="surface"><h2>Latest events</h2><pre class="codebox">${escapeHtml(JSON.stringify({ job_id: jobId, status: snapshot?.status || "EVENT_GAP", poll_fallback: true }, null, 2))}</pre></section>`);
}

function settingsPage() {
  const connected = state.credentials.some((item) => !item.is_revoked);
  return pageShell("Settings", "Runtime settings", "Configure the local daemon and BYO teacher provider without echoing secrets.", "", `<div class="action-grid"><button class="action-tile"><strong>Local daemon</strong><span>${escapeHtml(state.bootstrap?.baseUrl || "bootstrap pending")}</span></button><button class="action-tile" data-nav="/settings/teacher"><strong>Teacher provider</strong><span>${connected ? "Connected via OS keychain." : "BYO key required before generation."}</span></button></div>${statePanel(connected ? "success" : "empty", connected ? "Credential connected" : "Credential missing", connected ? "Keys are stored in OS keychain and never returned by the daemon." : "Save an OpenAI-compatible key before approving external teacher generation.")}`);
}

function teacherSettingsPage() {
  const credential = state.credentials.find((item) => item.provider === "openai_compatible" && !item.is_revoked) || state.credentials.find((item) => !item.is_revoked);
  return pageShell("Settings", "Teacher provider", "BYO OpenAI-compatible key storage uses OS keychain; the local daemon never echoes the key.", `<button class="button" data-action="delete-credential" ${credential ? "" : "disabled"}>Revoke</button><button class="button primary" data-action="save-credential">Save key</button>`, `${notice()}<div class="two-column"><section class="surface"><label class="field"><span>Base URL</span><input data-field="credential-base-url" value="${escapeHtml(state.credentialBaseUrl || credential?.base_url_origin || "https://api.openai.com/v1")}"></label><label class="field"><span>API key</span><input type="password" autocomplete="off" data-field="credential-api-key" value=""></label></section><section class="surface"><h2>Connection</h2>${credential ? `<div class="compact-list"><div class="check-line"><span class="check ok">ok</span>${escapeHtml(credential.provider)} · ${escapeHtml(credential.base_url_origin)}</div><div class="check-line"><span class="check ok">ok</span>${escapeHtml(credential.keychain_ref)}</div></div>` : statePanel("empty", "No teacher key", "Credential create/update returns only keychain metadata.")}</section></div>`);
}

function teacherPacketPanel() {
  const packet = state.teacherPacket;
  if (!packet) {
    return `<section class="surface"><h2>Teacher Packet Preview</h2><label class="field"><span>Generation instruction</span><textarea data-field="teacher-instruction">${escapeHtml(state.teacherInstruction)}</textarea></label><p>Preview sends only rule schema, output schema, anonymized approved examples, and this instruction after user approval.</p></section>`;
  }
  const examples = packet.packet_preview.anonymized_examples || [];
  return `<section class="surface teacher-preview"><div class="split-toolbar"><h2>Teacher Packet Preview</h2><button class="button primary" data-action="approve-teacher-packet" ${packet.approved_at ? "disabled" : ""}>Approve packet</button></div><div class="metric-grid">${metric("examples", String(examples.length), "ok")}${metric("masked", String(packet.pii_summary.masked_count || 0), "ok")}${metric("sha256", packet.packet_sha256.slice(0, 10), "blue")}</div><div class="two-column"><div><h3>Sent</h3><ul>${(packet.pii_summary.transmitted || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div><div><h3>Not sent</h3><ul>${(packet.pii_summary.not_transmitted || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div></div><pre class="codebox">${escapeHtml(JSON.stringify(packet.packet_preview, null, 2))}</pre></section>`;
}

function lockedPage(title, reason) {
  return pageShell("Locked", title, "This route is present in the M1 shell but waits for a later milestone.", "", statePanel("locked", "Milestone locked", reason));
}

function pageShell(eyebrow, title, description, actions, body) {
  return `<section class="page"><div class="page-header"><div><div class="eyebrow">${eyebrow}</div><h1>${escapeHtml(title)}</h1><p>${escapeHtml(description)}</p></div><div class="page-actions">${actions || ""}</div></div>${body}</section>`;
}

function examplesTable(examples) {
  return `<div class="table-surface"><table><thead><tr><th>#</th><th>Input</th><th>Expected route</th><th>Status</th></tr></thead><tbody>${examples.map((example, index) => `<tr><td>${index + 1}</td><td>${escapeHtml(String(example.input.text || ""))}</td><td class="mono">${escapeHtml(String(example.output.route || ""))}</td><td><span class="pill ok">schema-valid</span></td></tr>`).join("")}</tbody></table></div>`;
}

function checksHtml(checks) {
  return `<div class="checks">${checks.map((check) => `<div class="check-line"><span class="check ${check.ok ? "ok" : "bad"}">${check.ok ? "ok" : "!"}</span>${escapeHtml(check.message)}</div>`).join("")}</div>`;
}

function metric(label, value, tone) {
  return `<div class="metric"><span>${label}</span><strong>${escapeHtml(value)}</strong><em class="pill ${tone}">${tone}</em></div>`;
}

function statePanel(stateName, title, body, action = "") {
  const role = stateName === "api_error" ? "alert" : "status";
  return `<section class="state-panel ${stateName}" role="${role}" aria-live="polite"><div><strong>${escapeHtml(title)}</strong><p>${escapeHtml(body)}</p></div>${action}</section>`;
}

function notice() {
  return state.notice ? statePanel("success", "Status", state.notice) : "";
}

function breadcrumb(route) {
  if (route.name === "projects") return "projects";
  if (route.name === "projectNew") return "projects / new";
  if (route.name === "projectDashboard") return "projects / dashboard";
  if (route.name === "projectDefine") return "projects / define / Route contract";
  if (route.name === "datasetNew") return "projects / datasets / new";
  if (route.name === "datasetDetail") return "datasets / detail";
  if (route.name === "projectTraining") return "projects / training";
  if (route.name === "projectBenchmark") return "projects / benchmarks / AgentBench";
  if (route.name === "projectPackage") return "projects / package / Playground";
  if (route.name === "hardware") return "hardware / doctor";
  if (route.name === "job") return "jobs / monitor";
  return "settings";
}

function normalizePath(pathname) {
  return pathname === "/" ? "/projects" : pathname;
}

function errorText(error) {
  if (error instanceof ApiClientError) return `${error.payload.error_code}: ${error.payload.message}`;
  return error instanceof Error ? error.message : "Unknown error";
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[char]);
}
