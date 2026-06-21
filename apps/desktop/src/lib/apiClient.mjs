const routes = {
  healthz: ["GET", "/healthz"],
  listProjects: ["GET", "/projects"],
  createProject: ["POST", "/projects"],
  getProject: ["GET", "/projects/{id}"],
  updateProject: ["PATCH", "/projects/{id}"],
  listPresets: ["GET", "/presets"],
  listDatasets: ["GET", "/projects/{id}/datasets"],
  createDataset: ["POST", "/projects/{id}/datasets"],
  getDataset: ["GET", "/datasets/{id}"],
  updateDataset: ["PATCH", "/datasets/{id}"],
  getJob: ["GET", "/jobs/{job_id}"],
  submitHardwareScan: ["POST", "/hardware-doctor/scan"],
  getHardwareDoctorResult: ["GET", "/hardware-doctor/result"],
  previewTeacherPacket: ["POST", "/projects/{id}/teacher-packets/preview"],
  approveTeacherPacket: ["POST", "/teacher-packets/{id}/approve"],
  listCredentials: ["GET", "/credentials"],
  upsertCredential: ["PUT", "/credentials/{provider}"],
  deleteCredential: ["DELETE", "/credentials/{provider}"],
};

export class ApiClientError extends Error {
  constructor(status, payload) {
    super(payload.message);
    this.name = "ApiClientError";
    this.status = status;
    this.payload = payload;
  }
}

export function createApiClient(bootstrap, fetchImpl = fetch) {
  const baseUrl = bootstrap.baseUrl.replace(/\/+$/, "");
  return {
    async request(operation, { params = {}, body, idempotencyKey } = {}) {
      const [method, path] = routes[operation];
      const url = `${baseUrl}${buildPath(path, params)}${buildQuery(path, params)}`;
      const headers = {
        Accept: "application/json",
        Authorization: `Bearer ${bootstrap.token}`,
      };
      if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
      const init = { method, headers };
      if (body !== undefined && body !== null) {
        headers["Content-Type"] = "application/json";
        init.body = JSON.stringify(body);
      }
      const response = await fetchImpl(url, init);
      if (!response.ok) throw new ApiClientError(response.status, await errorPayload(response));
      if (response.status === 204) return undefined;
      return response.json();
    },
  };
}

export async function resolveBootstrap() {
  try {
    const invoke = window.__TAURI__?.core?.invoke || window.__TAURI__?.tauri?.invoke;
    if (invoke) {
      const value = await invoke("get_api_bootstrap");
      const baseUrl = value.baseUrl || value.base_url;
      if (baseUrl && value.token) return { baseUrl, token: value.token };
    }
  } catch {
    // Browser dev mode falls back to the local daemon default.
  }
  return window.MIB_BOOTSTRAP || { baseUrl: "http://127.0.0.1:8910", token: "test-token" };
}

export function idempotencyKey(prefix) {
  if (globalThis.crypto?.randomUUID) return `${prefix}-${globalThis.crypto.randomUUID()}`;
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

function buildPath(path, params) {
  return path.replace(/\{([^}]+)}/g, (_match, key) => {
    if (params[key] === undefined || params[key] === null) throw new Error(`API_PARAM_MISSING:${key}`);
    return encodeURIComponent(String(params[key]));
  });
}

function buildQuery(path, params) {
  const pathKeys = new Set(Array.from(path.matchAll(/\{([^}]+)}/g), (match) => match[1]));
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params || {})) {
    if (!pathKeys.has(key) && value !== undefined && value !== null) search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

async function errorPayload(response) {
  try {
    return await response.json();
  } catch {
    return {
      error_code: "NON_JSON_ERROR",
      message: response.statusText || "Request failed.",
      details: {},
      trace_id: response.headers.get("x-trace-id") || "",
    };
  }
}
