export interface ApiBootstrap {
  baseUrl: string;
  token: string;
}

type TauriInvoke = <T>(command: string, args?: Record<string, unknown>) => Promise<T>;

interface TauriWindow {
  __TAURI__?: {
    core?: {
      invoke?: TauriInvoke;
    };
    tauri?: {
      invoke?: TauriInvoke;
    };
  };
}

function tauriInvoke(): TauriInvoke {
  const tauriWindow = window as Window & TauriWindow;
  const invoke = tauriWindow.__TAURI__?.core?.invoke ?? tauriWindow.__TAURI__?.tauri?.invoke;
  if (!invoke) {
    throw new Error("TAURI_BOOTSTRAP_UNAVAILABLE");
  }
  return invoke;
}

function normalizeBootstrap(value: unknown): ApiBootstrap {
  if (!value || typeof value !== "object") {
    throw new Error("TAURI_BOOTSTRAP_INVALID");
  }

  const record = value as Record<string, unknown>;
  const baseUrl = record.baseUrl ?? record.base_url;
  const token = record.token;

  if (typeof baseUrl !== "string" || typeof token !== "string" || !baseUrl || !token) {
    throw new Error("TAURI_BOOTSTRAP_INVALID");
  }

  return { baseUrl, token };
}

export async function getApiBootstrap(): Promise<ApiBootstrap> {
  const invoke = tauriInvoke();
  return normalizeBootstrap(await invoke<unknown>("get_api_bootstrap"));
}
