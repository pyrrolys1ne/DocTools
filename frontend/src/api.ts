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

export function explore(dir: string, exts = ".docx"): Promise<ExploreResult> {
  return get<ExploreResult>(
    `/api/explore?dir=${encodeURIComponent(dir)}&exts=${encodeURIComponent(exts)}`,
  );
}

export function drives(): Promise<DrivesResult> {
  return get<DrivesResult>("/api/drives");
}

export function createJob(opts: CreateJobParams): Promise<{ id: string }> {
  return post<{ id: string }>("/api/jobs", opts);
}

export function getJob(jobId: string): Promise<JobStatus> {
  return fetch(`/api/jobs/${jobId}`).then((r) => r.json() as Promise<JobStatus>);
}

export function jobWsUrl(jobId: string): string {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.host}/api/jobs/${jobId}/ws`;
}
