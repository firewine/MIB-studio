import assert from "node:assert/strict";
import test from "node:test";
import { ApiClientError, createApiClient } from "./apiClient.mjs";

test("createApiClient attaches bearer and idempotency headers", async () => {
  const seen = {};
  const api = createApiClient({ baseUrl: "http://local.test/", token: "secret" }, async (url, init) => {
    seen.url = url;
    seen.init = init;
    return response(202, { job_id: "job_1", status: "SUCCEEDED" });
  });

  await api.request("submitHardwareScan", {
    body: { dry_run: true, target_backend: "auto" },
    idempotencyKey: "idem-1",
  });

  assert.equal(seen.url, "http://local.test/hardware-doctor/scan");
  assert.equal(seen.init.headers.Authorization, "Bearer secret");
  assert.equal(seen.init.headers["Idempotency-Key"], "idem-1");
  assert.equal(seen.init.headers["Content-Type"], "application/json");
});

test("createApiClient builds path and query params", async () => {
  let requestedUrl = "";
  const api = createApiClient({ baseUrl: "http://local.test", token: "secret" }, async (url) => {
    requestedUrl = url;
    return response(200, { items: [] });
  });
  await api.request("listDatasets", { params: { id: "proj 1", limit: 20 } });
  assert.equal(requestedUrl, "http://local.test/projects/proj%201/datasets?limit=20");
});

test("createApiClient raises typed API errors", async () => {
  const api = createApiClient({ baseUrl: "http://local.test", token: "secret" }, async () =>
    response(409, { error_code: "MILESTONE_LOCKED", message: "locked", details: {}, trace_id: "t1" }),
  );
  await assert.rejects(() => api.request("getJob", { params: { job_id: "job_1" } }), (error) => {
    assert.equal(error instanceof ApiClientError, true);
    assert.equal(error.status, 409);
    assert.equal(error.payload.error_code, "MILESTONE_LOCKED");
    return true;
  });
});

function response(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status >= 400 ? "error" : "ok",
    headers: new Map(),
    async json() {
      return body;
    },
  };
}
