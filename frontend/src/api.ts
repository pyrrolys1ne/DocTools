import type {
  CreateJobParams,
  DrivesResult,
  ExploreResult,
  JobStatus,
} from "./types";

async function get<T>(path: string): Promise<T> {
  const resp = await fetch(path);
  if (!resp.ok) {
    throw new Error(`请求失败 ${resp.status}: ${await resp.text()}`);
  }
  return resp.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const resp = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    throw new Error(`请求失败 ${resp.status}: ${await resp.text()}`);
  }
  return resp.json() as Promise<T>;
}

/**
 * API 基地址。本地工具默认同源（由后端托管前端）；前后端分离部署时
 * 用 VITE_API_BASE 指向后端，如 VITE_API_BASE=https://api.example.com/api/v1。
 */
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

export function explore(dir: string, exts = ".docx"): Promise<ExploreResult> {
  return get<ExploreResult>(
    `${API_BASE}/explore?dir=${encodeURIComponent(dir)}&exts=${encodeURIComponent(exts)}`,
  );
}

export function drives(): Promise<DrivesResult> {
  return get<DrivesResult>(`${API_BASE}/drives`);
}

export function createJob(opts: CreateJobParams): Promise<{ id: string }> {
  return post<{ id: string }>(`${API_BASE}/jobs`, opts);
}

export function getJob(jobId: string): Promise<JobStatus> {
  return fetch(`${API_BASE}/jobs/${jobId}`).then((r) => r.json() as Promise<JobStatus>);
}

export function jobWsUrl(jobId: string): string {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.host}${API_BASE}/jobs/${jobId}/ws`;
}
