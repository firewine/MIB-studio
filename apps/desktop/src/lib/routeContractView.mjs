import { contractSection, createContract, paletteCategories, taskTypes, yaml } from "./appModel.mjs";

export function routeContractPage({ state, checks, pageShell, noticeHtml, checksHtml, escapeHtml }) {
  const valid = checks.every((check) => check.ok);
  return pageShell(
    "Define",
    "Route contract",
    "Assemble input, route, guard, output, and audit blocks into a fixed router contract.",
    `<button class="button" data-action="download-contract">Download contract</button><button class="button primary" data-action="save-routes" ${valid ? "" : "disabled"}>Save contract</button>`,
    `${noticeHtml}<div class="define-grid">${toolboxHtml(state, escapeHtml)}${canvasHtml(state, escapeHtml)}${inspectorHtml(state, checks, checksHtml, escapeHtml)}</div>`,
  );
}

function toolboxHtml(state, escapeHtml) {
  const selected = paletteCategories.find((category) => category.id === state.selectedPaletteCategory) || paletteCategories[0];
  return `<section class="toolbox" aria-label="Route contract toolbox">
    <div class="toolbox-header"><h2>Toolbox</h2></div>
    <div class="tool-body">
      <div class="category-rail" role="tablist" aria-label="Block categories">${paletteCategories
        .map((category) => `<button class="category-dot ${category.id === selected.id ? "active" : ""}" style="--category-color:${category.color}" title="${category.label}" aria-label="${category.label}" aria-selected="${category.id === selected.id}" data-action="select-palette" data-palette="${category.id}"></button>`)
        .join("")}</div>
      <div class="blocks-list">${selected.blocks
        .map((block) => `<button class="palette-block ${block.tone}" data-action="insert-block" data-block-label="${escapeHtml(block.label)}">${escapeHtml(block.label)}<small>${escapeHtml(block.description)}</small></button>`)
        .join("")}</div>
    </div>
  </section>`;
}

function canvasHtml(state, escapeHtml) {
  return `<section class="canvas-surface" aria-label="Route contract canvas">
    <div class="canvas-toolbar">
      <span class="pill blue">${state.routes.length} routes</span>
      <span class="subtle">${state.routes.filter((item) => item.is_unsafe).length} unsafe · output schema locked</span>
      <span class="toolbar-spacer"></span>
      <button class="button" data-action="test-route">Test</button>
      <button class="button primary" data-action="compile-contract">Compile</button>
    </div>
    <div class="canvas-work">
      <div class="block-stack">
        <div class="iblock input">when <span class="socket">input.text</span> arrives</div>
        <div class="iblock input">normalize text with <span class="slot">pii_mask</span></div>
        <div class="iblock route">route among <span class="slot">${state.routes.length} labels</span> using examples</div>
        <div class="nested-blocks">
          <div class="iblock guard">if route has <span class="socket">unsafe</span> flag then <span class="slot">block</span></div>
          <div class="iblock logic">if confidence &lt; <span class="socket">0.65</span> then <span class="slot">human_review</span></div>
        </div>
        <div class="iblock eval">emit JSON <span class="slot">route · task_type · confidence</span></div>
        <div class="iblock data last">log trace with <span class="slot">contract_version</span></div>
      </div>
      ${routeBoardHtml(state, escapeHtml)}
    </div>
  </section>`;
}

function routeBoardHtml(state, escapeHtml) {
  return `<aside class="route-board" aria-label="Routes">
    <h3>Routes</h3>
    <div class="route-chip-list">${state.routes
      .map((route, index) => `<button class="route-chip ${index === state.selectedRoute ? "active" : ""}" data-route-index="${index}"><strong class="mono">${escapeHtml(route.route_id)}</strong><small>${escapeHtml(route.description)}</small><span>${route.is_default ? '<em class="pill blue">default</em>' : ""}${route.requires_human_review ? '<em class="pill warn">review</em>' : ""}${route.is_unsafe ? '<em class="pill bad">unsafe</em>' : '<em class="pill ok">auto</em>'}</span></button>`)
      .join("")}</div>
    <div class="preset-row">
      <button class="mini-button" data-action="add-preset" data-preset="support">+ support</button>
      <button class="mini-button" data-action="add-preset" data-preset="finance">+ finance</button>
      <button class="mini-button" data-action="add-preset" data-preset="ops">+ ops</button>
    </div>
  </aside>`;
}

function inspectorHtml(state, checks, checksHtml, escapeHtml) {
  const selected = state.routes[state.selectedRoute] || state.routes[0];
  return `<aside class="inspector" aria-label="Route inspector">
    <div class="inspector-header"><h2>Inspector</h2></div>
    <div class="inspector-body">
      <div class="tabs" role="tablist" aria-label="Inspector panels">
        ${inspectorTab(state, "route", "Route")}
        ${inspectorTab(state, "checks", "Checks")}
        ${inspectorTab(state, "contract", "Contract")}
      </div>
      ${state.inspectorTab === "route" ? routePanel(state, selected, escapeHtml) : ""}
      ${state.inspectorTab === "checks" ? checksPanel(checks, checksHtml) : ""}
      ${state.inspectorTab === "contract" ? contractPanel(state, escapeHtml) : ""}
    </div>
  </aside>`;
}

function inspectorTab(state, id, label) {
  return `<button class="tab ${state.inspectorTab === id ? "active" : ""}" role="tab" aria-selected="${state.inspectorTab === id}" data-action="select-inspector-tab" data-tab="${id}">${label}</button>`;
}

function routePanel(state, route, escapeHtml) {
  return `<section class="inspector-panel" role="tabpanel">
    <div class="notice-card"><strong class="mono">${escapeHtml(route.route_id)}</strong><span>Selected route contract properties</span></div>
    ${routeForm(route, escapeHtml)}
    <div class="split-toolbar">
      <button class="button" data-action="apply-route">Apply route</button>
      <button class="button" data-action="add-route">Add route</button>
    </div>
    ${state.routeTestResult ? `<pre class="codebox result-box">${escapeHtml(JSON.stringify(state.routeTestResult, null, 2))}</pre>` : ""}
  </section>`;
}

function checksPanel(checks, checksHtml) {
  return `<section class="inspector-panel" role="tabpanel">${checksHtml(checks)}</section>`;
}

function contractPanel(state, escapeHtml) {
  const text = state.contractTab === "agent" ? yaml(createContract(state.routes)) : JSON.stringify(contractSection(state.routes, state.contractTab), null, 2);
  return `<section class="inspector-panel" role="tabpanel">
    <div class="contract-tabs" role="tablist" aria-label="Contract sections">
      ${contractTab(state, "agent")}
      ${contractTab(state, "input")}
      ${contractTab(state, "output")}
      ${contractTab(state, "rules")}
    </div>
    <pre class="codebox contract-code">${escapeHtml(text)}</pre>
    <button class="button" data-nav="/projects/${state.selectedProject?.id}/datasets/new">Build examples from contract</button>
  </section>`;
}

function contractTab(state, id) {
  return `<button class="${state.contractTab === id ? "active" : ""}" aria-selected="${state.contractTab === id}" data-action="select-contract-tab" data-contract-tab="${id}">${id}</button>`;
}

function routeForm(route, escapeHtml) {
  return `<div class="form-grid">
    <label class="field"><span>Route id</span><input class="mono" data-field="route-id" value="${escapeHtml(route.route_id)}"></label>
    <label class="field"><span>Description</span><input data-field="route-desc" value="${escapeHtml(route.description)}"></label>
    <label class="field"><span>Task type</span><select data-field="task-type">${taskTypes.map((type) => `<option ${route.task_type === type ? "selected" : ""}>${type}</option>`).join("")}</select></label>
    <label class="field"><span>Positive examples</span><textarea data-field="examples">${escapeHtml(route.examples.join("\n"))}</textarea></label>
    <div class="check-list">
      <label class="check-field"><input type="checkbox" data-field="calculation" ${route.requires_calculation ? "checked" : ""}> requires calculation</label>
      <label class="check-field"><input type="checkbox" data-field="review" ${route.requires_human_review ? "checked" : ""}> human review</label>
      <label class="check-field"><input type="checkbox" data-field="unsafe" ${route.is_unsafe ? "checked" : ""}> unsafe route</label>
      <label class="check-field"><input type="checkbox" data-field="default-route" ${route.is_default ? "checked" : ""}> default route</label>
    </div>
  </div>`;
}
