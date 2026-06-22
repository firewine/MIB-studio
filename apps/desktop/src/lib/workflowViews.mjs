export function renderPackagePage({
  state,
  completedModelRun,
  validBenchmark,
  latestAgentPackage,
  pageShell,
  notice,
  metric,
  statePanel,
  escapeHtml,
}) {
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
    `${notice()}${gatePanel}<div class="two-column"><section class="surface"><h2>Package contract</h2>${agentPackage ? `<pre class="codebox">${escapeHtml(agentPackage.contract_yaml)}</pre>` : statePanel("empty", "No package yet", "Build package after a completed model run and valid benchmark report.")}</section><section class="surface"><h2>Playground result</h2>${playgroundResultHtml({ state, metric, statePanel, escapeHtml })}</section></div>${agentPackagesHtml({ state, escapeHtml })}`,
  );
}

export function renderExportPage({
  state,
  latestAgentPackage,
  latestExport,
  pageShell,
  notice,
  metric,
  statePanel,
  escapeHtml,
}) {
  const agentPackage = latestAgentPackage();
  const exportRead = latestExport();
  const canSubmit = Boolean(agentPackage);
  const canReveal = exportRead?.status === "SUCCEEDED" && exportRead.reveal_url;
  const actions = `<button class="button primary" data-action="start-export" ${canSubmit ? "" : "disabled"}>Start zip export</button><button class="button" data-action="reveal-export" ${canReveal ? "" : "disabled"}>Reveal artifact</button>`;
  const gatePanel = `<div class="metric-grid">${metric("agent package", agentPackage?.agent_id || "package required", agentPackage ? "ok" : "warn")}${metric("export type", "zip", "blue")}${metric("status", exportRead?.status || "not started", exportRead?.status === "SUCCEEDED" ? "ok" : "blue")}${metric("artifact", exportRead?.artifact_sha256 ? exportRead.artifact_sha256.slice(0, 10) : "pending", exportRead?.artifact_sha256 ? "ok" : "blue")}</div>`;
  return pageShell(
    "Export",
    "Export workflow",
    "Submit a zip export job through the local daemon and review only daemon-provided manifest and artifact hashes.",
    actions,
    `${notice()}${gatePanel}<div class="two-column"><section class="surface"><h2>Export request</h2><pre class="codebox">${escapeHtml(JSON.stringify({ agent_package_id: agentPackage?.id || null, export_type: "zip" }, null, 2))}</pre></section><section class="surface"><h2>Export result</h2>${exportResultHtml({ exportRead, metric, statePanel, escapeHtml })}</section></div>${statePanel("locked", "Release evidence boundary", "This UI smoke is not M6-RC or v0 release evidence. Runtime smoke, Docker evidence, endpoint transcripts, and real adapter evidence remain external release gates.")}`,
  );
}

function playgroundResultHtml({ state, metric, statePanel, escapeHtml }) {
  const result = state.playgroundResult;
  if (!result) return statePanel("empty", "No run yet", "Run Playground after package build.");
  return `<div class="metric-grid">${metric("verifier", result.verifier_status, result.verifier_status === "PASS" ? "ok" : "warn")}${metric("fallback", result.fallback_used ? "used" : result.fallback_required ? "required" : "not required", result.fallback_required ? "warn" : "ok")}${metric("audit", result.audit_event_id ? result.audit_event_id.slice(0, 8) : "missing", result.audit_event_id ? "ok" : "warn")}</div><pre class="codebox">${escapeHtml(JSON.stringify(result.output, null, 2))}</pre>`;
}

function agentPackagesHtml({ state, escapeHtml }) {
  if (!state.agentPackages.length) return "";
  return `<div class="table-surface"><table><thead><tr><th>Agent</th><th>Version</th><th>Contract</th><th>Benchmark</th></tr></thead><tbody>${state.agentPackages
    .map((item) => `<tr><td class="mono">${escapeHtml(item.agent_id)}</td><td>${escapeHtml(item.contract_version)}</td><td class="mono">${escapeHtml(item.contract_sha256.slice(0, 12))}</td><td class="mono">${escapeHtml(item.benchmark_id)}</td></tr>`)
    .join("")}</tbody></table></div>`;
}

function exportResultHtml({ exportRead, metric, statePanel, escapeHtml }) {
  if (!exportRead) return statePanel("empty", "No export yet", "Start zip export after an Agent Package exists.");
  return `<div class="metric-grid">${metric("job", exportRead.job_id.slice(0, 12), "blue")}${metric("manifest_sha256", exportRead.manifest_sha256 ? exportRead.manifest_sha256.slice(0, 10) : "pending", exportRead.manifest_sha256 ? "ok" : "blue")}${metric("artifact_sha256", exportRead.artifact_sha256 ? exportRead.artifact_sha256.slice(0, 10) : "pending", exportRead.artifact_sha256 ? "ok" : "blue")}${metric("download", exportRead.artifact_url || "not ready", exportRead.artifact_url ? "ok" : "blue")}</div><pre class="codebox">${escapeHtml(JSON.stringify(exportRead, null, 2))}</pre>`;
}
