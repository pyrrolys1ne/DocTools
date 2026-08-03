import type { DrivesResult, ExploreResult, JobStatus, ScanResult } from "./types";

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

export function explore(dir: string): Promise<ExploreResult> {
  return get<ExploreResult>(`/api/explore?dir=${encodeURIComponent(dir)}`);
}

export function drives(): Promise<DrivesResult> {
  return get<DrivesResult>("/api/drives");
}

export function scan(sourcePath: string, recursive: boolean): Promise<ScanResult> {
  return post<ScanResult>("/api/scan", { source_path: sourcePath, recursive });
}

export function createJob(opts: {
  source_path: string;
  output_path: string;
  recursive: boolean;
  dry_run: boolean;
  output_is_dir: boolean;
}): Promise<{ id: string }> {
  return post<{ id: string }>("/api/jobs", opts);
}

export function getJob(jobId: string): Promise<JobStatus> {
  return fetch(`/api/jobs/${jobId}`).then((r) => r.json() as Promise<JobStatus>);
}

export function jobWsUrl(jobId: string): string {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.host}/api/jobs/${jobId}/ws`;
}
