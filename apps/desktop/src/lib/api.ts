import type {
  ApiError,
  ApiOperationId,
  ApiParams,
  ApiRequest,
  ApiResponse,
  TypedApiClient,
} from "./generated";
import type { ApiBootstrap } from "./bootstrap";

type HttpMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

interface OperationRoute {
  method: HttpMethod;
  path: string;
}

export class ApiClientError extends Error {
  readonly status: number;
  readonly payload: ApiError;

  constructor(status: number, payload: ApiError) {
    super(payload.message);
    this.name = "ApiClientError";
    this.status = status;
    this.payload = payload;
  }
}

const operationRoutes: Record<ApiOperationId, OperationRoute> = {
  healthz: { method: "GET", path: "/healthz" },
  listProjects: { method: "GET", path: "/projects" },
  createProject: { method: "POST", path: "/projects" },
  getProject: { method: "GET", path: "/projects/{id}" },
  updateProject: { method: "PATCH", path: "/projects/{id}" },
  archiveProject: { method: "DELETE", path: "/projects/{id}" },
  listPresets: { method: "GET", path: "/presets" },
  getPreset: { method: "GET", path: "/presets/{id}" },
  getModelCatalog: { method: "GET", path: "/model-catalog" },
  listDatasets: { method: "GET", path: "/projects/{id}/datasets" },
  createDataset: { method: "POST", path: "/projects/{id}/datasets" },
  getDataset: { method: "GET", path: "/datasets/{id}" },
  updateDataset: { method: "PATCH", path: "/datasets/{id}" },
  updateExample: { method: "PATCH", path: "/examples/{id}" },
  listGlobalJobs: { method: "GET", path: "/jobs" },
  listProjectJobs: { method: "GET", path: "/projects/{id}/jobs" },
  submitProjectJob: { method: "POST", path: "/projects/{id}/jobs" },
  getJob: { method: "GET", path: "/jobs/{job_id}" },
  cancelJob: { method: "DELETE", path: "/jobs/{job_id}" },
  streamJobEvents: { method: "GET", path: "/jobs/{job_id}/events" },
  retryJob: { method: "POST", path: "/jobs/{job_id}/retry" },
  resumeJob: { method: "POST", path: "/jobs/{job_id}/resume" },
  listEvalSets: { method: "GET", path: "/projects/{id}/eval-sets" },
  createEvalSet: { method: "POST", path: "/projects/{id}/eval-sets" },
  getEvalSet: { method: "GET", path: "/eval-sets/{id}" },
  listEvalRuns: { method: "GET", path: "/projects/{id}/eval-runs" },
  getEvalRun: { method: "GET", path: "/eval-runs/{id}" },
  listBenchmarks: { method: "GET", path: "/projects/{id}/benchmarks" },
  getBenchmark: { method: "GET", path: "/benchmarks/{id}" },
  getBenchmarkReport: { method: "GET", path: "/benchmarks/{id}/report" },
  listModelRuns: { method: "GET", path: "/projects/{id}/model-runs" },
  getModelRun: { method: "GET", path: "/model-runs/{id}" },
  listModelRunCheckpoints: { method: "GET", path: "/model-runs/{id}/checkpoints" },
  listAgentPackages: { method: "GET", path: "/projects/{id}/agent-packages" },
  createAgentPackage: { method: "POST", path: "/projects/{id}/agent-packages" },
  getAgentPackage: { method: "GET", path: "/agent-packages/{agent_package_id}" },
  runPlayground: { method: "POST", path: "/agent-packages/{agent_package_id}/playground-runs" },
  createExport: { method: "POST", path: "/projects/{id}/export" },
  getExport: { method: "GET", path: "/exports/{job_id}" },
  downloadExportArtifact: { method: "GET", path: "/exports/{job_id}/artifact" },
  revealExportArtifact: { method: "POST", path: "/exports/{job_id}/reveal" },
  submitHardwareScan: { method: "POST", path: "/hardware-doctor/scan" },
  getHardwareDoctorResult: { method: "GET", path: "/hardware-doctor/result" },
  previewTeacherPacket: { method: "POST", path: "/projects/{id}/teacher-packets/preview" },
  approveTeacherPacket: { method: "POST", path: "/teacher-packets/{id}/approve" },
  listCredentials: { method: "GET", path: "/credentials" },
  upsertCredential: { method: "PUT", path: "/credentials/{provider}" },
  deleteCredential: { method: "DELETE", path: "/credentials/{provider}" },
};

function paramsRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function pathParamNames(path: string): Set<string> {
  return new Set(Array.from(path.matchAll(/\{([^}]+)\}/g), (match) => match[1]));
}

function buildPath(route: OperationRoute, params: Record<string, unknown>): string {
  return route.path.replace(/\{([^}]+)\}/g, (_match, key: string) => {
    const value = params[key];
    if (typeof value !== "string" && typeof value !== "number") {
      throw new Error(`API_PARAM_MISSING:${key}`);
    }
    return encodeURIComponent(String(value));
  });
}

function buildQuery(route: OperationRoute, params: Record<string, unknown>): string {
  const pathParams = pathParamNames(route.path);
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (pathParams.has(key) || value === undefined || value === null) {
      continue;
    }
    search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  try {
    return (await response.json()) as ApiError;
  } catch {
    return {
      error_code: "NON_JSON_ERROR",
      message: response.statusText || "Request failed.",
      details: {},
      trace_id: response.headers.get("x-trace-id") ?? "",
    };
  }
}

export function createApiClient(
  bootstrap: ApiBootstrap,
  fetchImpl: typeof fetch = fetch,
): TypedApiClient {
  const baseUrl = bootstrap.baseUrl.replace(/\/+$/, "");

  return {
    async request<TOperation extends ApiOperationId>(
      operation: TOperation,
      args: {
        params: ApiParams<TOperation>;
        body: ApiRequest<TOperation>;
        idempotencyKey?: string;
      },
    ): Promise<ApiResponse<TOperation>> {
      const route = operationRoutes[operation];
      const params = paramsRecord(args.params);
      const url = `${baseUrl}${buildPath(route, params)}${buildQuery(route, params)}`;
      const headers: Record<string, string> = {
        Accept: "application/json",
        Authorization: `Bearer ${bootstrap.token}`,
      };
      if (args.idempotencyKey) {
        headers["Idempotency-Key"] = args.idempotencyKey;
      }

      const init: RequestInit = { method: route.method, headers };
      if (args.body !== undefined && args.body !== null) {
        headers["Content-Type"] = "application/json";
        init.body = JSON.stringify(args.body);
      }

      const response = await fetchImpl(url, init);
      if (!response.ok) {
        throw new ApiClientError(response.status, await errorFromResponse(response));
      }
      if (response.status === 204) {
        return undefined as ApiResponse<TOperation>;
      }
      if (operation === "streamJobEvents") {
        return response.body as ApiResponse<TOperation>;
      }
      if (operation === "downloadExportArtifact") {
        return (await response.blob()) as ApiResponse<TOperation>;
      }
      return (await response.json()) as ApiResponse<TOperation>;
    },
  };
}
