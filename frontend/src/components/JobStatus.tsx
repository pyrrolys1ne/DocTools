import { CheckCircle2, FileText, Loader2, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";

import type { FileResult, JobStatus as JobStatusType } from "../types";

/** 处理中：进度条 + 当前文件。 */
export function ProgressCard({ job, progress }: { job: JobStatusType; progress: number }) {
  return (
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
  );
}

/** 完成：统计徽标 + 逐文件结果。 */
export function DoneCard({
  job,
  okCount,
  failCount,
}: {
  job: JobStatusType;
  okCount: number;
  failCount: number;
}) {
  return (
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
  );
}

/** 失败：错误原因 + 部分成功的结果列表。 */
export function FailedCard({ job }: { job: JobStatusType }) {
  return (
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
  );
}

export function ResultList({ results }: { results: FileResult[] }) {
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
