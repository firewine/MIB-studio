import assert from "node:assert/strict";
import test from "node:test";
import {
  createContract,
  createSeedExamples,
  initialRoutes,
  parseAppRoute,
  routesToProjectInput,
  validateRoutes,
  workflowSteps,
} from "./appModel.mjs";

test("parseAppRoute resolves M1 shell routes", () => {
  assert.deepEqual(parseAppRoute("/projects/new"), { name: "projectNew" });
  assert.deepEqual(parseAppRoute("/projects/proj_1/define"), { name: "projectDefine", projectId: "proj_1" });
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
});

test("createContract keeps v6 router contract fields", () => {
  const contract = createContract(initialRoutes);
  assert.equal(contract.agent_type, "router");
  assert.equal(contract.base_model, "google/gemma-2b-it");
  assert.deepEqual(contract.verifiers, ["json_schema", "allowed_route_check", "confidence_threshold", "unsafe_route_guard"]);
});
