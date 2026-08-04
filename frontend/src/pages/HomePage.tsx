import { ChevronRight } from "lucide-react";

import { OPERATIONS_META, type Operation } from "@/config/operations";
import { cn } from "@/lib/utils";

/** 首页：功能宫格，每个功能一个小方块，点开进入对应页面。 */
export default function HomePage({ onOpen }: { onOpen: (op: Operation) => void }) {
  return (
    <section className="mt-6">
      <p className="mb-3 text-sm text-muted-foreground">选择一个功能开始：</p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {OPERATIONS_META.map((m) => (
          <button
            key={m.op}
            type="button"
            onClick={() => onOpen(m.op)}
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
  );
}
