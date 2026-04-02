const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL;
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
    // 纯文本错误直接回退到原文
  }

  return rawText || fallback;
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
  const response = await fetch(makeUrl(path), init);
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
      headers: body === undefined ? init?.headers : { "Content-Type": "application/json", ...init?.headers },
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
