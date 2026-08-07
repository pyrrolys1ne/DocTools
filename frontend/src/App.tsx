import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { ErrorBanner } from "@/components/form";
import { DoneCard, FailedCard, ProgressCard } from "@/components/JobStatus";
import { OperationHeader } from "@/components/OperationHeader";
import { PrototypeSwitcher } from "@/components/PrototypeSwitcher";
import { isUiVariant, type UiVariant } from "@/config/ui";
import type { View } from "@/config/operations";
import { useJob } from "@/hooks/useJob";
import BatchPage from "@/pages/BatchPage";
import HomePage from "@/pages/HomePage";
import MergePdfPage from "@/pages/MergePdfPage";
import PdfToImagesPage from "@/pages/PdfToImagesPage";
import SplitPdfPage from "@/pages/SplitPdfPage";

/**
 * 顶层壳：品牌头部 + 页面路由（首页宫格 / 各功能页）+ 统一的任务状态展示。
 * 各功能页只负责自己的表单与路径选择，任务运行逻辑在 useJob 里。
 */
export default function App() {
  const [view, setView] = useState<View>("home");
  const [variant, setVariant] = useState<UiVariant>(() => {
    const value = new URLSearchParams(window.location.search).get("variant");
    return isUiVariant(value) ? value : "workspace";
  });
  const { phase, job, error, startJob, progress, busy, okCount, failCount } = useJob();

  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set("variant", variant);
    window.history.replaceState(null, "", url);
  }, [variant]);

  return (
    <main className={`ui-shell ui-variant-${variant}`}>
      <header className="ui-app-header flex items-center gap-3.5">
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
        <HomePage onOpen={setView} variant={variant} />
      ) : (
        <>
          <OperationHeader view={view} onBack={() => setView("home")} variant={variant} />

          {view === "merge-pdf" ? (
            <MergePdfPage onStart={startJob} busy={busy} variant={variant} />
          ) : view === "split-pdf" ? (
            <SplitPdfPage onStart={startJob} busy={busy} variant={variant} />
          ) : view === "pdf-to-images" ? (
            <PdfToImagesPage onStart={startJob} busy={busy} variant={variant} />
          ) : (
            <BatchPage op={view} onStart={startJob} busy={busy} variant={variant} />
          )}

          {/* 任务层错误（创建失败等） */}
          {error && <ErrorBanner message={error} />}

          {/* 运行进度 / 完成 / 失败 */}
          {phase === "running" && job && <ProgressCard job={job} progress={progress} />}
          {phase === "done" && job && (
            <DoneCard job={job} okCount={okCount} failCount={failCount} />
          )}
          {phase === "failed" && job && <FailedCard job={job} />}
        </>
      )}
      <PrototypeSwitcher value={variant} onChange={setVariant} />
    </main>
   );
}
