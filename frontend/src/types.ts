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

export interface FileResult {
  src: string;
  dst: string;
  ok: boolean;
  error: string | null;
}

export type Operation =
  | "remove-headers"
  | "remove-footers"
  | "remove-headers-footers"
  | "word-to-pdf"
  | "ppt-to-pdf"
  | "image-to-pdf"
  | "pdf-to-word"
  | "pdf-to-ppt"
  | "pdf-to-images"
  | "compress-images"
  | "merge-pdf"
  | "split-pdf";

/** 使用批量表单（源目录/单文件 + 递归）的操作。 */
export type BatchOp =
  | "remove-headers"
  | "remove-footers"
  | "remove-headers-footers"
  | "word-to-pdf"
  | "ppt-to-pdf"
  | "image-to-pdf"
  | "pdf-to-word"
  | "pdf-to-ppt"
  | "compress-images";

export interface CreateJobParams {
  operation: Operation;
  source_path: string;
  output_path: string;
  recursive: boolean;
  output_is_dir: boolean;
  sources?: string[];
  page_ranges?: string;
  /** 图片压缩：JPEG 重编码质量（1-100）。 */
  quality?: number;
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
