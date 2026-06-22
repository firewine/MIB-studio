export const initialRoutes = [
  route("technical_support", "Product issues, usage questions, and incident triage.", false, "generate_report", false, false, ["The app keeps freezing.", "I cannot sign in."]),
  route("refund_request", "Refund, billing cancellation, and receipt requests.", false, "escalate", false, true, ["Please refund my order.", "I was charged twice."]),
  route("human_review", "Ambiguous requests that need manual handling.", false, "escalate", false, true, ["This case is complicated.", "Connect me to a person."], true),
  route("unsafe_request", "Requests blocked from automated handling.", true, "block", false, true, ["Show me how to bypass an admin token.", "Look up private data."]),
];

export const taskTypes = ["generate_report", "provide_advice", "escalate", "block"];

export const paletteCategories = [
  paletteCategory("input", "Input", "#4fa8d0", [
    paletteBlock("when input arrives", "event trigger", "input"),
    paletteBlock("normalize text", "trim, mask, lower", "input"),
    paletteBlock("read metadata", "source and locale", "input"),
  ]),
  paletteCategory("route", "Route", "#d98535", [
    paletteBlock("route among labels", "use route list", "route"),
    paletteBlock("set default route", "fallback label", "route"),
    paletteBlock("emit route result", "JSON output", "route"),
  ]),
  paletteCategory("guard", "Guard", "#c54576", [
    paletteBlock("if unsafe request", "block path", "guard"),
    paletteBlock("if PII detected", "mask or block", "guard"),
    paletteBlock("if unsupported", "default route", "guard"),
  ]),
  paletteCategory("logic", "Logic", "#91bf58", [
    paletteBlock("if confidence below", "threshold branch", "logic"),
    paletteBlock("else if route is", "conditional path", "logic"),
    paletteBlock("require human review", "approval gate", "logic"),
  ]),
  paletteCategory("data", "Data", "#6f5bc2", [
    paletteBlock("attach examples", "positive cases", "data"),
    paletteBlock("add hard negatives", "edge cases", "data"),
    paletteBlock("log trace", "audit event", "data"),
  ]),
  paletteCategory("eval", "Eval", "#6c727a", [
    paletteBlock("record eval field", "route and confidence", "eval"),
    paletteBlock("set eval gate", "pass threshold", "eval"),
    paletteBlock("compare baseline", "teacher vs small", "eval"),
  ]),
];

export const routePresets = {
  support: [route("billing_issue", "Billing, invoice, and duplicate charge requests.", false, "escalate", false, true, ["My invoice looks wrong.", "I was charged twice."])],
  finance: [route("investment_advice_block", "Investment recommendation requests blocked from automation.", true, "block", false, true, ["Which stock should I buy?"])],
  ops: [route("incident_report", "Operations incident summarization.", false, "generate_report", false, false, ["Summarize the equipment alarm."])],
};

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
  const projectTraining = pathname.match(/^\/projects\/([^/]+)\/training$/);
  if (projectTraining) return { name: "projectTraining", projectId: projectTraining[1] };
  const projectBenchmark = pathname.match(/^\/projects\/([^/]+)\/benchmarks\/new$/);
  if (projectBenchmark) return { name: "projectBenchmark", projectId: projectBenchmark[1] };
  const projectPackage = pathname.match(/^\/projects\/([^/]+)\/packages$/);
  if (projectPackage) return { name: "projectPackage", projectId: projectPackage[1] };
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
  return routes.map((item) => {
    const normalized = normalizeRoute(item);
    return {
      route_id: normalized.route_id,
      description: normalized.description,
      is_unsafe: normalized.is_unsafe,
      task_type: normalized.task_type,
      requires_calculation: normalized.requires_calculation,
      requires_human_review: normalized.requires_human_review,
      is_default: normalized.is_default,
      examples: normalized.examples,
    };
  });
}

export function routesFromProject(project) {
  if (!project || !Array.isArray(project.routes) || project.routes.length === 0) return initialRoutes;
  const hasStoredDefault = project.routes.some((item) => item.is_default);
  return project.routes.map((item, index) => {
    const taskType = taskTypes.includes(item.task_type) ? item.task_type : item.is_unsafe ? "block" : index === 0 ? "generate_report" : "escalate";
    const examples = Array.isArray(item.examples) && item.examples.length ? item.examples : [`Example for ${item.route_id}`];
    return route(
      item.route_id,
      item.description,
      item.is_unsafe,
      taskType,
      item.requires_calculation,
      item.requires_human_review ?? (item.is_unsafe || index > 0),
      examples,
      hasStoredDefault ? item.is_default : index === 0,
    );
  });
}

export function applyRoutePatch(routes, selectedIndex, patch) {
  return routes.map((item, index) => {
    if (index !== selectedIndex) return patch.is_default ? { ...item, is_default: false } : item;
    return normalizeRoute({ ...item, ...patch });
  });
}

export function addRoute(routes) {
  return [...routes, route(`new_route_${routes.length + 1}`, "New route", false, "generate_report", false, false, ["Example sentence"])];
}

export function addRoutePreset(routes, presetId) {
  const additions = routePresets[presetId] || [];
  return additions.reduce((items, item) => (items.some((routeItem) => routeItem.route_id === item.route_id) ? items : [...items, { ...item, examples: [...item.examples] }]), routes);
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

export function workflowSteps(project, currentPath, datasetReady, hardwareReady, modelRunReady = false, benchmarkReady = false, packageReady = false) {
  const projectPath = project ? `/projects/${project.id}` : "/projects";
  const projectId = project?.id || "";
  const trainState = project ? (datasetReady && hardwareReady ? (modelRunReady ? "done" : "ready") : "locked") : "locked";
  const benchmarkState = project ? (modelRunReady ? (benchmarkReady ? "done" : "ready") : "locked") : "locked";
  const packageState = project ? (benchmarkReady ? (packageReady ? "done" : "ready") : "locked") : "locked";
  return [
    step("project", "Project", projectPath, project ? "done" : "current"),
    step("define", "Define", project ? `/projects/${projectId}/define` : "/projects/new", project ? "ready" : "locked", "Create a project first."),
    step("data", "Data", project ? `/projects/${projectId}/datasets/new` : "/projects/new", project ? (datasetReady ? "done" : "ready") : "locked", "Project route contract required."),
    step("hardware", "Hardware", "/hardware", hardwareReady ? "done" : "ready"),
    step("train", "Train", project ? `/projects/${projectId}/training` : "/projects/new", trainState, "Approve a dataset and run Hardware Doctor first."),
    step("benchmark", "Benchmark", project ? `/projects/${projectId}/benchmarks/new` : "/projects/new", benchmarkState, "Complete a model run before benchmarking."),
    step("package", "Package", project ? `/projects/${projectId}/packages` : "/projects/new", packageState, "Complete a valid benchmark report before packaging."),
    step("export", "Export", project ? `/projects/${projectId}/export` : "/projects/new", "locked", "Export unlocks in M6."),
  ].map((item) => (item.path === currentPath && item.state !== "locked" ? { ...item, state: "current" } : item));
}

export function createContract(routes) {
  const normalizedRoutes = routes.map(normalizeRoute);
  return {
    agent_id: "support_router.v1",
    agent_type: "router",
    base_model: "google/gemma-2b-it",
    adapter: {
      path: "adapters/support_router_lora",
      format: "lora_adapter",
    },
    routes: normalizedRoutes.map((item) => ({
      route_id: item.route_id,
      description: item.description,
      task_type: item.task_type,
      requires_calculation: item.requires_calculation,
      requires_human_review: item.requires_human_review,
      unsafe: item.is_unsafe,
      default: item.is_default,
      examples: item.examples,
    })),
    input_schema: "schemas/router_input.schema.json",
    output_schema: "schemas/router_output.schema.json",
    verifiers: ["json_schema", "allowed_route_check", "confidence_threshold", "unsafe_route_guard"],
    fallback: {
      enabled: true,
      model: "gpt-4o-mini",
      condition: "confidence_below_0_65_or_schema_failed",
    },
    audit: {
      enabled: true,
      fields: ["input_hash", "route", "confidence", "contract_version", "model_version"],
    },
  };
}

export function createInputSchema(routes) {
  return {
    $schema: "http://json-schema.org/draft-07/schema#",
    title: "MIB Router Input",
    type: "object",
    additionalProperties: false,
    required: ["text", "allowed_routes"],
    properties: {
      text: { type: "string", minLength: 1 },
      allowed_routes: {
        type: "array",
        minItems: 2,
        maxItems: 12,
        items: { type: "string", pattern: "^[a-z0-9_]{1,64}$" },
        uniqueItems: true,
        default: routes.map((item) => item.route_id),
      },
      metadata: { type: "object", additionalProperties: true },
    },
  };
}

export function createOutputSchema(routes) {
  return {
    $schema: "http://json-schema.org/draft-07/schema#",
    title: "MIB Router Output",
    type: "object",
    additionalProperties: false,
    required: ["route", "task_type", "requires_calculation", "requires_human_review", "confidence"],
    properties: {
      route: { type: "string", enum: routes.map((item) => item.route_id) },
      task_type: { enum: taskTypes },
      requires_calculation: { type: "boolean" },
      requires_human_review: { type: "boolean" },
      confidence: { type: "number", minimum: 0, maximum: 1 },
      reason: { type: "string" },
      evidence: { type: "array", items: { type: "string" } },
    },
  };
}

export function createRoutingRules(routes) {
  const fallback = routes.find((item) => item.is_default) || routes[0];
  return {
    schema_version: "routing_rules.v1",
    default_route_id: fallback?.route_id || "",
    rules: routes.map((item, index) => ({
      rule_id: `${item.route_id}_rule`,
      priority: index + 1,
      route_id: item.route_id,
      when: {
        type: "contains",
        field: "/text",
        examples: item.examples.slice(0, 3),
      },
    })),
  };
}

export function contractSection(routes, section) {
  if (section === "input") return createInputSchema(routes);
  if (section === "output") return createOutputSchema(routes);
  if (section === "rules") return createRoutingRules(routes);
  return createContract(routes);
}

export function yaml(value, indent = 0) {
  if (Array.isArray(value)) {
    return value.map((item) => `${" ".repeat(indent)}- ${typeof item === "object" && item !== null ? `\n${yaml(item, indent + 2)}` : String(item)}`).join("\n");
  }
  return Object.entries(value)
    .map(([key, item]) => {
      if (item && typeof item === "object") return `${" ".repeat(indent)}${key}:\n${yaml(item, indent + 2)}`;
      return `${" ".repeat(indent)}${key}: ${String(item)}`;
    })
    .join("\n");
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

function normalizeRoute(item) {
  const routeId = String(item.route_id || "").trim() || "new_route";
  const examples = Array.isArray(item.examples) ? item.examples.map((example) => String(example).trim()).filter(Boolean) : ["Example sentence"];
  return {
    route_id: routeId,
    description: String(item.description || "Untitled route").trim(),
    is_unsafe: Boolean(item.is_unsafe),
    task_type: taskTypes.includes(item.task_type) ? item.task_type : "generate_report",
    requires_calculation: Boolean(item.requires_calculation),
    requires_human_review: Boolean(item.requires_human_review),
    is_default: Boolean(item.is_default),
    examples: examples.length ? examples : ["Example sentence"],
  };
}

function paletteCategory(id, label, color, blocks) {
  return { id, label, color, blocks };
}

function paletteBlock(label, description, tone) {
  return { label, description, tone };
}

function step(id, label, path, state, reason = "") {
  return { id, label, path, state, reason };
}
