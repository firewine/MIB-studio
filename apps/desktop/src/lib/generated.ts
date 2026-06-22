// @generated from schemas/openapi.json; do not edit by hand.
export type Id = string;
export type ModelId = "google/gemma-2b-it" | "microsoft/Phi-3.5-mini-instruct";
export type IsoDatetime = string;
export type JobStatus = "QUEUED" | "RUNNING" | "SUCCEEDED" | "FAILED" | "CANCELLED" | "INTERRUPTED";
export type JobType = "dataset_gen" | "train" | "eval" | "benchmark" | "export" | "hardware_scan";
export type DatasetStatus = "DRAFT" | "BUILT" | "REVIEWED" | "APPROVED" | "ARCHIVED";
export type BenchmarkStatus = "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED" | "INTERRUPTED";
export type EvalTargetStatus = BenchmarkStatus | "SKIPPED_OPTIONAL";
export type Backend = "cuda" | "mlx";

export interface PageParams {
  cursor?: string;
  limit?: number;
}

export interface ErrorResponse {
  error_code: string;
  message: string;
  details: Record<string, unknown>;
  trace_id: string;
}

export interface RouteInput {
  route_id: string;
  description: string;
  is_unsafe: boolean;
  task_type?: "generate_report" | "provide_advice" | "escalate" | "block";
  requires_calculation?: boolean;
  requires_human_review?: boolean;
  is_default?: boolean;
  examples?: string[];
}

export interface ProjectCreate {
  name: string;
  preset_id: string;
  routes: RouteInput[];
}

export interface ProjectPatch {
  name?: string;
  routes?: RouteInput[];
}

export interface HealthRead {
  status: "ok";
  version: string;
}

export interface RouteRead {
  id: Id;
  route_id: string;
  description: string;
  is_unsafe: boolean;
  task_type: "generate_report" | "provide_advice" | "escalate" | "block";
  requires_calculation: boolean;
  requires_human_review: boolean;
  is_default: boolean;
  examples: string[];
  created_at: IsoDatetime;
}

export interface ProjectRead {
  id: Id;
  name: string;
  preset_id: string;
  routes: RouteRead[];
  archived_at?: IsoDatetime | null;
  route_taxonomy_locked?: boolean;
  created_at: IsoDatetime;
  updated_at: IsoDatetime;
}

export interface PresetRead {
  id: string;
  name: string;
  preset_type: "router";
  version: number;
  schema_refs: Record<string, string>;
  config_json: Record<string, unknown>;
  created_at: IsoDatetime;
}

export interface DatasetBuildRequest {
  examples: ExampleInput[];
  status: "DRAFT" | "BUILT";
}

export interface ExampleInput {
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  source: "user" | "teacher" | "import" | "hard_negative" | "eval_gold";
}

export interface DatasetPatch {
  status?: "DRAFT" | "BUILT" | "REVIEWED" | "APPROVED" | "ARCHIVED";
  approved_example_ids?: Id[];
}

export interface DatasetRead {
  id: Id;
  project_id: Id;
  status: "DRAFT" | "BUILT" | "REVIEWED" | "APPROVED" | "ARCHIVED";
  version: number;
  path: string;
  sample_count: number;
  sha256: string;
  schema_version: string;
  route_snapshot_sha256: string;
  created_at: IsoDatetime;
  frozen_at?: IsoDatetime | null;
}

export interface DatasetWithExamples extends DatasetRead {
  examples: ExampleRead[];
  next_cursor?: string | null;
}

export interface RowValidationError {
  field: string;
  code: string;
  message: string;
}

export interface ExamplePatch {
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  review_status?: "PENDING" | "APPROVED" | "REJECTED" | "EDITED";
}

export interface ExampleRead {
  id: Id;
  dataset_id: Id;
  source: "user" | "teacher" | "import" | "hard_negative" | "eval_gold";
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  review_status: "PENDING" | "APPROVED" | "REJECTED" | "EDITED";
  approved: boolean;
  validation_errors: RowValidationError[];
  created_at: IsoDatetime;
}

export interface JobAcceptedResponse {
  job_id: Id;
  status: JobStatus;
  type: string;
  events_url: string;
  created_resource_type: "model_run" | "benchmark" | "export" | "hardware_scan" | "dataset" | "none";
  created_resource_id?: Id | null;
  idempotency_replayed: boolean;
}

export interface JobRead {
  id: Id;
  project_id?: Id | null;
  parent_job_id?: Id | null;
  type: "dataset_gen" | "train" | "eval" | "benchmark" | "export" | "hardware_scan";
  status: JobStatus;
  resource_class: "cpu_shared" | "gpu_exclusive";
  priority: number;
  params_json: Record<string, unknown>;
  progress_json: Record<string, unknown>;
  error_class?: string | null;
  error_message?: string | null;
  cancel_requested_at?: IsoDatetime | null;
  attempt_count: number;
  events_url: string;
  created_at: IsoDatetime;
  started_at?: IsoDatetime | null;
  ended_at?: IsoDatetime | null;
}

export interface JobControlResponse {
  job_id: Id;
  child_job_id?: Id | null;
  status: JobStatus;
  cancel_requested?: boolean;
  events_url: string;
}

export type JobEventType = "status_change" | "heartbeat" | "step" | "loss" | "vram" | "log" | "artifact" | "metric" | "error";

export interface JobEventEnvelope {
  job_id: Id;
  seq: number;
  ts: IsoDatetime;
  level: "debug" | "info" | "warn" | "error";
  event_type: JobEventType;
  payload: Record<string, unknown>;
  trace_id: string;
}

export interface ResumeJobRequest {
  checkpoint_id: Id;
}

export interface JobRetryRequest {
  teacher_packet_approval_id?: Id | null;
}

export interface DatasetGenParams {
  dataset_id?: Id | null;
  generation_mode: "build_from_user_examples" | "teacher_synthetic";
  teacher_packet_approval_id?: Id | null;
  packet_sha256?: string | null;
  target_count: number;
  hard_negative_min_count: number;
}

export interface TrainParams {
  preset_id: string;
  dataset_id: Id;
  base_model: ModelId;
  backend: "cuda" | "mlx";
  training_preset: "quick" | "balanced" | "production";
  seed: number;
}

export interface BenchmarkTargetConfig {
  target_key: string;
  target_type: "prompt_only" | "fine_tuned" | "teacher" | "rule_based" | "local_large";
  backend: "cuda" | "mlx" | "teacher" | "rule_based" | "prompt_only" | "local_large";
  model_run_id?: Id | null;
  base_model?: ModelId | null;
  prompt_template_sha256?: string | null;
  credential_id?: Id | null;
  teacher_base_url_origin?: string | null;
  routing_rules_path?: string | null;
  routing_rules_sha256?: string | null;
  local_large_config?: Record<string, unknown> | null;
  required?: boolean;
}

export interface EvalParams {
  eval_set_id: Id;
  target: BenchmarkTargetConfig;
  seed: number;
}

export interface BenchmarkParams {
  eval_set_id: Id;
  targets: BenchmarkTargetConfig[];
  seeds: number[];
}

export type JobSubmitRequest =
  | { type: "dataset_gen"; params: DatasetGenParams }
  | { type: "train"; params: TrainParams }
  | { type: "eval"; params: EvalParams }
  | { type: "benchmark"; params: BenchmarkParams };

export interface EvalSetCreate {
  purpose: "teacher_guard" | "benchmark_gold" | "finance_reference";
  dataset_id: Id;
  example_ids: Id[];
  labeler_ids: string[];
  kappa?: number | null;
}

export interface EvalSetRead {
  id: Id;
  project_id: Id;
  dataset_id: Id;
  purpose: "teacher_guard" | "benchmark_gold" | "finance_reference";
  version: number;
  path: string;
  sha256: string;
  sample_count: number;
  route_snapshot_sha256: string;
  labeler_ids_json: string[];
  kappa?: number | null;
  frozen_at: IsoDatetime;
  created_at: IsoDatetime;
}

export interface EvalRunRead {
  id: Id;
  benchmark_id: Id;
  model_run_id?: Id | null;
  target_key: string;
  target_type: "prompt_only" | "fine_tuned" | "teacher" | "local_large" | "rule_based";
  backend: "cuda" | "mlx" | "teacher" | "rule_based" | "prompt_only" | "local_large";
  target_status: "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED" | "INTERRUPTED" | "SKIPPED_OPTIONAL";
  target_config_json: Record<string, unknown>;
  seed: number;
  credential_id?: Id | null;
  metrics_json: Record<string, unknown>;
  created_at: IsoDatetime;
}

export interface BenchmarkRead {
  id: Id;
  project_id: Id;
  job_id: Id;
  eval_set_id: Id;
  status: "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED" | "INTERRUPTED";
  report_sha256?: string | null;
  hash_status: "VALID" | "MISMATCH" | "MISSING";
  parity_status: "PASS" | "FAIL" | "NA";
  created_at: IsoDatetime;
  completed_at?: IsoDatetime | null;
}

export interface BenchmarkReportRead {
  benchmark_id: Id;
  report_sha256?: string | null;
  hash_status: "VALID" | "MISMATCH" | "MISSING";
  report?: Record<string, unknown> | null;
}

export interface ModelRunRead {
  id: Id;
  project_id: Id;
  dataset_id: Id;
  job_id?: Id | null;
  base_model: ModelId;
  backend: "cuda" | "mlx";
  method: "qlora" | "mlx_lora";
  adapter_path?: string | null;
  status: JobStatus;
  adapter_sha256?: string | null;
  artifact_manifest_sha256?: string | null;
  seed: number;
  config_hash: string;
  best_checkpoint_id?: Id | null;
  resumable: boolean;
  started_at?: IsoDatetime | null;
  ended_at?: IsoDatetime | null;
  created_at: IsoDatetime;
}

export interface CheckpointRead {
  id: Id;
  job_id: Id;
  model_run_id: Id;
  dataset_id: Id;
  dataset_version: number;
  step: number;
  path: string;
  training_config_hash: string;
  weights_sha256: string;
  resume_enabled: boolean;
  resume_disabled_reason_code: "NONE" | "DATASET_VERSION_MISMATCH" | "CONFIG_HASH_MISMATCH" | "MISSING_ARTIFACT" | "JOB_NOT_RESUMABLE";
  resume_disabled_reason_message: string;
  metrics_json?: Record<string, unknown>;
  created_at: IsoDatetime;
}

export interface AgentPackageCreate {
  model_run_id: Id;
  benchmark_id: Id;
  agent_slug?: string | null;
  fallback: FallbackConfigInput;
}

export interface FallbackConfigInput {
  enabled: boolean;
  provider: "openai" | "openai_compatible" | "none";
  model?: string | null;
  condition?: { type: "confidence_lt" | "verifier_failed" | "disabled"; threshold?: number | null } | null;
}

export interface AgentPackageRead {
  id: Id;
  agent_id: string;
  project_id: Id;
  model_run_id: Id;
  benchmark_id: Id;
  route_catalog_sha256: string;
  contract_version: number;
  contract_yaml: string;
  contract_sha256: string;
  created_at: IsoDatetime;
}

export interface PlaygroundRunRequest {
  input: Record<string, unknown>;
  approve_fallback?: boolean;
}

export interface PlaygroundRunResponse {
  output: Record<string, unknown>;
  verifier_status: "PASS" | "FAIL";
  verifier_errors: string[];
  fallback_required: boolean;
  fallback_used: boolean;
  audit_event_id?: Id | null;
}

export interface ExportParams {
  agent_package_id: Id;
  export_type: "zip" | "docker";
}

export interface ExportRead {
  id: Id;
  job_id: Id;
  agent_package_id: Id;
  export_type: "zip" | "docker";
  status: JobStatus;
  manifest_path?: string | null;
  manifest_sha256?: string | null;
  artifact_path?: string | null;
  artifact_sha256?: string | null;
  artifact_url?: string | null;
  reveal_url?: string | null;
  error_message?: string | null;
  created_at: IsoDatetime;
  completed_at?: IsoDatetime | null;
}

export interface RevealExportResponse {
  artifact_path: string;
  revealed: boolean;
}

export interface HardwareScanRequest {
  dry_run?: boolean;
  target_backend?: "cuda" | "mlx" | "auto";
}

export interface HardwareProfileRead {
  id: Id;
  machine_id: string;
  os: string;
  cpu?: string | null;
  gpu_vendor: "nvidia" | "apple" | "amd" | "intel" | "none" | "unknown";
  gpu_name?: string | null;
  vram_gb?: number | null;
  unified_ram_gb?: number | null;
  ram_gb: number;
  cuda_status?: "ok" | "missing" | "unsupported" | "na" | null;
  mlx_status?: "ok" | "missing" | "unsupported" | "na" | null;
  capability_gate: "G0" | "G1" | "G2";
  gate?: "G0" | "G1" | "G2";
  backend_recommendation: "cuda" | "mlx" | "cpu" | "unsupported";
  training_enabled: boolean;
  training_disabled_reason_code: "NO_GPU" | "LOW_VRAM" | "UNSUPPORTED_VENDOR" | "MISSING_DRIVER" | "PYTHON_UNSUPPORTED" | "NONE";
  training_disabled_reason_message: string;
  allowed_backends: Array<"cuda" | "mlx">;
  unlock_requirements: string[];
  dry_run_result_json: Record<string, unknown>;
  created_at: IsoDatetime;
  reason_code?: string;
}

export interface ModelCatalogEntryRead {
  id: ModelId;
  license: string;
  trust_remote_code: boolean;
  context_length: number;
  train_seq_len: number;
  chat_template: string;
  system_role: string;
  allowed_backends: Array<"cuda" | "mlx">;
  lora_target: string[];
  hf_commit_sha?: string | null;
  strict_manifest_ready: boolean;
  available: boolean;
  disabled_reason_code: "NONE" | "STRICT_MANIFEST_MISSING" | "LICENSE_NOT_ACCEPTED" | "BACKEND_UNSUPPORTED" | "LOCAL_CACHE_MISSING";
  disabled_reason_message: string;
  terms_required?: boolean;
  required_weight_files: Array<{
    path: string;
    sha256: string;
    size_bytes: number;
    present_in_cache: boolean;
  }>;
}

export interface ModelCatalogRead {
  items: ModelCatalogEntryRead[];
  strict_ready: boolean;
}

export interface CredentialUpsert {
  base_url: string;
  api_key: string;
  expires_at?: IsoDatetime | null;
}

export interface CredentialRead {
  id: Id;
  provider: "openai" | "openai_compatible";
  base_url_origin: string;
  keychain_ref: string;
  is_revoked: boolean;
  expires_at?: IsoDatetime | null;
  created_at: IsoDatetime;
  last_used_at?: IsoDatetime | null;
}

export interface TeacherPacketPreviewRequest {
  dataset_id: Id;
  example_ids: Id[];
  instruction: string;
}

export interface TeacherPacketPreviewRead {
  id: Id;
  project_id: Id;
  packet_sha256: string;
  packet_preview: Record<string, unknown>;
  pii_summary: Record<string, unknown>;
  expires_at: IsoDatetime;
  approved_at?: IsoDatetime | null;
}

export interface TeacherPacketApprovalRead {
  approval_id: Id;
  project_id: Id;
  approved_at: IsoDatetime;
  expires_at: IsoDatetime;
  packet_sha256: string;
}

export interface PageResponse<T> {
  items: T[];
  next_cursor?: string | null;
}

export type ApiOperationId =
  | "healthz"
  | "listProjects"
  | "createProject"
  | "getProject"
  | "updateProject"
  | "archiveProject"
  | "listPresets"
  | "getPreset"
  | "getModelCatalog"
  | "listDatasets"
  | "createDataset"
  | "getDataset"
  | "updateDataset"
  | "updateExample"
  | "listGlobalJobs"
  | "listProjectJobs"
  | "submitProjectJob"
  | "getJob"
  | "cancelJob"
  | "streamJobEvents"
  | "retryJob"
  | "resumeJob"
  | "listEvalSets"
  | "createEvalSet"
  | "getEvalSet"
  | "listEvalRuns"
  | "getEvalRun"
  | "listBenchmarks"
  | "getBenchmark"
  | "getBenchmarkReport"
  | "listModelRuns"
  | "getModelRun"
  | "listModelRunCheckpoints"
  | "listAgentPackages"
  | "createAgentPackage"
  | "getAgentPackage"
  | "runPlayground"
  | "createExport"
  | "getExport"
  | "downloadExportArtifact"
  | "revealExportArtifact"
  | "submitHardwareScan"
  | "getHardwareDoctorResult"
  | "previewTeacherPacket"
  | "approveTeacherPacket"
  | "listCredentials"
  | "upsertCredential"
  | "deleteCredential";

export interface ApiOperationMap {
  healthz: { params: void; request: void; response: HealthRead };
  listProjects: { params: PageParams & { include_archived?: boolean }; request: void; response: PageResponse<ProjectRead> };
  createProject: { params: void; request: ProjectCreate; response: ProjectRead };
  getProject: { params: { id: Id }; request: void; response: ProjectRead };
  updateProject: { params: { id: Id }; request: ProjectPatch; response: ProjectRead };
  archiveProject: { params: { id: Id }; request: void; response: void };
  listPresets: { params: void; request: void; response: PageResponse<PresetRead> };
  getPreset: { params: { id: Id }; request: void; response: PresetRead };
  getModelCatalog: { params: void; request: void; response: ModelCatalogRead };
  listDatasets: { params: { id: Id; status?: DatasetStatus } & PageParams; request: void; response: PageResponse<DatasetRead> };
  createDataset: { params: { id: Id }; request: DatasetBuildRequest; response: DatasetRead };
  getDataset: { params: { id: Id } & PageParams; request: void; response: DatasetWithExamples };
  updateDataset: { params: { id: Id }; request: DatasetPatch; response: DatasetRead };
  updateExample: { params: { id: Id }; request: ExamplePatch; response: ExampleRead };
  listGlobalJobs: { params: ({ status?: JobStatus; type?: JobType } & PageParams); request: void; response: PageResponse<JobRead> };
  listProjectJobs: { params: ({ id: Id; status?: JobStatus; type?: JobType } & PageParams); request: void; response: PageResponse<JobRead> };
  submitProjectJob: { params: { id: Id }; request: JobSubmitRequest; response: JobAcceptedResponse };
  getJob: { params: { job_id: Id }; request: void; response: JobRead };
  cancelJob: { params: { job_id: Id }; request: void; response: JobControlResponse };
  streamJobEvents: { params: { job_id: Id; last_event_id?: number }; request: void; response: ReadableStream<Uint8Array> };
  retryJob: { params: { job_id: Id }; request: JobRetryRequest; response: JobControlResponse };
  resumeJob: { params: { job_id: Id }; request: ResumeJobRequest; response: JobControlResponse };
  listEvalSets: { params: ({ id: Id; purpose?: "teacher_guard" | "benchmark_gold" | "finance_reference" } & PageParams); request: void; response: PageResponse<EvalSetRead> };
  createEvalSet: { params: { id: Id }; request: EvalSetCreate; response: EvalSetRead };
  getEvalSet: { params: { id: Id }; request: void; response: EvalSetRead };
  listEvalRuns: { params: ({ id: Id; benchmark_id?: Id; target_key?: string; target_status?: EvalTargetStatus } & PageParams); request: void; response: PageResponse<EvalRunRead> };
  getEvalRun: { params: { id: Id }; request: void; response: EvalRunRead };
  listBenchmarks: { params: ({ id: Id; status?: BenchmarkStatus } & PageParams); request: void; response: PageResponse<BenchmarkRead> };
  getBenchmark: { params: { id: Id }; request: void; response: BenchmarkRead };
  getBenchmarkReport: { params: { id: Id }; request: void; response: BenchmarkReportRead };
  listModelRuns: { params: ({ id: Id; status?: JobStatus; backend?: Backend } & PageParams); request: void; response: PageResponse<ModelRunRead> };
  getModelRun: { params: { id: Id }; request: void; response: ModelRunRead };
  listModelRunCheckpoints: { params: { id: Id } & PageParams; request: void; response: PageResponse<CheckpointRead> };
  listAgentPackages: { params: { id: Id } & PageParams; request: void; response: PageResponse<AgentPackageRead> };
  createAgentPackage: { params: { id: Id }; request: AgentPackageCreate; response: AgentPackageRead };
  getAgentPackage: { params: { agent_package_id: Id }; request: void; response: AgentPackageRead };
  runPlayground: { params: { agent_package_id: Id }; request: PlaygroundRunRequest; response: PlaygroundRunResponse };
  createExport: { params: { id: Id }; request: ExportParams; response: JobAcceptedResponse };
  getExport: { params: { job_id: Id }; request: void; response: ExportRead };
  downloadExportArtifact: { params: { job_id: Id }; request: void; response: Blob };
  revealExportArtifact: { params: { job_id: Id }; request: void; response: RevealExportResponse };
  submitHardwareScan: { params: void; request: HardwareScanRequest; response: JobAcceptedResponse };
  getHardwareDoctorResult: { params: void; request: void; response: HardwareProfileRead };
  previewTeacherPacket: { params: { id: Id }; request: TeacherPacketPreviewRequest; response: TeacherPacketPreviewRead };
  approveTeacherPacket: { params: { id: Id }; request: void; response: TeacherPacketApprovalRead };
  listCredentials: { params: void; request: void; response: { items: CredentialRead[] } };
  upsertCredential: { params: { provider: string }; request: CredentialUpsert; response: void };
  deleteCredential: { params: { provider: string }; request: void; response: void };
}

export type ApiParams<TOperation extends ApiOperationId> = ApiOperationMap[TOperation]["params"];
export type ApiRequest<TOperation extends ApiOperationId> = ApiOperationMap[TOperation]["request"];
export type ApiResponse<TOperation extends ApiOperationId> = ApiOperationMap[TOperation]["response"];
export type ApiError = ErrorResponse;

export interface TypedApiClient {
  request<TOperation extends ApiOperationId>(
    operation: TOperation,
    args: {
      params: ApiParams<TOperation>;
      body: ApiRequest<TOperation>;
      idempotencyKey?: string;
    }
  ): Promise<ApiResponse<TOperation>>;
}
