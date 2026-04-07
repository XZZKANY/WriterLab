const DEFAULT_BACKEND_ORIGIN = "http://127.0.0.1:8000";

function isBrowserRuntime() {
  return typeof window !== "undefined";
}

export function getApiBaseUrl() {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }

  return isBrowserRuntime() ? "" : DEFAULT_BACKEND_ORIGIN;
}

function describeApiBaseUrl(apiBaseUrl: string) {
  return apiBaseUrl || "当前前端同源 /api 代理";
}

function makeUrl(path: string) {
  return `${getApiBaseUrl()}${path}`;
}

async function readResponseBody(response: Response) {
  if (response.status === 204) {
    return "";
  }

  return response.text();
}

function pickErrorMessage(rawText: string, fallback: string) {
  if (!rawText) {
    return fallback;
  }

  try {
    const parsed = JSON.parse(rawText) as { detail?: unknown; message?: unknown };
    if (typeof parsed.detail === "string" && parsed.detail.trim()) {
      return parsed.detail;
    }
    if (typeof parsed.message === "string" && parsed.message.trim()) {
      return parsed.message;
    }
  } catch {
    // 纯文本错误直接回退到原始响应体。
  }

  return rawText || fallback;
}

function formatNetworkErrorMessage(fallback: string, apiBaseUrl: string, error: unknown) {
  const originalMessage =
    error instanceof Error && error.message.trim() ? ` 原始错误：${error.message}` : "";
  const targetLabel = describeApiBaseUrl(apiBaseUrl);

  return `${fallback}：无法连接到接口服务（${targetLabel}）。请确认后端服务已启动，并检查 NEXT_PUBLIC_API_BASE_URL 或前端代理配置是否正确。${originalMessage}`;
}

async function parseJsonOrThrow<T>(response: Response, fallback: string) {
  const rawText = await readResponseBody(response);

  if (!response.ok) {
    throw new Error(pickErrorMessage(rawText, fallback));
  }

  if (!rawText) {
    return undefined as T;
  }

  return JSON.parse(rawText) as T;
}

export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
  fallback = "请求失败",
) {
  const apiBaseUrl = getApiBaseUrl();
  const requestUrl = makeUrl(path);

  let response: Response;
  try {
    response = await fetch(requestUrl, init);
  } catch (error) {
    throw new Error(formatNetworkErrorMessage(fallback, apiBaseUrl, error));
  }

  return parseJsonOrThrow<T>(response, fallback);
}

export function apiGet<T>(path: string, fallback?: string) {
  return apiRequest<T>(path, undefined, fallback);
}

export function apiPost<T>(
  path: string,
  body?: unknown,
  fallback?: string,
  init?: Omit<RequestInit, "body" | "method">,
) {
  return apiRequest<T>(
    path,
    {
      method: "POST",
      headers:
        body === undefined
          ? init?.headers
          : { "Content-Type": "application/json", ...init?.headers },
      ...init,
      body: body === undefined ? undefined : JSON.stringify(body),
    },
    fallback,
  );
}

export function apiPut<T>(path: string, body?: unknown, fallback?: string) {
  return apiRequest<T>(
    path,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    },
    fallback,
  );
}

export function apiPatch<T>(path: string, body?: unknown, fallback?: string) {
  return apiRequest<T>(
    path,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    },
    fallback,
  );
}

export function apiDelete<T>(path: string, fallback?: string) {
  return apiRequest<T>(
    path,
    {
      method: "DELETE",
    },
    fallback,
  );
}
