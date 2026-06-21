import {
  createContract,
  createSeedExamples,
  initialRoutes,
  parseAppRoute,
  routesFromProject,
  routesToProjectInput,
  validateRoutes,
  workflowSteps,
} from "./lib/appModel.mjs";
import { ApiClientError, createApiClient, idempotencyKey, resolveBootstrap } from "./lib/apiClient.mjs";

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
  routes: [...initialRoutes],
  examples: [],
  online: false,
  loading: true,
  apiError: null,
  notice: null,
  selectedRoute: 0,
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
    const [projects, presets, hardware] = await Promise.all([
      state.api.request("listProjects", { params: { include_archived: false } }).catch(() => ({ items: [] })),
      state.api.request("listPresets").catch(() => ({ items: [] })),
      getHardware(),
    ]);
    state.projects = projects.items || [];
    state.presets = presets.items || [];
    state.hardware = hardware;
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
  if (target.dataset.routeIndex) {
    state.selectedRoute = Number(target.dataset.routeIndex);
    return render();
  }
  const action = target.dataset.action;
  if (action === "refresh") await refresh();
  if (action === "create-project") await createProject();
  if (action === "save-routes") await saveRoutes();
  if (action === "build-dataset") await buildDataset();
  if (action === "approve-dataset") await approveDataset();
  if (action === "scan-hardware") await scanHardware();
  if (action === "poll-job") await pollJob();
  render();
}

function onInput(event) {
  const field = event.target.dataset.field;
  if (!field) return;
  if (field === "project-name") state.projectName = event.target.value;
  const selected = state.routes[state.selectedRoute];
  if (!selected) return;
  if (field === "route-id") selected.route_id = event.target.value;
  if (field === "route-desc") selected.description = event.target.value;
  if (field === "unsafe") selected.is_unsafe = event.target.checked;
  if (field === "review") selected.requires_human_review = event.target.checked;
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
  await refresh();
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
      .map((step, index) => `<button class="workflow-step ${step.state}" title="${escapeHtml(step.reason || step.label)}" data-nav="${step.state === "locked" ? state.path : step.path}"><span class="step-index">${step.state === "locked" ? "L" : index + 1}</span><span><span class="step-label">${step.label}</span><small>${step.state}</small></span></button>`)
      .join("")}</div></section>
    <nav class="side-nav"><button class="${state.path.startsWith("/projects") && !state.path.includes("define") ? "active" : ""}" data-nav="/projects"><span class="nav-icon">P</span>Projects</button><button class="${state.path.includes("/define") ? "active" : ""}" data-nav="${project ? `/projects/${project.id}/define` : "/projects/new"}"><span class="nav-icon">D</span>Define</button><button class="${state.path.includes("datasets") ? "active" : ""}" data-nav="${project ? `/projects/${project.id}/datasets/new` : "/projects/new"}"><span class="nav-icon">E</span>Data</button><button class="${state.path === "/hardware" ? "active" : ""}" data-nav="/hardware"><span class="nav-icon">H</span>Hardware</button><button class="${state.path.startsWith("/settings") ? "active" : ""}" data-nav="/settings"><span class="nav-icon">S</span>Settings</button></nav>
  </aside>`;
}

function topbar(route) {
  return `<header class="topbar"><div class="command-bar">cmd ${breadcrumb(route)} <code>Ctrl+K</code></div><div class="connection-row"><span class="top-chip ${state.online ? "ok" : "bad"}">${state.online ? "local daemon" : "offline"}</span><span class="top-chip">teacher locked</span><span class="top-chip mono">${escapeHtml((state.bootstrap?.baseUrl || "").replace("http://", ""))}</span></div><button class="top-chip clickable gate-${String(state.hardware?.capability_gate || "unknown").toLowerCase()}" data-nav="/hardware">${state.hardware?.capability_gate || "unknown"} - ${state.hardware?.backend_recommendation || "scan"}</button><button class="top-chip clickable" ${state.lastJob ? `data-nav="/jobs/${state.lastJob.job_id}"` : ""}>${state.lastJob ? state.lastJob.status : "no jobs"}</button></header>`;
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
  const selected = state.routes[state.selectedRoute] || state.routes[0];
  const contract = createContract(state.routes);
  return pageShell("Define", "Route contract", "Assemble input, route, guard, output, and audit blocks into a fixed router contract.", `<button class="button" data-action="save-routes">Save</button>`, `${notice()}<div class="define-grid"><section class="toolbox"><h2>Toolbox</h2>${["when input arrives", "normalize text", "route among labels", "if unsafe request", "if confidence below", "emit JSON"].map((block) => `<button class="palette-block">${block}<small>route contract block</small></button>`).join("")}</section><section class="canvas-surface"><div class="canvas-toolbar"><span class="pill blue">${state.routes.length} routes</span><button class="button">Test</button></div><div class="block-stack"><div class="iblock input">when input.text arrives</div><div class="iblock input">normalize text with pii_mask</div><div class="iblock route">route among ${state.routes.length} labels using examples</div><div class="nested-blocks"><div class="iblock guard">if route has unsafe flag then block</div><div class="iblock logic">if confidence &lt; 0.65 then human_review</div></div><div class="iblock eval">emit JSON route - task_type - confidence</div><div class="iblock data">log trace with contract_version</div></div></section><aside class="inspector"><h2>Inspector</h2><div class="route-chips">${state.routes.map((item, index) => `<button class="${index === state.selectedRoute ? "active" : ""}" data-route-index="${index}"><strong>${escapeHtml(item.route_id)}</strong><small>${escapeHtml(item.description)}</small></button>`).join("")}</div>${routeForm(selected)}<h3>Checks</h3>${checksHtml(checks)}<h3>Contract</h3><pre class="codebox">${escapeHtml(JSON.stringify(contract, null, 2))}</pre><button class="button" data-nav="/projects/${state.selectedProject?.id}/datasets/new">Build examples from contract</button></aside></div>`);
}

function examplesPage() {
  const valid = state.examples.filter((item) => typeof item.input.text === "string" && typeof item.output.route === "string").length;
  return pageShell("Data", "Example grid", "Build a persisted JSONL dataset from at least 20 schema-valid user examples.", `<button class="button primary" data-action="build-dataset" ${valid >= 20 ? "" : "disabled"}>Build dataset</button>`, `<div class="split-toolbar"><span class="pill ${valid >= 20 ? "ok" : "warn"}">${valid}/20 valid</span></div>${examplesTable(state.examples)}`);
}

function datasetPage() {
  const dataset = state.dataset;
  const rows = dataset?.examples || [];
  return pageShell("Dataset", "Dataset build result", "Review persisted examples, validation status, hash, and approval readiness.", `<button class="button primary" data-action="approve-dataset" ${rows.length >= 20 ? "" : "disabled"}>Approve 20</button>`, `${notice()}<div class="metric-grid">${metric("status", dataset?.status || "loading", "blue")}${metric("samples", String(dataset?.sample_count || 0), "ok")}${metric("sha256", (dataset?.sha256 || "pending").slice(0, 10), "blue")}</div>${dataset ? examplesTable(rows.map((example) => ({ input: example.input, output: example.output, source: example.source }))) : ""}`);
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
  return pageShell("Settings", "Runtime settings", "M1 exposes local daemon status. Teacher credentials are rendered as locked until M2.", "", `<div class="action-grid"><button class="action-tile"><strong>Local daemon</strong><span>${escapeHtml(state.bootstrap?.baseUrl || "bootstrap pending")}</span></button><button class="action-tile" data-nav="/settings/teacher"><strong>Teacher provider</strong><span>Locked until credential storage lands in M2.</span></button></div>${statePanel("locked", "Credentials locked", "Keys are never echoed in the M1 shell; credential storage starts in M2.")}`);
}

function lockedPage(title, reason) {
  return pageShell("Locked", title, "This route is present in the M1 shell but waits for a later milestone.", "", statePanel("locked", "Milestone locked", reason));
}

function pageShell(eyebrow, title, description, actions, body) {
  return `<section class="page"><div class="page-header"><div><div class="eyebrow">${eyebrow}</div><h1>${escapeHtml(title)}</h1><p>${escapeHtml(description)}</p></div><div class="page-actions">${actions || ""}</div></div>${body}</section>`;
}

function routeForm(route) {
  return `<div class="form-grid"><label class="field"><span>Route id</span><input data-field="route-id" value="${escapeHtml(route.route_id)}"></label><label class="field"><span>Description</span><input data-field="route-desc" value="${escapeHtml(route.description)}"></label><label class="check-field"><input type="checkbox" data-field="unsafe" ${route.is_unsafe ? "checked" : ""}> unsafe route</label><label class="check-field"><input type="checkbox" data-field="review" ${route.requires_human_review ? "checked" : ""}> human review</label></div>`;
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
  return `<section class="state-panel ${stateName}"><div><strong>${escapeHtml(title)}</strong><p>${escapeHtml(body)}</p></div>${action}</section>`;
}

function notice() {
  return state.notice ? statePanel("success", "Status", state.notice) : "";
}

function breadcrumb(route) {
  if (route.name === "projects") return "projects";
  if (route.name === "projectNew") return "projects / new";
  if (route.name === "projectDashboard") return "projects / dashboard";
  if (route.name === "projectDefine") return "projects / define / route-contract";
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
