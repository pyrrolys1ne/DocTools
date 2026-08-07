import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  OUTPUT_PLACEHOLDER,
  QUALITY_LEVELS,
  SOURCE_PLACEHOLDER,
  type BatchOp,
  type Scope,
} from "@/config/operations";
import type { UiVariant } from "@/config/ui";
import { cn } from "@/lib/utils";

import { CheckOption, Field, Segmented } from "./form";

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
  variant: UiVariant;
}

/** 批量处理表单：源路径（目录/单文件）+ 输出目录 + 递归 + 压缩质量。 */
export default function BatchForm(props: BatchFormProps) {
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
    variant,
  } = props;

  return (
    <Card className={cn("operation-form-card", `operation-form-${variant}`)}>
      <CardContent
        className={cn(
          "operation-form-content space-y-5 pt-6",
          variant === "workspace" &&
            "lg:grid lg:grid-cols-[minmax(0,1.5fr)_minmax(280px,0.8fr)] lg:gap-x-8 lg:gap-y-5 lg:space-y-0",
          variant === "rail" &&
            "lg:grid lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)_190px] lg:items-end lg:gap-x-5 lg:gap-y-5 lg:space-y-0",
        )}
      >
        {/* 目录批量 / 单个文件 */}
        <Segmented
          options={[
            { value: "dir", label: "目录批量" },
            { value: "file", label: "单个文件" },
          ]}
          value={scope}
          onChange={onScopeChange}
        />

        <Field label={scope === "dir" ? "源目录" : "源文件"}>
          <div
            className={cn(
              "file-picker-row flex gap-2 rounded-[12px] transition-shadow",
              variant === "workspace" && "lg:min-h-40 lg:flex-col lg:justify-end lg:p-4",
              variant === "rail" && "lg:flex-col",
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

        <Field label="输出目录（可选，默认生成在源路径旁）">
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
            <Segmented
              options={QUALITY_LEVELS.map((lv) => ({ value: String(lv.value), label: lv.label }))}
              value={String(quality)}
              onChange={(v) => onQualityChange(Number(v))}
            />
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
