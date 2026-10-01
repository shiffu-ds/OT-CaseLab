export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
export async function api<T>(path: string, options: RequestInit = {}, csrf?: string): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  if (csrf && options.method && options.method !== 'GET') headers.set('X-CSRF-Token', csrf);
  const response = await fetch(`/api/v1${path}`, { ...options, headers, credentials: 'same-origin', cache: 'no-store' });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    let detail = data?.detail || data?.error || 'The request could not be completed. Please try again.';
    if (Array.isArray(detail)) detail = detail.map((item: { msg?: string }) => item.msg || 'Invalid field').join('; ');
    if (typeof detail !== 'string') detail = detail?.message || 'The request could not be completed.';
    throw new ApiError(response.status, detail);
  }
  return data as T;
}
export const json = (method: string, value?: unknown): RequestInit => ({ method, ...(value === undefined ? {} : { body: JSON.stringify(value) }) });
export function printable(value: unknown): string {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.map(printable).filter(Boolean).join(' · ');
  if (typeof value === 'object') {
    const object = value as Record<string, unknown>;
    return String(object.text || object.description || object.criterion || object.label || object.statement || object.id || JSON.stringify(value));
  }
  return String(value);
}
