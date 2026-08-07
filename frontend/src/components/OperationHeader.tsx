import { ChevronLeft } from "lucide-react";

import { OPERATIONS_META, type Operation } from "@/config/operations";
import type { UiVariant } from "@/config/ui";
import { cn } from "@/lib/utils";

/** 功能页顶部：返回首页按钮 + 功能名与图标。 */
export function OperationHeader({
  view,
  onBack,
  variant,
}: {
  view: Operation;
  onBack: () => void;
  variant: UiVariant;
}) {
  const meta = OPERATIONS_META.find((m) => m.op === view);
  return (
    <div className={cn("operation-header", `operation-header-${variant}`)}>
      <button
        type="button"
        onClick={onBack}
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
  );
}
