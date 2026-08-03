export interface ExploreResult {
  dir: string;
  parent: string | null;
  dirs: string[];
  files: string[];
  /** 目录可访问但无法完整读取时的提示（如权限受限的系统目录）。 */
  error: string | null;
}

export interface SpecialFolder {
  name: string;
  path: string;
}

export interface DrivesResult {
  drives: string[];
  special: SpecialFolder[];
}

export interface ScanFile {
  name: string;
  size: number;
}

export interface ScanResult {
  source_path: string;
  kind: "file" | "dir";
  recursive: boolean;
  files: ScanFile[];
}

export interface FileResult {
  src: string;
  dst: string;
  ok: boolean;
  error: string | null;
}

export type JobState = "pending" | "running" | "done" | "failed";

export interface JobStatus {
  id: string;
  status: JobState;
  total: number;
  done: number;
  current: string | null;
  error: string | null;
  results: FileResult[];
}
