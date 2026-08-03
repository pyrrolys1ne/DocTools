import { useCallback, useState } from "react";
import { CheckCircle2, FileText, Loader2, XCircle } from "lucide-react";

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
import type { FileResult, JobStatus, ScanFile } from "./types";

type Mode = "dir" | "file";
type Phase = "idle" | "scanning" | "preview" | "running" | "done" | "failed";

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

export default function App() {
  const [mode, setMode] = useState<Mode>("dir");
  // 目录模式
  const [sourceDir, setSourceDir] = useState("");
  const [outputDir, setOutputDir] = useState("");
  const [recursive, setRecursive] = useState(false);
  // 单文件模式
  const [sourceFile, setSourceFile] = useState("");
  const [outputFile, setOutputFile] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [files, setFiles] = useState<ScanFile[]>([]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [job, setJob] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pickerFor, setPickerFor] = useState<"source" | "output" | null>(null);

  const totalSize = files.reduce((sum, f) => sum + f.size, 0);
  const progress = job && job.total > 0 ? (job.done / job.total) * 100 : 0;
  const busy = phase === "running" || phase === "scanning";
  const okCount = job ? job.results.filter((r) => r.ok).length : 0;
  const failCount = job ? job.results.length - okCount : 0;

  // 启动任务并订阅进度（WebSocket 实时；失败则回退轮询）
  const startJob = useCallback(
    async (
      source_path: string,
      output_path: string,
      recursive: boolean,
      output_is_dir: boolean,
    ) => {
      setError(null);
      setJob(null);
      setPhase("running");
      try {
        const { id } = await createJob({
          source_path,
          output_path,
          recursive,
          dry_run: dryRun,
          output_is_dir,
        });

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
        setPhase("preview");
      }
    },
    [dryRun],
  );

  const onScan = useCallback(async () => {
    setError(null);
    setPhase("scanning");
    try {
      const result = await scan(sourceDir, recursive);
      setFiles(result.files);
      setPhase("preview");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setPhase("idle");
    }
  }, [sourceDir, recursive]);

  const onStartDir = () => startJob(sourceDir, outputDir, recursive, false);
  const onStartFile = () => startJob(sourceFile, outputFile, false, true);

  // 单文件拖拽：Firefox 通过 text/plain 提供完整路径；Chrome 出于隐私
  // 不暴露绝对路径，给出友好提示引导使用「浏览」。
  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const text = e.dataTransfer.getData("text/plain").trim();
    if (/\.docx$/i.test(text)) {
      setSourceFile(text);
      return;
    }
    const name = e.dataTransfer.files?.[0]?.name ?? "";
    if (/\.docx$/i.test(name)) {
      setError(`已检测到「${name}」，但浏览器无法提供完整路径。请使用「浏览」选择该文件。`);
    } else {
      setError("请拖入 .docx 文件");
    }
  }, []);

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
              v0.2
            </Badge>
          </h1>
          <p className="text-sm text-muted-foreground">批量去除 Word 页眉（含横线）</p>
        </div>
      </header>

      <Tabs value={mode} onValueChange={(v) => setMode(v as Mode)} className="mt-4">
        <TabsList>
          <TabsTrigger value="dir">目录批量</TabsTrigger>
          <TabsTrigger value="file">单个文件</TabsTrigger>
        </TabsList>

        {/* ===== 目录批量模式 ===== */}
        <TabsContent value="dir">
          <Card>
            <CardContent className="space-y-4 pt-6">
              <Field label="源目录">
                <div className="flex gap-2">
                  <Input
                    value={sourceDir}
                    onChange={(e) => setSourceDir(e.target.value)}
                    placeholder="例如 D:/Projects/DocTools/docs"
                  />
                  <Button type="button" variant="outline" onClick={() => setPickerFor("source")}>
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
                    value={outputDir}
                    onChange={(e) => setOutputDir(e.target.value)}
                    placeholder="留空则使用默认"
                  />
                  <Button type="button" variant="outline" onClick={() => setPickerFor("output")}>
                    浏览…
                  </Button>
                </div>
              </Field>
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                <CheckOption checked={recursive} onCheckedChange={setRecursive}>
                  递归子目录
                </CheckOption>
                <CheckOption checked={dryRun} onCheckedChange={setDryRun}>
                  仅预览（dry-run）
                </CheckOption>
              </div>
              <div className="flex gap-2 pt-1">
                <Button variant="outline" onClick={onScan} disabled={busy}>
                  {phase === "scanning" ? (
                    <>
                      <Loader2 className="animate-spin" /> 扫描中…
                    </>
                  ) : (
                    "扫描"
                  )}
                </Button>
                <Button onClick={onStartDir} disabled={busy}>
                  开始处理
                </Button>
              </div>
            </CardContent>
          </Card>

          {phase === "scanning" && (
            <Card>
              <CardContent className="space-y-3 pt-6">
                <Skeleton className="h-4 w-40" />
                {[0, 1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </CardContent>
            </Card>
          )}

          {mode === "dir" && phase !== "scanning" && files.length > 0 && (
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

          {mode === "dir" && phase === "idle" && files.length === 0 && (
            <p className="py-6 text-center text-sm text-muted-foreground">
              选择源目录后点击「扫描」查看待处理文件。
            </p>
          )}
        </TabsContent>

        {/* ===== 单个文件模式 ===== */}
        <TabsContent value="file">
          <Card>
            <CardContent className="space-y-4 pt-6">
              <Field label="源文件（.docx，可直接拖入文件）">
                <div
                  className={cn(
                    "flex gap-2 rounded-md transition-shadow",
                    dragOver && "ring-2 ring-ring",
                  )}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragOver(true);
                  }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                >
                  <Input
                    value={sourceFile}
                    onChange={(e) => setSourceFile(e.target.value)}
                    placeholder="选择或输入单个 .docx 文件路径"
                  />
                  <Button type="button" variant="outline" onClick={() => setPickerFor("source")}>
                    浏览…
                  </Button>
                </div>
              </Field>
              <Field
                label={
                  <span>
                    输出目录{" "}
                    <span className="font-normal text-muted-foreground">
                      （留空在源文件旁生成 *_cleaned.docx）
                    </span>
                  </span>
                }
              >
                <div className="flex gap-2">
                  <Input
                    value={outputFile}
                    onChange={(e) => setOutputFile(e.target.value)}
                    placeholder="留空则使用默认"
                  />
                  <Button type="button" variant="outline" onClick={() => setPickerFor("output")}>
                    浏览…
                  </Button>
                </div>
              </Field>
              <div>
                <CheckOption checked={dryRun} onCheckedChange={setDryRun}>
                  仅预览（dry-run）
                </CheckOption>
              </div>
              <div className="pt-1">
                <Button onClick={onStartFile} disabled={busy || !sourceFile}>
                  开始处理
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

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

      {/* ===== 目录/文件选择弹窗 ===== */}
      {pickerFor === "source" && (
        <DirectoryPicker
          initial={mode === "dir" ? sourceDir : sourceFile}
          title={mode === "dir" ? "选择源目录" : "选择源文件"}
          onSelect={(dir) => {
            if (mode === "dir") setSourceDir(dir);
            setPickerFor(null);
          }}
          onSelectFile={
            mode === "file"
              ? (path) => {
                  setSourceFile(path);
                  setPickerFor(null);
                }
              : undefined
          }
          onClose={() => setPickerFor(null)}
        />
      )}

      {pickerFor === "output" && (
        <DirectoryPicker
          initial={mode === "dir" ? outputDir : outputFile}
          title="选择输出目录"
          onSelect={(dir) => {
            if (mode === "dir") setOutputDir(dir);
            else setOutputFile(dir);
            setPickerFor(null);
          }}
          onClose={() => setPickerFor(null)}
        />
      )}
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
