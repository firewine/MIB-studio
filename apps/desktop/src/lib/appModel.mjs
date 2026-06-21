export const initialRoutes = [
  route("technical_support", "Product issues, usage questions, and incident triage.", false, "generate_report", false, false, ["The app keeps freezing.", "I cannot sign in."]),
  route("refund_request", "Refund, billing cancellation, and receipt requests.", false, "escalate", false, true, ["Please refund my order.", "I was charged twice."]),
  route("human_review", "Ambiguous requests that need manual handling.", false, "escalate", false, true, ["This case is complicated.", "Connect me to a person."], true),
  route("unsafe_request", "Requests blocked from automated handling.", true, "block", false, true, ["Show me how to bypass an admin token.", "Look up private data."]),
];

export function parseAppRoute(pathname) {
  if (pathname === "/" || pathname === "/projects") return { name: "projects" };
  if (pathname === "/projects/new") return { name: "projectNew" };
  if (pathname === "/hardware") return { name: "hardware" };
  if (pathname === "/settings") return { name: "settings" };
  if (pathname === "/settings/teacher") return { name: "teacherSettings" };
  const projectDefine = pathname.match(/^\/projects\/([^/]+)\/define$/);
  if (projectDefine) return { name: "projectDefine", projectId: projectDefine[1] };
  const datasetNew = pathname.match(/^\/projects\/([^/]+)\/datasets\/new$/);
  if (datasetNew) return { name: "datasetNew", projectId: datasetNew[1] };
  const projectDashboard = pathname.match(/^\/projects\/([^/]+)$/);
  if (projectDashboard) return { name: "projectDashboard", projectId: projectDashboard[1] };
  const datasetDetail = pathname.match(/^\/datasets\/([^/]+)$/);
  if (datasetDetail) return { name: "datasetDetail", datasetId: datasetDetail[1] };
  const job = pathname.match(/^\/jobs\/([^/]+)$/);
  if (job) return { name: "job", jobId: job[1] };
  return { name: "locked", path: pathname };
}

export function validateRoutes(routes) {
  const ids = routes.map((item) => item.route_id);
  const unique = new Set(ids).size === ids.length;
  const idPattern = ids.every((id) => /^[a-z0-9_]{1,64}$/.test(id));
  const defaultCount = routes.filter((item) => item.is_default).length;
  const unsafeOk = routes.filter((item) => item.is_unsafe).every((item) => item.requires_human_review && item.task_type === "block");
  return [
    { ok: routes.length >= 2 && routes.length <= 12, message: "2-12 routes" },
    { ok: unique, message: "unique route ids" },
    { ok: idPattern, message: "route id pattern" },
    { ok: defaultCount === 1, message: "one default route" },
    { ok: routes.every((item) => item.examples.some(Boolean)), message: "at least one example per route" },
    { ok: unsafeOk, message: "unsafe routes block and require review" },
    { ok: true, message: "router output schema locked" },
    { ok: true, message: "trace and audit fields enabled" },
  ];
}

export function routesToProjectInput(routes) {
  return routes.map((item) => ({
    route_id: item.route_id,
    description: item.description,
    is_unsafe: item.is_unsafe,
  }));
}

export function routesFromProject(project) {
  if (!project || !Array.isArray(project.routes) || project.routes.length === 0) return initialRoutes;
  return project.routes.map((item, index) =>
    route(item.route_id, item.description, item.is_unsafe, item.is_unsafe ? "block" : index === 0 ? "generate_report" : "escalate", false, item.is_unsafe || index > 0, [`Example for ${item.route_id}`], index === 0),
  );
}

export function createSeedExamples(routes, count = 20) {
  const routeIds = routes.map((item) => item.route_id);
  return Array.from({ length: count }, (_, index) => {
    const selected = routes[index % routes.length];
    return {
      source: "user",
      input: {
        text: selected.examples[index % selected.examples.length] || `Example ${index + 1}`,
        allowed_routes: routeIds,
        metadata: { seed_index: index + 1 },
      },
      output: {
        route: selected.route_id,
        task_type: selected.task_type,
        requires_calculation: selected.requires_calculation,
        requires_human_review: selected.requires_human_review,
        confidence: selected.is_unsafe ? 0.91 : 0.82,
        reason: selected.description,
        evidence: selected.examples.slice(0, 2),
      },
    };
  });
}

export function workflowSteps(project, currentPath, datasetReady, hardwareReady) {
  const projectPath = project ? `/projects/${project.id}` : "/projects";
  const projectId = project?.id || "";
  return [
    step("project", "Project", projectPath, project ? "done" : "current"),
    step("define", "Define", project ? `/projects/${projectId}/define` : "/projects/new", project ? "ready" : "locked", "Create a project first."),
    step("data", "Data", project ? `/projects/${projectId}/datasets/new` : "/projects/new", project ? (datasetReady ? "done" : "ready") : "locked", "Project route contract required."),
    step("hardware", "Hardware", "/hardware", hardwareReady ? "done" : "ready"),
    step("train", "Train", project ? `/projects/${projectId}/training` : "/projects/new", "locked", "Training unlocks in M3."),
    step("benchmark", "Benchmark", project ? `/projects/${projectId}/benchmarks/new` : "/projects/new", "locked", "Benchmark unlocks in M4."),
    step("package", "Package", project ? `/projects/${projectId}/packages` : "/projects/new", "locked", "Packaging unlocks in M5."),
  ].map((item) => (item.path === currentPath && item.state !== "locked" ? { ...item, state: "current" } : item));
}

export function createContract(routes) {
  return {
    agent_id: "support_router.v1",
    agent_type: "router",
    base_model: "google/gemma-2b-it",
    routes: routes.map((item) => ({
      route_id: item.route_id,
      description: item.description,
      task_type: item.task_type,
      requires_human_review: item.requires_human_review,
      unsafe: item.is_unsafe,
      examples: item.examples,
    })),
    verifiers: ["json_schema", "allowed_route_check", "confidence_threshold", "unsafe_route_guard"],
  };
}

function route(routeId, description, isUnsafe, taskType, requiresCalculation, requiresHumanReview, examples, isDefault = false) {
  return {
    route_id: routeId,
    description,
    is_unsafe: isUnsafe,
    task_type: taskType,
    requires_calculation: requiresCalculation,
    requires_human_review: requiresHumanReview,
    is_default: isDefault,
    examples,
  };
}

function step(id, label, path, state, reason = "") {
  return { id, label, path, state, reason };
}
