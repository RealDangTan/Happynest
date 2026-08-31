export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }

  static async from(res: Response): Promise<ApiError> {
    let message = res.statusText;
    let detail: unknown;
    try {
      const body = await res.json();
      detail = body?.detail ?? body;
      if (typeof detail === "string") message = detail;
      else if (
        detail &&
        typeof detail === "object" &&
        "message" in detail &&
        typeof detail.message === "string"
      )
        message = detail.message;
      else if (Array.isArray(detail))
        message = detail
          .map((d: { msg?: string }) => d.msg ?? JSON.stringify(d))
          .join("; ");
    } catch {
      /* body không phải JSON — giữ statusText */
    }
    return new ApiError(res.status, message, detail);
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { credentials: "include", ...init });
  if (!res.ok) throw await ApiError.from(res);
  return (await res.json()) as T;
}
