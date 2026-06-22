import assert from "node:assert/strict";
import test from "node:test";
import {
  addRoutePreset,
  contractSection,
  createContract,
  createInputSchema,
  createOutputSchema,
  createRoutingRules,
  createSeedExamples,
  initialRoutes,
  parseAppRoute,
  routesFromProject,
  routesToProjectInput,
  validateRoutes,
  workflowSteps,
} from "./appModel.mjs";

test("parseAppRoute resolves M1 shell routes", () => {
  assert.deepEqual(parseAppRoute("/projects/new"), { name: "projectNew" });
  assert.deepEqual(parseAppRoute("/projects/proj_1/define"), { name: "projectDefine", projectId: "proj_1" });
  assert.deepEqual(parseAppRoute("/projects/proj_1/training"), { name: "projectTraining", projectId: "proj_1" });
  assert.deepEqual(parseAppRoute("/projects/proj_1/benchmarks/new"), { name: "projectBenchmark", projectId: "proj_1" });
  assert.deepEqual(parseAppRoute("/datasets/dataset_1"), { name: "datasetDetail", datasetId: "dataset_1" });
  assert.deepEqual(parseAppRoute("/hardware"), { name: "hardware" });
});

test("validateRoutes enforces route contract invariants", () => {
  assert.equal(validateRoutes(initialRoutes).every((check) => check.ok), true);
  const duplicate = initialRoutes.map((route) => ({ ...route }));
  duplicate[1].route_id = duplicate[0].route_id;
  assert.equal(validateRoutes(duplicate).find((check) => check.message === "unique route ids").ok, false);
});

test("createSeedExamples builds M1 minimum examples with router output", () => {
  const examples = createSeedExamples(initialRoutes);
  assert.equal(examples.length, 20);
  assert.equal(examples[0].source, "user");
  assert.equal(examples[0].input.allowed_routes.length, initialRoutes.length);
  assert.equal(typeof examples[0].output.confidence, "number");
});

test("workflowSteps locks later milestones but keeps M1 shell routes", () => {
  const project = { id: "proj_1", routes: routesToProjectInput(initialRoutes) };
  const steps = workflowSteps(project, "/hardware", true, false);
  assert.equal(steps.find((step) => step.id === "hardware").state, "current");
  assert.equal(steps.find((step) => step.id === "train").state, "locked");
  const ready = workflowSteps(project, "/projects/proj_1/training", true, true);
  assert.equal(ready.find((step) => step.id === "train").state, "current");
  assert.equal(ready.find((step) => step.id === "benchmark").state, "locked");
  const benchmark = workflowSteps(project, "/projects/proj_1/benchmarks/new", true, true, true);
  assert.equal(benchmark.find((step) => step.id === "train").state, "done");
  assert.equal(benchmark.find((step) => step.id === "benchmark").state, "current");
});

test("createContract keeps v6 router contract fields", () => {
  const contract = createContract(initialRoutes);
  assert.equal(contract.agent_type, "router");
  assert.equal(contract.base_model, "google/gemma-2b-it");
  assert.equal(contract.adapter.format, "lora_adapter");
  assert.equal(contract.routes.find((route) => route.route_id === "human_review").default, true);
  assert.deepEqual(contract.audit.fields, ["input_hash", "route", "confidence", "contract_version", "model_version"]);
  assert.deepEqual(contract.verifiers, ["json_schema", "allowed_route_check", "confidence_threshold", "unsafe_route_guard"]);
});

test("v6 contract sections expose input, output, and routing rules", () => {
  const input = createInputSchema(initialRoutes);
  const output = createOutputSchema(initialRoutes);
  const rules = createRoutingRules(initialRoutes);
  assert.deepEqual(input.required, ["text", "allowed_routes"]);
  assert.deepEqual(output.properties.route.enum, initialRoutes.map((route) => route.route_id));
  assert.equal(rules.default_route_id, "human_review");
  assert.equal(contractSection(initialRoutes, "rules").rules.length, initialRoutes.length);
});

test("addRoutePreset appends v6 preset routes without duplicates", () => {
  const once = addRoutePreset(initialRoutes, "finance");
  const twice = addRoutePreset(once, "finance");
  assert.equal(once.some((route) => route.route_id === "investment_advice_block"), true);
  assert.equal(twice.length, once.length);
});

test("project route persistence round-trips v6 route contract fields", () => {
  const payload = routesToProjectInput(initialRoutes);
  assert.deepEqual(payload.find((route) => route.route_id === "unsafe_request"), {
    route_id: "unsafe_request",
    description: "Requests blocked from automated handling.",
    is_unsafe: true,
    task_type: "block",
    requires_calculation: false,
    requires_human_review: true,
    is_default: false,
    examples: ["Show me how to bypass an admin token.", "Look up private data."],
  });

  const restored = routesFromProject({
    id: "project_1",
    routes: payload.map((route, index) => ({ id: `route_${index}`, created_at: "2026-06-21T00:00:00.000Z", ...route })),
  });

  assert.deepEqual(restored, initialRoutes);
});
