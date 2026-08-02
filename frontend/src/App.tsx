import { useCallback, useState } from "react";
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

export default function App() {
  const [mode, setMode] = useState<Mode>("dir");
  // 目录模式
  const [sourceDir, setSourceDir] = useState("");
  const [outputDir, setOutputDir] = useState("");
  const [recursive, setRecursive] = useState(false);
  // 单文件模式
  const [sourceFile, setSourceFile] = useState("");
  const [outputFile, setOutputFile] = useState("");
  const [dryRun, setDryRun] = useState(false);
  const [files, setFiles] = useState<ScanFile[]>([]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [job, setJob] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pickerFor, setPickerFor] = useState<"source" | "output" | null>(null);

  const totalSize = files.reduce((sum, f) => sum + f.size, 0);
  const progress = job && job.total > 0 ? (job.done / job.total) * 100 : 0;
  const busy = phase === "running" || phase === "scanning";

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

  return (
    <main className="app">
      <header className="app-header">
        <div className="logo" aria-hidden="true">
          <span className="logo-mark">D</span>
        </div>
        <div>
          <h1>
            DocTools <span className="ver">v0.1</span>
          </h1>
          <p className="subtitle">批量去除 Word 页眉（含横线）</p>
        </div>
      </header>

      <div className="mode-toggle">
        <button
          className={mode === "dir" ? "active" : ""}
          onClick={() => setMode("dir")}
        >
          目录批量
        </button>
        <button
          className={mode === "file" ? "active" : ""}
          onClick={() => setMode("file")}
        >
          单个文件
        </button>
      </div>

      {mode === "dir" ? (
        <section className="card">
          <div className="field">
            <label className="field-label">源目录</label>
            <div className="input-row">
              <input
                value={sourceDir}
                onChange={(e) => setSourceDir(e.target.value)}
                placeholder="例如 D:/Projects/DocTools/docs"
              />
              <button type="button" onClick={() => setPickerFor("source")}>
                浏览…
              </button>
            </div>
          </div>
          <div className="field">
            <label className="field-label">
              输出目录（留空自动生成 <code>*_cleaned</code>）
            </label>
            <div className="input-row">
              <input
                value={outputDir}
                onChange={(e) => setOutputDir(e.target.value)}
                placeholder="留空则使用默认"
              />
              <button type="button" onClick={() => setPickerFor("output")}>
                浏览…
              </button>
            </div>
          </div>
          <div className="row">
            <label className="check">
              <input
                type="checkbox"
                checked={recursive}
                onChange={(e) => setRecursive(e.target.checked)}
              />
              递归子目录
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={dryRun}
                onChange={(e) => setDryRun(e.target.checked)}
              />
              仅预览（dry-run）
            </label>
          </div>
          <div className="row">
            <button onClick={onScan} disabled={busy}>
              {phase === "scanning" ? "扫描中…" : "扫描"}
            </button>
            <button onClick={onStartDir} disabled={busy} className="primary">
              开始处理
            </button>
          </div>
        </section>
      ) : (
        <section className="card">
          <div className="field">
            <label className="field-label">源文件（.docx）</label>
            <div className="input-row">
              <input
                value={sourceFile}
                onChange={(e) => setSourceFile(e.target.value)}
                placeholder="选择或输入单个 .docx 文件路径"
              />
              <button type="button" onClick={() => setPickerFor("source")}>
                浏览…
              </button>
            </div>
          </div>
          <div className="field">
            <label className="field-label">
              输出目录（留空时在源文件旁生成 <code>文件名_cleaned.docx</code>）
            </label>
            <div className="input-row">
              <input
                value={outputFile}
                onChange={(e) => setOutputFile(e.target.value)}
                placeholder="留空则使用默认"
              />
              <button type="button" onClick={() => setPickerFor("output")}>
                浏览…
              </button>
            </div>
          </div>
          <div className="row">
            <label className="check">
              <input
                type="checkbox"
                checked={dryRun}
                onChange={(e) => setDryRun(e.target.checked)}
              />
              仅预览（dry-run）
            </label>
          </div>
          <div className="row">
            <button onClick={onStartFile} disabled={busy || !sourceFile} className="primary">
              开始处理
            </button>
          </div>
        </section>
      )}

      {error && <p className="error">⚠ {error}</p>}

      {mode === "dir" && files.length > 0 && (
        <section className="card">
          <h2>
            待处理 {files.length} 个文件 · 共 {formatSize(totalSize)}
            {recursive ? "（含子目录）" : ""}
          </h2>
          <ul className="file-list">
            {files.map((f) => (
              <li key={f.name}>
                <span className="name">📄 {f.name}</span>
                <span className="size">{formatSize(f.size)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {job && phase === "running" && (
        <section className="card">
          <h2>处理中… {job.done}/{job.total}</h2>
          <div className="bar">
            <div className="bar-fill" style={{ width: `${progress}%` }} />
          </div>
          {job.current && <p className="current">当前：{job.current}</p>}
        </section>
      )}

      {phase === "done" && job && (
        <section className="card">
          <h2>完成 ✅ {job.done}/{job.total}</h2>
          <ResultList results={job.results} />
        </section>
      )}

      {phase === "failed" && job && (
        <section className="card error-card">
          <h2>处理失败 ❌ {job.error ?? "未知错误"}</h2>
          <ResultList results={job.results} />
        </section>
      )}

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
    <ul className="result-list">
      {results.map((r) => (
        <li key={r.src}>
          <span className="name">📄 {r.src}</span>
          {r.ok ? (
            <span className="badge ok-badge">✓ OK</span>
          ) : (
            <span className="badge bad-badge">✕ {r.error ?? "FAIL"}</span>
          )}
        </li>
      ))}
    </ul>
  );
}
