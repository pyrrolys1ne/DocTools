import { useCallback, useState } from "react";
import {
  CheckCircle2,
  Eraser,
  FileText,
  Files,
  Image as ImageIcon,
  Loader2,
  Presentation,
  Split,
  XCircle,
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
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import DirectoryPicker from "./DirectoryPicker";
import { createJob, getJob, jobWsUrl, scan } from "./api";
import type {
  BatchOp,
  CreateJobParams,
  FileResult,
  JobStatus,
  Operation,
  ScanFile,
} from "./types";

type Scope = "dir" | "file";
type Phase = "idle" | "scanning" | "preview" | "running" | "done" | "failed";
type PickerTarget =
  | { kind: "batch-source" }
  | { kind: "batch-output" }
  | { kind: "merge-source" }
  | { kind: "merge-output" }
  | { kind: "split-source" }
  | { kind: "split-output" };

const BATCH_EXTS: Record<BatchOp, string> = {
  "remove-headers": ".docx",
  "word-to-pdf": ".docx,.doc",
  "ppt-to-pdf": ".pptx,.ppt",
  "image-to-pdf": ".png,.jpg,.jpeg,.bmp,.gif,.webp,.tif,.tiff",
};

const SOURCE_HINT: Record<BatchOp, { dir: string; file: string }> = {
  "remove-headers": { dir: ".docx", file: ".docx" },
  "word-to-pdf": { dir: "含 .docx/.doc", file: ".docx/.doc" },
  "ppt-to-pdf": { dir: "含 .pptx/.ppt", file: ".pptx/.ppt" },
  "image-to-pdf": { dir: "含 png/jpg/…", file: "png/jpg/…" },
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

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
  dryRun: boolean;
  onDryRunChange: (v: boolean) => void;
  mergeImages: boolean;
  onMergeImagesChange: (v: boolean) => void;
  dragOver: boolean;
  onDragOver: (v: boolean) => void;
  onDrop: (e: React.DragEvent<HTMLDivElement>) => void;
  showScan: boolean;
  scanning: boolean;
  onScan: () => void;
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
    dryRun,
    onDryRunChange,
    mergeImages,
    onMergeImagesChange,
    dragOver,
    onDragOver,
    onDrop,
    showScan,
    scanning,
    onScan,
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

        <Field
          label={
            scope === "dir"
              ? `源目录（${SOURCE_HINT[op].dir}）`
              : `源文件（${SOURCE_HINT[op].file}，可直接拖入）`
          }
        >
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
              placeholder="例如 D:/Projects/DocTools/docs"
            />
            <Button type="button" variant="outline" onClick={onBrowseSource}>
              浏览…
            </Button>
          </div>
        </Field>

        <Field
          label={
            <span>
              输出目录{" "}
              <span className="font-normal text-muted-foreground">
                （留空自动生成 *_cleaned）
              </span>
            </span>
          }
        >
          <div className="flex gap-2">
            <Input
              value={output}
              onChange={(e) => onOutputChange(e.target.value)}
              placeholder="留空则使用默认"
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
          <CheckOption checked={dryRun} onCheckedChange={onDryRunChange}>
            仅预览（dry-run）
          </CheckOption>
          {op === "image-to-pdf" && (
            <CheckOption checked={mergeImages} onCheckedChange={onMergeImagesChange}>
              合成一个 PDF（所有图片合并成一个文件）
            </CheckOption>
          )}
        </div>

        <div className="flex gap-2 pt-1">
          {showScan && (
            <Button variant="outline" onClick={onScan} disabled={busy}>
              {scanning ? (
                <>
                  <Loader2 className="animate-spin" /> 扫描中…
                </>
              ) : (
                "扫描"
              )}
            </Button>
          )}
          <Button onClick={onStart} disabled={busy}>
            开始处理
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function App() {
  const [operation, setOperation] = useState<Operation>("remove-headers");
  // 批量表单（去页眉 / 转PDF 共用）
  const [scope, setScope] = useState<Scope>("dir");
  const [source, setSource] = useState("");
  const [output, setOutput] = useState("");
  const [recursive, setRecursive] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [mergeImages, setMergeImages] = useState(false);
  // 合并 PDF
  const [mergeSources, setMergeSources] = useState<string[]>([]);
  const [mergeOutDir, setMergeOutDir] = useState("");
  const [mergeFileName, setMergeFileName] = useState("merged.pdf");
  // 拆分 PDF
  const [splitSource, setSplitSource] = useState("");
  const [splitOutDir, setSplitOutDir] = useState("");
  const [splitCustom, setSplitCustom] = useState(false);
  const [splitRanges, setSplitRanges] = useState("");
  // 运行状态
  const [files, setFiles] = useState<ScanFile[]>([]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [job, setJob] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [picker, setPicker] = useState<PickerTarget | null>(null);

  const batchOp: BatchOp =
    operation === "merge-pdf" || operation === "split-pdf"
      ? "remove-headers"
      : operation;
  const showScan = batchOp === "remove-headers" && scope === "dir";

  const totalSize = files.reduce((sum, f) => sum + f.size, 0);
  const progress = job && job.total > 0 ? (job.done / job.total) * 100 : 0;
  const busy = phase === "running" || phase === "scanning";
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

  const onScan = useCallback(async () => {
    setError(null);
    setPhase("scanning");
    try {
      const result = await scan(source, recursive);
      setFiles(result.files);
      setPhase("preview");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setPhase("idle");
    }
  }, [source, recursive]);

  const onStartBatch = () => {
    if (!source.trim()) {
      setError("请选择源目录或文件");
      return;
    }
    startJob({
      operation: batchOp,
      source_path: source,
      output_path: output,
      recursive,
      dry_run: dryRun,
      output_is_dir: scope === "file",
      ...(batchOp === "image-to-pdf" ? { merge_images: mergeImages } : {}),
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
    startJob({
      operation: "merge-pdf",
      source_path: "",
      output_path: `${mergeOutDir.replace(/[\\/]+$/, "")}/${mergeFileName.trim() || "merged.pdf"}`,
      recursive: false,
      dry_run: false,
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
    startJob({
      operation: "split-pdf",
      source_path: splitSource,
      output_path: splitOutDir,
      recursive: false,
      dry_run: false,
      output_is_dir: false,
      page_ranges: splitCustom ? splitRanges : "",
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
          if (k === "batch-source" && scope === "dir") setSource(dir);
          else if (k === "batch-output") setOutput(dir);
          else if (k === "merge-output") setMergeOutDir(dir);
          else if (k === "split-output") setSplitOutDir(dir);
          setPicker(null);
        }}
        onSelectFile={
          (k === "batch-source" && scope === "file") || k === "split-source"
            ? (path) => {
                if (k === "batch-source" && scope === "file") setSource(path);
                else if (k === "split-source") setSplitSource(path);
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
          <p className="text-sm text-muted-foreground">
            去页眉 · 转 PDF · 合并/拆分 PDF
          </p>
        </div>
      </header>

      <Tabs
        value={operation}
        onValueChange={(v) => setOperation(v as Operation)}
        className="mt-4"
      >
        <TabsList className="max-w-full overflow-x-auto">
          <TabsTrigger value="remove-headers">
            <Eraser /> 去页眉
          </TabsTrigger>
          <TabsTrigger value="word-to-pdf">
            <FileText /> Word 转 PDF
          </TabsTrigger>
          <TabsTrigger value="ppt-to-pdf">
            <Presentation /> PPT 转 PDF
          </TabsTrigger>
          <TabsTrigger value="image-to-pdf">
            <ImageIcon /> 图片转 PDF
          </TabsTrigger>
          <TabsTrigger value="merge-pdf">
            <Files /> 合并 PDF
          </TabsTrigger>
          <TabsTrigger value="split-pdf">
            <Split /> 拆分 PDF
          </TabsTrigger>
        </TabsList>

        <TabsContent value="remove-headers">
          <BatchForm
            op="remove-headers"
            scope={scope}
            onScopeChange={setScope}
            source={source}
            onSourceChange={setSource}
            output={output}
            onOutputChange={setOutput}
            recursive={recursive}
            onRecursiveChange={setRecursive}
            dryRun={dryRun}
            onDryRunChange={setDryRun}
            mergeImages={mergeImages}
            onMergeImagesChange={setMergeImages}
            dragOver={dragOver}
            onDragOver={setDragOver}
            onDrop={handleDrop}
            showScan={showScan}
            scanning={phase === "scanning"}
            onScan={onScan}
            onStart={onStartBatch}
            busy={busy}
            onBrowseSource={() => setPicker({ kind: "batch-source" })}
            onBrowseOutput={() => setPicker({ kind: "batch-output" })}
          />
        </TabsContent>

        <TabsContent value="word-to-pdf">
          <BatchForm
            op="word-to-pdf"
            scope={scope}
            onScopeChange={setScope}
            source={source}
            onSourceChange={setSource}
            output={output}
            onOutputChange={setOutput}
            recursive={recursive}
            onRecursiveChange={setRecursive}
            dryRun={dryRun}
            onDryRunChange={setDryRun}
            mergeImages={mergeImages}
            onMergeImagesChange={setMergeImages}
            dragOver={dragOver}
            onDragOver={setDragOver}
            onDrop={handleDrop}
            showScan={false}
            scanning={false}
            onScan={() => {}}
            onStart={onStartBatch}
            busy={busy}
            onBrowseSource={() => setPicker({ kind: "batch-source" })}
            onBrowseOutput={() => setPicker({ kind: "batch-output" })}
          />
        </TabsContent>

        <TabsContent value="ppt-to-pdf">
          <BatchForm
            op="ppt-to-pdf"
            scope={scope}
            onScopeChange={setScope}
            source={source}
            onSourceChange={setSource}
            output={output}
            onOutputChange={setOutput}
            recursive={recursive}
            onRecursiveChange={setRecursive}
            dryRun={dryRun}
            onDryRunChange={setDryRun}
            mergeImages={mergeImages}
            onMergeImagesChange={setMergeImages}
            dragOver={dragOver}
            onDragOver={setDragOver}
            onDrop={handleDrop}
            showScan={false}
            scanning={false}
            onScan={() => {}}
            onStart={onStartBatch}
            busy={busy}
            onBrowseSource={() => setPicker({ kind: "batch-source" })}
            onBrowseOutput={() => setPicker({ kind: "batch-output" })}
          />
        </TabsContent>

        <TabsContent value="image-to-pdf">
          <BatchForm
            op="image-to-pdf"
            scope={scope}
            onScopeChange={setScope}
            source={source}
            onSourceChange={setSource}
            output={output}
            onOutputChange={setOutput}
            recursive={recursive}
            onRecursiveChange={setRecursive}
            dryRun={dryRun}
            onDryRunChange={setDryRun}
            mergeImages={mergeImages}
            onMergeImagesChange={setMergeImages}
            dragOver={dragOver}
            onDragOver={setDragOver}
            onDrop={handleDrop}
            showScan={false}
            scanning={false}
            onScan={() => {}}
            onStart={onStartBatch}
            busy={busy}
            onBrowseSource={() => setPicker({ kind: "batch-source" })}
            onBrowseOutput={() => setPicker({ kind: "batch-output" })}
          />
        </TabsContent>

        <TabsContent value="merge-pdf">
          <Card>
            <CardContent className="space-y-4 pt-6">
              <Field label="源文件（.pdf，可多选）">
                <div className="flex gap-2">
                  <Input
                    value={
                      mergeSources.length > 0 ? `已选 ${mergeSources.length} 个 PDF` : ""
                    }
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
              <Field
                label={
                  <span>
                    输出目录{" "}
                    <span className="font-normal text-muted-foreground">
                      （合并结果保存到该目录）
                    </span>
                  </span>
                }
              >
                <div className="flex gap-2">
                  <Input
                    value={mergeOutDir}
                    onChange={(e) => setMergeOutDir(e.target.value)}
                    placeholder="输出目录"
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
        </TabsContent>

        <TabsContent value="split-pdf">
          <Card>
            <CardContent className="space-y-4 pt-6">
              <Field label="源文件（.pdf）">
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
                    placeholder="拆分成品输出目录"
                  />
                  <Button variant="outline" onClick={() => setPicker({ kind: "split-output" })}>
                    浏览…
                  </Button>
                </div>
              </Field>
              <div className="space-y-2">
                <CheckOption checked={splitCustom} onCheckedChange={setSplitCustom}>
                  自定义页码范围（不勾选则每页一个文件）
                </CheckOption>
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
        </TabsContent>
      </Tabs>

      {/* ===== 扫描结果（仅去页眉·目录模式） ===== */}
      {operation === "remove-headers" && phase === "scanning" && (
        <Card>
          <CardContent className="space-y-3 pt-6">
            <Skeleton className="h-4 w-40" />
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </CardContent>
        </Card>
      )}

      {operation === "remove-headers" &&
        scope === "dir" &&
        phase !== "scanning" &&
        files.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                待处理 {files.length} 个文件 · 共 {formatSize(totalSize)}
                {recursive && <Badge variant="secondary">含子目录</Badge>}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[280px] rounded-md border">
                <ul className="divide-y">
                  {files.map((f) => (
                    <li
                      key={f.name}
                      className="flex items-center justify-between gap-3 px-3 py-2"
                    >
                      <span className="flex min-w-0 items-center gap-2 font-mono text-xs">
                        <FileText className="size-4 shrink-0 text-muted-foreground" />
                        <span className="truncate">{f.name}</span>
                      </span>
                      <span className="tabular shrink-0 text-xs text-muted-foreground">
                        {formatSize(f.size)}
                      </span>
                    </li>
                  ))}
                </ul>
              </ScrollArea>
            </CardContent>
          </Card>
        )}

      {operation === "remove-headers" &&
        scope === "dir" &&
        phase === "idle" &&
        files.length === 0 && (
          <p className="py-6 text-center text-sm text-muted-foreground">
            选择源目录后点击「扫描」查看待处理文件。
          </p>
        )}

      {error && (
        <div className="mt-4 flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <XCircle className="mt-0.5 size-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ===== 运行进度 ===== */}
      {phase === "running" && job && (
        <Card>
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
        <Card>
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
        <Card className="border-destructive/50">
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

      <footer className="pt-6 text-center text-xs text-muted-foreground">
        处理在本地完成，文件不会上传。
      </footer>

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
