import { useCallback, useState } from "react";

import { createJob, getJob, jobWsUrl } from "../api";
import type { CreateJobParams, JobStatus } from "../types";

type Phase = "idle" | "running" | "done" | "failed";

/**
 * 运行任务：创建任务并订阅 WebSocket 实时进度；连接失败时回退轮询。
 * 返回的 phase / job / error 由 App 统一渲染进度与结果卡片。
 */
export function useJob() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [job, setJob] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  const progress = job && job.total > 0 ? (job.done / job.total) * 100 : 0;
  const busy = phase === "running";
  const okCount = job ? job.results.filter((r) => r.ok).length : 0;
  const failCount = job ? job.results.length - okCount : 0;

  return { phase, job, error, startJob, progress, busy, okCount, failCount };
}
