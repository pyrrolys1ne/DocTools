import { useCallback, useEffect, useState } from "react";
import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Eraser,
  FileImage,
  FileText,
  Files,
  Image as ImageIcon,
  Loader2,
  Presentation,
  Shrink,
  Split,
  XCircle,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import DirectoryPicker from "./DirectoryPicker";
import { createJob, getJob, jobWsUrl } from "./api";
import { loadRecents, saveRecents, type Recents } from "./recents";
import type {
  BatchOp,
  CreateJobParams,
  FileResult,
  JobStatus,
  Operation,
} from "./types";

type Scope = "dir" | "file";
type Phase = "idle" | "running" | "done" | "failed";
type View = "home" | Operation;
type PickerTarget =
  | { kind: "batch-source" }
  | { kind: "batch-output" }
  | { kind: "merge-source" }
  | { kind: "merge-output" }
  | { kind: "split-source" }
  | { kind: "split-output" }
  | { kind: "pdf-images-source" }
  | { kind: "pdf-images-output" };

/** 去页眉版块的可选目标：去页眉 / 去页脚 / 两者同时。 */
type RemoveTarget = "remove-headers" | "remove-footers" | "remove-headers-footers";

const REMOVE_TARGETS: RemoveTarget[] = [
  "remove-headers",
  "remove-footers",
  "remove-headers-footers",
];

const TARGET_LABEL: Record<RemoveTarget, string> = {
  "remove-headers": "去页眉",
  "remove-footers": "去页脚",
  "remove-headers-footers": "去页眉页脚",
};

const BATCH_EXTS: Record<BatchOp, string> = {
  "remove-headers": ".docx",
  "remove-footers": ".docx",
  "remove-headers-footers": ".docx",
  "word-to-pdf": ".docx,.doc",
  "ppt-to-pdf": ".pptx,.ppt",
  "image-to-pdf": ".png,.jpg,.jpeg,.bmp,.gif,.webp,.tif,.tiff",
  "pdf-to-word": ".pdf",
  "pdf-to-ppt": ".pdf",
  "compress-images": ".png,.jpg,.jpeg,.bmp,.gif,.webp,.tif,.tiff",
};

const HEADER_FOOTER_PLACEHOLDER = {
  dir: "选择包含 .docx 的目录",
  file: "选择或拖入 .docx 文件",
};

const PDF_PLACEHOLDER = {
  dir: "选择包含 .pdf 的目录",
  file: "选择或拖入 .pdf 文件",
};

const IMAGE_PLACEHOLDER = {
  dir: "选择包含图片（png/jpg/…）的目录",
  file: "选择或拖入图片（png/jpg/…）",
};

/** 各批量操作的源路径占位说明（行内显示在输入框内）。 */
const SOURCE_PLACEHOLDER: Record<BatchOp, { dir: string; file: string }> = {
  "remove-headers": HEADER_FOOTER_PLACEHOLDER,
  "remove-footers": HEADER_FOOTER_PLACEHOLDER,
  "remove-headers-footers": HEADER_FOOTER_PLACEHOLDER,
  "word-to-pdf": { dir: "选择包含 .docx/.doc 的目录", file: "选择或拖入 .docx/.doc 文件" },
  "ppt-to-pdf": { dir: "选择包含 .pptx/.ppt 的目录", file: "选择或拖入 .pptx/.ppt 文件" },
  "image-to-pdf": IMAGE_PLACEHOLDER,
  "pdf-to-word": PDF_PLACEHOLDER,
  "pdf-to-ppt": PDF_PLACEHOLDER,
  "compress-images": IMAGE_PLACEHOLDER,
};

const HEADER_FOOTER_OUTPUT = {
  dir: "默认生成到源目录旁的 *_cleaned 文件夹",
  file: "默认生成到源文件旁的 *_cleaned.docx",
};

/** 各批量操作的输出目录占位说明（标注默认生成的位置）。 */
const OUTPUT_PLACEHOLDER: Record<BatchOp, { dir: string; file: string }> = {
  "remove-headers": HEADER_FOOTER_OUTPUT,
  "remove-footers": HEADER_FOOTER_OUTPUT,
  "remove-headers-footers": HEADER_FOOTER_OUTPUT,
  "word-to-pdf": {
    dir: "默认生成到源目录旁的 *_pdf 文件夹",
    file: "默认生成到源文件旁的同名 .pdf",
  },
  "ppt-to-pdf": {
    dir: "默认生成到源目录旁的 *_pdf 文件夹",
    file: "默认生成到源文件旁的同名 .pdf",
  },
  "image-to-pdf": {
    dir: "默认生成到源目录旁 *_images 文件夹的 merged.pdf",
    file: "默认生成到源文件旁 *_images 文件夹的 merged.pdf",
  },
  "pdf-to-word": {
    dir: "默认生成到源目录旁的 *_docx 文件夹",
    file: "默认生成到源文件旁的同名 .docx",
  },
  "pdf-to-ppt": {
    dir: "默认生成到源目录旁的 *_pptx 文件夹",
    file: "默认生成到源文件旁的同名 .pptx",
  },
  "compress-images": {
    dir: "默认生成到源目录旁的 *_compressed 文件夹",
    file: "默认生成到源文件旁的同名文件",
  },
};

/** 首页功能宫格：每个功能一个小方块，点开进入对应页面。 */
/** 首页功能宫格：六项转换置顶成对排列，其余功能紧随，大小一致。 */
const OPERATIONS_META: {
  op: Operation;
  title: string;
  desc: string;
  icon: LucideIcon;
  accent: string;
}[] = [
  { op: "word-to-pdf", title: "Word 转 PDF", desc: ".docx/.doc 转为 PDF", icon: FileText, accent: "from-sky-500 to-blue-600" },
  { op: "pdf-to-word", title: "PDF 转 Word", desc: "PDF 转为可编辑的 Word", icon: FileText, accent: "from-cyan-500 to-teal-500" },
  { op: "ppt-to-pdf", title: "PPT 转 PDF", desc: ".pptx/.ppt 转为 PDF", icon: Presentation, accent: "from-orange-500 to-amber-500" },
  { op: "pdf-to-ppt", title: "PDF 转 PPT", desc: "PDF 每页做成一张幻灯片", icon: Presentation, accent: "from-fuchsia-500 to-purple-500" },
  { op: "image-to-pdf", title: "图片转 PDF", desc: "多张图片合成一个 PDF", icon: ImageIcon, accent: "from-emerald-500 to-teal-500" },
  { op: "pdf-to-images", title: "PDF 转图片", desc: "PDF 每页导出一张 PNG", icon: FileImage, accent: "from-teal-500 to-cyan-600" },
  { op: "merge-pdf", title: "合并 PDF", desc: "把多个 PDF 合成一个", icon: Files, accent: "from-violet-500 to-purple-500" },
  { op: "split-pdf", title: "拆分 PDF", desc: "每页一个或按页码范围", icon: Split, accent: "from-rose-500 to-pink-500" },
  { op: "remove-headers", title: "去页眉 / 去页脚", desc: "移除 Word 页眉、页脚", icon: Eraser, accent: "from-blue-500 to-indigo-500" },
  { op: "compress-images", title: "图片压缩", desc: "压缩图片体积，可选质量", icon: Shrink, accent: "from-amber-500 to-orange-600" },
];

/** 图片压缩质量档位。 */
const QUALITY_LEVELS = [
  { label: "高", value: 90 },
  { label: "中", value: 80 },
  { label: "低", value: 60 },
];

function Field({
  label,
  children,
}: {
  label: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

function CheckOption({
  checked,
  onCheckedChange,
  children,
}: {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  children: React.ReactNode;
}) {
  return (
    <label className="flex cursor-pointer select-none items-center gap-2 text-sm">
      <Checkbox checked={checked} onCheckedChange={onCheckedChange} />
      {children}
    </label>
  );
}

interface BatchFormProps {
  op: BatchOp;
  scope: Scope;
  onScopeChange: (s: Scope) => void;
  source: string;
  onSourceChange: (v: string) => void;
  output: string;
  onOutputChange: (v: string) => void;
  recursive: boolean;
  onRecursiveChange: (v: boolean) => void;
  dragOver: boolean;
  onDragOver: (v: boolean) => void;
  onDrop: (e: React.DragEvent<HTMLDivElement>) => void;
  quality: number;
  onQualityChange: (q: number) => void;
  onStart: () => void;
  busy: boolean;
  onBrowseSource: () => void;
  onBrowseOutput: () => void;
}

function BatchForm(props: BatchFormProps) {
  const {
    op,
    scope,
    onScopeChange,
    source,
    onSourceChange,
    output,
    onOutputChange,
    recursive,
    onRecursiveChange,
    dragOver,
    onDragOver,
    onDrop,
    quality,
    onQualityChange,
    onStart,
    busy,
    onBrowseSource,
    onBrowseOutput,
  } = props;

  return (
    <Card>
      <CardContent className="space-y-4 pt-6">
        {/* 目录批量 / 单个文件 */}
        <div className="inline-flex rounded-lg bg-muted p-[3px]">
          {(["dir", "file"] as Scope[]).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onScopeChange(s)}
              className={cn(
                "rounded-md px-3 py-1 text-sm transition-colors",
                scope === s
                  ? "bg-background font-medium shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {s === "dir" ? "目录批量" : "单个文件"}
            </button>
          ))}
        </div>

        <Field label={scope === "dir" ? "源目录" : "源文件"}>
          <div
            className={cn(
              "flex gap-2 rounded-md transition-shadow",
              scope === "file" && dragOver && "ring-2 ring-ring",
            )}
            onDragOver={(e) => {
              e.preventDefault();
              onDragOver(true);
            }}
            onDragLeave={() => onDragOver(false)}
            onDrop={onDrop}
          >
            <Input
              value={source}
              onChange={(e) => onSourceChange(e.target.value)}
              placeholder={
                scope === "dir" ? SOURCE_PLACEHOLDER[op].dir : SOURCE_PLACEHOLDER[op].file
              }
            />
            <Button type="button" variant="outline" onClick={onBrowseSource}>
              浏览…
            </Button>
          </div>
        </Field>

        <Field label="输出目录">
          <div className="flex gap-2">
            <Input
              value={output}
              onChange={(e) => onOutputChange(e.target.value)}
              placeholder={OUTPUT_PLACEHOLDER[op][scope]}
            />
            <Button type="button" variant="outline" onClick={onBrowseOutput}>
              浏览…
            </Button>
          </div>
        </Field>

        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          {scope === "dir" && (
            <CheckOption checked={recursive} onCheckedChange={onRecursiveChange}>
              递归子目录
            </CheckOption>
          )}
        </div>

        {op === "compress-images" && (
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm text-muted-foreground">压缩质量</span>
            <div className="inline-flex rounded-lg bg-muted p-[3px]">
              {QUALITY_LEVELS.map((lv) => (
                <button
                  key={lv.value}
                  type="button"
                  onClick={() => onQualityChange(lv.value)}
                  className={cn(
                    "rounded-md px-3 py-1 text-sm transition-colors",
                    quality === lv.value
                      ? "bg-background font-medium shadow-sm"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {lv.label}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="flex gap-2 pt-1">
          <Button onClick={onStart} disabled={busy}>
            开始处理
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function App() {
  const [view, setView] = useState<View>("home");
  // 去页眉 / 去页脚 / 两者（同一版块，子切换）
  const [target, setTarget] = useState<RemoveTarget>("remove-headers");
  // 批量表单（去页眉/去页脚 / 各转PDF 共用）
  const [scope, setScope] = useState<Scope>("dir");
  const [source, setSource] = useState("");
  const [output, setOutput] = useState("");
  const [recursive, setRecursive] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [compressQuality, setCompressQuality] = useState(80);
  // 合并 PDF
  const [mergeSources, setMergeSources] = useState<string[]>([]);
  const [mergeOutDir, setMergeOutDir] = useState("");
  const [mergeFileName, setMergeFileName] = useState("merged.pdf");
  // 拆分 PDF
  const [splitSource, setSplitSource] = useState("");
  const [splitOutDir, setSplitOutDir] = useState("");
  const [splitCustom, setSplitCustom] = useState(false);
  const [splitRanges, setSplitRanges] = useState("");
  // PDF 转图片
  const [pdfImagesSource, setPdfImagesSource] = useState("");
  const [pdfImagesOutDir, setPdfImagesOutDir] = useState("");
  // 运行状态
  const [phase, setPhase] = useState<Phase>("idle");
  const [job, setJob] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [picker, setPicker] = useState<PickerTarget | null>(null);

  // 记住上次使用的源路径 / 输出目录（按操作分组，localStorage 持久化）
  const [recents, setRecents] = useState<Recents>(loadRecents);
  const updateRecents = useCallback((fn: (r: Recents) => Recents) => {
    setRecents((prev) => {
      const next = fn(prev);
      saveRecents(next);
      return next;
    });
  }, []);
  const remember = useCallback(
    (kind: "source" | "output", op: string, value: string) => {
      if (!value) return;
      updateRecents((r) => ({ ...r, [kind]: { ...r[kind], [op]: value } }));
    },
    [updateRecents],
  );

  // 进入某个功能页时回填该功能上次使用的路径（去页眉/去页脚按 target 区分记忆）
  useEffect(() => {
    if (view === "home") return;
    if (view === "merge-pdf") {
      setMergeOutDir(recents.output?.["merge-pdf"] ?? "");
      setMergeFileName(recents.mergeFileName ?? "merged.pdf");
    } else if (view === "split-pdf") {
      setSplitOutDir(recents.output?.["split-pdf"] ?? "");
    } else if (view === "pdf-to-images") {
      setPdfImagesSource(recents.source?.["pdf-to-images"] ?? "");
      setPdfImagesOutDir(recents.output?.["pdf-to-images"] ?? "");
    } else {
      const key = view === "remove-headers" ? target : view;
      setSource(recents.source?.[key] ?? "");
      setOutput(recents.output?.[key] ?? "");
    }
    // 仅在切换页面 / 切换去页眉去页脚时回填
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, target]);

  // 当前页面使用的批量操作：去页眉版块内由 target 决定（去页眉/去页脚）
  const batchOp: BatchOp =
    view === "remove-headers"
      ? target
      : view === "word-to-pdf" ||
          view === "ppt-to-pdf" ||
          view === "image-to-pdf" ||
          view === "pdf-to-word" ||
          view === "pdf-to-ppt" ||
          view === "compress-images"
        ? view
        : "remove-headers";
  const showTargetToggle = view === "remove-headers";

  const progress = job && job.total > 0 ? (job.done / job.total) * 100 : 0;
  const busy = phase === "running";
  const okCount = job ? job.results.filter((r) => r.ok).length : 0;
  const failCount = job ? job.results.length - okCount : 0;

  // 启动任务并订阅进度（WebSocket 实时；失败则回退轮询）
  const startJob = useCallback(async (params: CreateJobParams) => {
    setError(null);
    setJob(null);
    setPhase("running");
    try {
      const { id } = await createJob(params);

      const ws = new WebSocket(jobWsUrl(id));
      ws.onmessage = (ev) => {
        const data = JSON.parse(ev.data) as JobStatus;
        setJob(data);
        if (data.status === "done" || data.status === "failed") {
          ws.close();
          getJob(id).then(setJob); // 拉取含逐文件结果的完整快照
          setPhase(data.status === "done" ? "done" : "failed");
        }
      };
      ws.onerror = () => {
        const timer = window.setInterval(async () => {
          const data = await getJob(id);
          setJob(data);
          if (data.status === "done" || data.status === "failed") {
            window.clearInterval(timer);
            setPhase(data.status === "done" ? "done" : "failed");
          }
        }, 500);
      };
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setPhase("idle");
    }
  }, []);

  const onStartBatch = () => {
    if (!source.trim()) {
      setError("请选择源目录或文件");
      return;
    }
    remember("source", batchOp, source);
    remember("output", batchOp, output);
    startJob({
      operation: batchOp,
      source_path: source,
      output_path: output,
      recursive,
      output_is_dir: scope === "file",
      ...(batchOp === "compress-images" ? { quality: compressQuality } : {}),
    });
  };

  const onStartMerge = () => {
    if (mergeSources.length === 0) {
      setError("请选择要合并的 PDF 文件");
      return;
    }
    if (!mergeOutDir.trim()) {
      setError("请选择输出目录");
      return;
    }
    remember("output", "merge-pdf", mergeOutDir);
    updateRecents((r) => ({ ...r, mergeFileName: mergeFileName.trim() || "merged.pdf" }));
    startJob({
      operation: "merge-pdf",
      source_path: "",
      output_path: `${mergeOutDir.replace(/[\\/]+$/, "")}/${mergeFileName.trim() || "merged.pdf"}`,
      recursive: false,
      output_is_dir: false,
      sources: mergeSources,
    });
  };

  const onStartSplit = () => {
    if (!splitSource.trim()) {
      setError("请选择要拆分的 PDF 文件");
      return;
    }
    if (!splitOutDir.trim()) {
      setError("请选择输出目录");
      return;
    }
    remember("output", "split-pdf", splitOutDir);
    startJob({
      operation: "split-pdf",
      source_path: splitSource,
      output_path: splitOutDir,
      recursive: false,
      output_is_dir: false,
      page_ranges: splitCustom ? splitRanges : "",
    });
  };

  const onStartPdfImages = () => {
    if (!pdfImagesSource.trim()) {
      setError("请选择要转图片的 .pdf 文件");
      return;
    }
    remember("source", "pdf-to-images", pdfImagesSource);
    remember("output", "pdf-to-images", pdfImagesOutDir);
    startJob({
      operation: "pdf-to-images",
      source_path: pdfImagesSource,
      output_path: pdfImagesOutDir,
      recursive: false,
      output_is_dir: false,
    });
  };

  // 单文件拖拽：Firefox 通过 text/plain 提供完整路径；Chrome 出于隐私
  // 不暴露绝对路径，给出友好提示引导使用「浏览」。
  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const text = e.dataTransfer.getData("text/plain").trim();
    if (/\.(docx|doc|pptx|ppt|pdf)$/i.test(text)) {
      setSource(text);
      return;
    }
    const name = e.dataTransfer.files?.[0]?.name ?? "";
    if (/\.(docx|doc|pptx|ppt|pdf)$/i.test(name)) {
      setError(`已检测到「${name}」，但浏览器无法提供完整路径。请使用「浏览」选择该文件。`);
    } else {
      setError("请拖入支持的文档文件");
    }
  }, []);

  // ===== 目录/文件选择弹窗 =====
  const renderPicker = () => {
    if (!picker) return null;
    const k = picker.kind;
    let initial = "";
    let title = "";
    let exts = ".docx";
    let multi = false;

    if (k === "batch-source") {
      initial = source;
      title = scope === "file" ? "选择源文件" : "选择源目录";
      exts = BATCH_EXTS[batchOp];
    } else if (k === "batch-output") {
      initial = output;
      title = "选择输出目录";
    } else if (k === "merge-source") {
      title = "选择要合并的 PDF 文件";
      exts = ".pdf";
      multi = true;
    } else if (k === "merge-output") {
      initial = mergeOutDir;
      title = "选择输出目录";
    } else if (k === "split-source") {
      initial = splitSource;
      title = "选择要拆分的 PDF 文件";
      exts = ".pdf";
    } else if (k === "pdf-images-source") {
      initial = pdfImagesSource;
      title = "选择要转图片的 PDF 文件";
      exts = ".pdf";
    } else if (k === "pdf-images-output") {
      initial = pdfImagesOutDir;
      title = "选择输出目录";
    } else {
      initial = splitOutDir;
      title = "选择输出目录";
    }

    return (
      <DirectoryPicker
        initial={initial}
        title={title}
        exts={exts}
        multi={multi}
        onSelect={(dir) => {
          if (k === "batch-source" && scope === "dir") {
            setSource(dir);
            remember("source", batchOp, dir);
          } else if (k === "batch-output") {
            setOutput(dir);
            remember("output", batchOp, dir);
          } else if (k === "merge-output") {
            setMergeOutDir(dir);
            remember("output", "merge-pdf", dir);
          } else if (k === "split-output") {
            setSplitOutDir(dir);
            remember("output", "split-pdf", dir);
          } else if (k === "pdf-images-output") {
            setPdfImagesOutDir(dir);
            remember("output", "pdf-to-images", dir);
          }
          setPicker(null);
        }}
        onSelectFile={
          (k === "batch-source" && scope === "file") ||
          k === "split-source" ||
          k === "pdf-images-source"
            ? (path) => {
                if (k === "batch-source" && scope === "file") {
                  setSource(path);
                  remember("source", batchOp, path);
                } else if (k === "split-source") {
                  setSplitSource(path);
                  remember("source", "split-pdf", path);
                } else if (k === "pdf-images-source") {
                  setPdfImagesSource(path);
                  remember("source", "pdf-to-images", path);
                }
                setPicker(null);
              }
            : undefined
        }
        onSelectFiles={(paths) => {
          setMergeSources(paths);
          setPicker(null);
        }}
        onClose={() => setPicker(null)}
      />
    );
  };

  const meta = OPERATIONS_META.find((m) => m.op === view);

  return (
    <main className="mx-auto w-full max-w-[780px] px-4 pb-20 pt-8 sm:px-6">
      <header className="flex items-center gap-3.5">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-linear-to-br from-primary to-indigo-500 text-xl font-extrabold text-primary-foreground shadow-md">
          D
        </div>
        <div>
          <h1 className="flex items-center gap-2 text-xl font-bold tracking-tight">
            DocTools
            <Badge variant="secondary" className="font-medium">
              v0.3
            </Badge>
          </h1>
          <p className="text-sm text-muted-foreground">本地文档处理工具</p>
        </div>
      </header>

      {view === "home" ? (
        /* ===== 首页：功能宫格 ===== */
        <section className="mt-6">
          <p className="mb-3 text-sm text-muted-foreground">选择一个功能开始：</p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {OPERATIONS_META.map((m) => (
              <button
                key={m.op}
                type="button"
                onClick={() => setView(m.op)}
                className="group flex items-center gap-4 rounded-xl border bg-card p-4 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/50 hover:shadow-md"
              >
                <div
                  className={cn(
                    "flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-linear-to-br text-white shadow-sm",
                    m.accent,
                  )}
                >
                  <m.icon className="size-6" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold">{m.title}</p>
                  <p className="truncate text-xs text-muted-foreground">{m.desc}</p>
                </div>
                <ChevronRight className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
              </button>
            ))}
          </div>
          <p className="mt-10 text-center text-xs text-muted-foreground">
            处理在本地完成，文件不会上传。
          </p>
        </section>
      ) : (
        /* ===== 功能页 ===== */
        <>
          <div className="mt-4">
            <button
              type="button"
              onClick={() => setView("home")}
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              <ChevronLeft className="size-4" /> 返回
            </button>
            {meta && (
              <div className="mt-2 flex items-center gap-3">
                <div
                  className={cn(
                    "flex h-9 w-9 items-center justify-center rounded-lg bg-linear-to-br text-white shadow-sm",
                    meta.accent,
                  )}
                >
                  <meta.icon className="size-4" />
                </div>
                <h2 className="text-lg font-bold">{meta.title}</h2>
              </div>
            )}
          </div>

          {view === "merge-pdf" ? (
            <Card className="mt-4">
              <CardContent className="space-y-4 pt-6">
                <Field label="源文件">
                  <div className="flex gap-2">
                    <Input
                      value={mergeSources.length > 0 ? `已选 ${mergeSources.length} 个 PDF` : ""}
                      readOnly
                      placeholder="点击浏览，多选要合并的 PDF"
                      className="cursor-pointer"
                      onClick={() => setPicker({ kind: "merge-source" })}
                    />
                    <Button
                      variant="outline"
                      onClick={() => setPicker({ kind: "merge-source" })}
                    >
                      浏览…
                    </Button>
                  </div>
                </Field>
                {mergeSources.length > 0 && (
                  <p className="break-all text-xs text-muted-foreground">
                    已选：{mergeSources.map((p) => p.split(/[\\/]/).pop()).join("、")}
                  </p>
                )}
                <Field label="输出目录">
                  <div className="flex gap-2">
                    <Input
                      value={mergeOutDir}
                      onChange={(e) => setMergeOutDir(e.target.value)}
                      placeholder="合并结果保存到该目录"
                    />
                    <Button variant="outline" onClick={() => setPicker({ kind: "merge-output" })}>
                      浏览…
                    </Button>
                  </div>
                </Field>
                <Field label="合并后文件名">
                  <Input
                    value={mergeFileName}
                    onChange={(e) => setMergeFileName(e.target.value)}
                    placeholder="默认 merged.pdf"
                  />
                </Field>
                <div className="pt-1">
                  <Button onClick={onStartMerge} disabled={busy}>
                    开始合并
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : view === "split-pdf" ? (
            <Card className="mt-4">
              <CardContent className="space-y-4 pt-6">
                <Field label="源文件">
                  <div className="flex gap-2">
                    <Input
                      value={splitSource}
                      onChange={(e) => setSplitSource(e.target.value)}
                      placeholder="选择要拆分的 .pdf 文件"
                    />
                    <Button variant="outline" onClick={() => setPicker({ kind: "split-source" })}>
                      浏览…
                    </Button>
                  </div>
                </Field>
                <Field label="输出目录">
                  <div className="flex gap-2">
                    <Input
                      value={splitOutDir}
                      onChange={(e) => setSplitOutDir(e.target.value)}
                      placeholder="默认生成到源文件旁的 *_split 文件夹"
                    />
                    <Button variant="outline" onClick={() => setPicker({ kind: "split-output" })}>
                      浏览…
                    </Button>
                  </div>
                </Field>
                <div className="space-y-2">
                  <CheckOption checked={splitCustom} onCheckedChange={setSplitCustom}>
                    自定义页码范围
                  </CheckOption>
                  <p className="text-xs text-muted-foreground">
                    不勾选时每页拆成一个文件
                  </p>
                  {splitCustom && (
                    <Input
                      value={splitRanges}
                      onChange={(e) => setSplitRanges(e.target.value)}
                      placeholder="如 1-3,5,8-12"
                    />
                  )}
                </div>
                <div className="pt-1">
                  <Button onClick={onStartSplit} disabled={busy}>
                    开始拆分
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : view === "pdf-to-images" ? (
            <Card className="mt-4">
              <CardContent className="space-y-4 pt-6">
                <Field label="源文件">
                  <div className="flex gap-2">
                    <Input
                      value={pdfImagesSource}
                      onChange={(e) => setPdfImagesSource(e.target.value)}
                      placeholder="选择要转图片的 .pdf 文件"
                    />
                    <Button
                      variant="outline"
                      onClick={() => setPicker({ kind: "pdf-images-source" })}
                    >
                      浏览…
                    </Button>
                  </div>
                </Field>
                <Field label="输出目录">
                  <div className="flex gap-2">
                    <Input
                      value={pdfImagesOutDir}
                      onChange={(e) => setPdfImagesOutDir(e.target.value)}
                      placeholder="默认生成到源文件旁的 *_images 文件夹"
                    />
                    <Button
                      variant="outline"
                      onClick={() => setPicker({ kind: "pdf-images-output" })}
                    >
                      浏览…
                    </Button>
                  </div>
                </Field>
                <div className="pt-1">
                  <Button onClick={onStartPdfImages} disabled={busy}>
                    开始转换
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="mt-4 space-y-4">
              {showTargetToggle && (
                <div className="inline-flex rounded-lg bg-muted p-[3px]">
                  {REMOVE_TARGETS.map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setTarget(t)}
                      className={cn(
                        "rounded-md px-3 py-1 text-sm transition-colors",
                        target === t
                          ? "bg-background font-medium shadow-sm"
                          : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {TARGET_LABEL[t]}
                    </button>
                  ))}
                </div>
              )}
              <BatchForm
                op={batchOp}
                scope={scope}
                onScopeChange={setScope}
                source={source}
                onSourceChange={setSource}
                output={output}
                onOutputChange={setOutput}
                recursive={recursive}
                onRecursiveChange={setRecursive}
                dragOver={dragOver}
                onDragOver={setDragOver}
                onDrop={handleDrop}
                quality={compressQuality}
                onQualityChange={setCompressQuality}
                onStart={onStartBatch}
                busy={busy}
                onBrowseSource={() => setPicker({ kind: "batch-source" })}
                onBrowseOutput={() => setPicker({ kind: "batch-output" })}
              />
            </div>
          )}

          {error && (
            <div className="mt-4 flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              <XCircle className="mt-0.5 size-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* ===== 运行进度 ===== */}
          {phase === "running" && job && (
            <Card className="mt-4">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Loader2 className="size-4 animate-spin" /> 处理中… {job.done}/{job.total}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Progress
                  value={progress}
                  indicatorClassName="bg-linear-to-r from-primary to-fuchsia-500"
                />
                {job.current && (
                  <p className="truncate text-sm text-muted-foreground">当前：{job.current}</p>
                )}
              </CardContent>
            </Card>
          )}

          {/* ===== 完成 ===== */}
          {phase === "done" && job && (
            <Card className="mt-4">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <CheckCircle2 className="size-4 text-success" /> 完成
                </CardTitle>
                <div className="flex flex-wrap gap-2 pt-1">
                  <Badge variant="secondary" className="tabular">
                    共 {job.total}
                  </Badge>
                  <Badge variant="success" className="tabular">
                    ✓ 成功 {okCount}
                  </Badge>
                  {failCount > 0 && (
                    <Badge variant="destructive" className="tabular">
                      ✕ 失败 {failCount}
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {job.results.length > 0 ? (
                  <ResultList results={job.results} />
                ) : (
                  <p className="text-sm text-muted-foreground">无处理结果。</p>
                )}
              </CardContent>
            </Card>
          )}

          {/* ===== 失败 ===== */}
          {phase === "failed" && job && (
            <Card className="mt-4 border-destructive/50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <XCircle className="size-4 text-destructive" /> 处理失败
                </CardTitle>
                <CardDescription>{job.error ?? "未知错误"}</CardDescription>
              </CardHeader>
              {job.results.length > 0 && (
                <CardContent>
                  <ResultList results={job.results} />
                </CardContent>
              )}
            </Card>
          )}
        </>
      )}

      {renderPicker()}
    </main>
  );
}

function ResultList({ results }: { results: FileResult[] }) {
  return (
    <ScrollArea className="h-[280px] rounded-md border">
      <ul className="divide-y">
        {results.map((r) => (
          <li key={r.src} className="flex items-center justify-between gap-3 px-3 py-2">
            <span className="flex min-w-0 items-center gap-2 font-mono text-xs">
              <FileText className="size-4 shrink-0 text-muted-foreground" />
              <span className="truncate">{r.src}</span>
            </span>
            {r.ok ? (
              <Badge variant="success" className="shrink-0">
                ✓ OK
              </Badge>
            ) : (
              <Badge variant="destructive" className="max-w-[55%] shrink-0 truncate">
                ✕ {r.error ?? "FAIL"}
              </Badge>
            )}
          </li>
        ))}
      </ul>
    </ScrollArea>
  );
}
