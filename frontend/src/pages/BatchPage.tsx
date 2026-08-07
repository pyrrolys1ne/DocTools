import { useEffect, useState } from "react";

import BatchForm from "@/components/BatchForm";
import { ErrorBanner, Segmented } from "@/components/form";
import {
  BATCH_EXTS,
  REMOVE_TARGETS,
  TARGET_LABEL,
  type BatchOp,
  type RemoveTarget,
  type Scope,
} from "@/config/operations";
import { usePicker } from "@/hooks/usePicker";
import { useRecents } from "@/hooks/useRecents";
import type { UiVariant } from "@/config/ui";
import { cn } from "@/lib/utils";

import type { CreateJobParams } from "../types";

interface Props {
  /** 当前批量操作；op 为 remove-headers 时显示去页眉/去页脚目标切换。 */
  op: BatchOp;
  busy: boolean;
  onStart: (params: CreateJobParams) => void;
  variant: UiVariant;
}

/** 批量处理页：去页眉/去页脚、各转 PDF、图片转 PDF、图片压缩共用。 */
export default function BatchPage({ op, busy, onStart, variant }: Props) {
  const { recents, remember } = useRecents();
  const picker = usePicker();
  const isRemove = op === "remove-headers";
  const [target, setTarget] = useState<RemoveTarget>("remove-headers");
  const [scope, setScope] = useState<Scope>("dir");
  const [source, setSource] = useState("");
  const [output, setOutput] = useState("");
  const [recursive, setRecursive] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [quality, setQuality] = useState(80);
  const [error, setError] = useState<string | null>(null);

  // 实际执行的操作：去页眉版块由 target 决定
  const effectiveOp: BatchOp = isRemove ? target : op;

  // 挂载 / 切换去页眉去页脚目标时回填该操作上次使用的路径
  useEffect(() => {
    setSource(recents.source?.[effectiveOp] ?? "");
    setOutput(recents.output?.[effectiveOp] ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effectiveOp]);

  // 单文件拖拽：Firefox 通过 text/plain 提供完整路径；Chrome 出于隐私
  // 不暴露绝对路径，给出友好提示引导使用「浏览」。
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
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
  };

  const submit = () => {
    setError(null);
    if (!source.trim()) {
      setError("请选择源目录或文件");
      return;
    }
    remember("source", effectiveOp, source);
    remember("output", effectiveOp, output);
    onStart({
      operation: effectiveOp,
      source_path: source,
      output_path: output,
      recursive,
      output_is_dir: scope === "file",
      ...(effectiveOp === "compress-images" ? { quality } : {}),
    });
  };

  const openSourcePicker = () => {
    picker.open({
      initial: source,
      title: scope === "file" ? "选择源文件" : "选择源目录",
      exts: BATCH_EXTS[effectiveOp],
      onSelect:
        scope === "dir"
          ? (dir) => {
              setSource(dir);
              remember("source", effectiveOp, dir);
            }
          : undefined,
      onSelectFile:
        scope === "file"
          ? (path) => {
              setSource(path);
              remember("source", effectiveOp, path);
            }
          : undefined,
    });
  };

  const openOutputPicker = () => {
    picker.open({
      initial: output,
      title: "选择输出目录",
      onSelect: (dir) => {
        setOutput(dir);
        remember("output", effectiveOp, dir);
      },
    });
  };

  return (
    <div className={cn("operation-page mt-4 space-y-4", `operation-page-${variant}`)}>
      {isRemove && (
        <Segmented
          options={REMOVE_TARGETS.map((t) => ({ value: t, label: TARGET_LABEL[t] }))}
          value={target}
          onChange={setTarget}
        />
      )}
      <BatchForm
        op={effectiveOp}
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
        quality={quality}
        onQualityChange={setQuality}
        onStart={submit}
        busy={busy}
        onBrowseSource={openSourcePicker}
        onBrowseOutput={openOutputPicker}
        variant={variant}
      />
      {error && <ErrorBanner message={error} />}
      {picker.element}
    </div>
  );
}
