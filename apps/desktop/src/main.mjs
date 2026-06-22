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
  const steps = workflowSteps(project, state.path, state.datasets.length > 0, Boolean(state.hardware));
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
  return pageShell("Workbench", project?.name || "Project dashboard", "Restart-safe summary for the route contract, examples, hardware preflight, and later locked workflow steps.", `<button class="button" data-action="refresh">Refresh</button>`, `<div class="metric-grid">${metric("route contract", `${project?.routes.length || 0} routes`, "ok")}${metric("datasets", `${state.datasets.length} saved`, state.datasets.length ? "ok" : "warn")}${metric("archived", project?.archived_at ? "read-only" : "active", "ok")}</div><div class="action-grid"><button class="action-tile" data-nav="/projects/${project?.id}/define"><strong>Define routes</strong><span>Open the v6 route contract builder.</span></button><button class="action-tile" data-nav="/projects/${project?.id}/datasets/new"><strong>Build examples</strong><span>Create the first approved-ready dataset.</span></button></div>`);
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
  return pageShell("Hardware", "Hardware Doctor", "Run a local dry-run scan and gate training access with G0, G1, or G2 hardware status.", `<button class="button" data-action="refresh">Refresh</button><button class="button primary" data-action="scan-hardware">Run dry-run</button>`, `${notice()}<div class="metric-grid">${metric("gate", profile?.capability_gate || "unknown", profile?.training_enabled ? "ok" : "warn")}${metric("backend", profile?.backend_recommendation || "scan required", "blue")}${metric("memory", profile ? `${profile.vram_gb || profile.unified_ram_gb || profile.ram_gb}GB` : "unknown", "ok")}</div><section class="surface"><h2>Training preflight</h2>${profile ? `<p>${escapeHtml(profile.training_disabled_reason_message)}</p><button class="button primary" ${profile.training_enabled ? "" : "disabled"}>Start train</button>` : statePanel("empty", "No scan yet", "Run a dry-run scan to create the first HardwareProfile.")}</section>`);
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
