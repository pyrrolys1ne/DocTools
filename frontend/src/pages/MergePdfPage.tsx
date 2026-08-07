import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ErrorBanner, Field } from "@/components/form";
import { usePicker } from "@/hooks/usePicker";
import { useRecents } from "@/hooks/useRecents";
import type { UiVariant } from "@/config/ui";
import { cn } from "@/lib/utils";

import type { CreateJobParams } from "../types";

interface Props {
  busy: boolean;
  onStart: (params: CreateJobParams) => void;
  variant: UiVariant;
}

/** 合并 PDF：多选源文件，输出到指定目录下的一个 PDF。 */
export default function MergePdfPage({ busy, onStart, variant }: Props) {
  const { recents, remember, updateRecents } = useRecents();
  const picker = usePicker();
  const [sources, setSources] = useState<string[]>([]);
  const [outDir, setOutDir] = useState("");
  const [fileName, setFileName] = useState("merged.pdf");
  const [error, setError] = useState<string | null>(null);

  // 挂载时回填上次使用的输出目录与文件名
  useEffect(() => {
    setOutDir(recents.output?.["merge-pdf"] ?? "");
    setFileName(recents.mergeFileName ?? "merged.pdf");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openSourcePicker = () =>
    picker.open({
      title: "选择要合并的 PDF 文件",
      exts: ".pdf",
      multi: true,
      onSelectFiles: setSources,
    });

  const openOutputPicker = () =>
    picker.open({
      initial: outDir,
      title: "选择输出目录",
      onSelect: (dir) => {
        setOutDir(dir);
        remember("output", "merge-pdf", dir);
      },
    });

  const submit = () => {
    setError(null);
    if (sources.length === 0) {
      setError("请选择要合并的 PDF 文件");
      return;
    }
    if (!outDir.trim()) {
      setError("请选择输出目录");
      return;
    }
    remember("output", "merge-pdf", outDir);
    updateRecents((r) => ({ ...r, mergeFileName: fileName.trim() || "merged.pdf" }));
    onStart({
      operation: "merge-pdf",
      source_path: "",
      output_path: `${outDir.replace(/[\\/]+$/, "")}/${fileName.trim() || "merged.pdf"}`,
      recursive: false,
      output_is_dir: false,
      sources,
    });
  };

  return (
    <Card className={cn("operation-form-card operation-form-special mt-4", `operation-form-${variant}`)}>
      <CardContent
        className={cn(
          "operation-form-content space-y-5 pt-6",
          variant === "workspace" &&
            "lg:grid lg:grid-cols-[minmax(0,1.5fr)_minmax(280px,0.8fr)] lg:gap-x-8 lg:gap-y-5 lg:space-y-0",
          variant === "rail" &&
            "lg:grid lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)_190px] lg:items-end lg:gap-x-5 lg:gap-y-5 lg:space-y-0",
        )}
      >
        <Field label="源文件">
          <div className="file-picker-row flex gap-2 rounded-[12px]">
            <Input
              value={sources.length > 0 ? `已选 ${sources.length} 个 PDF` : ""}
              readOnly
              placeholder="点击浏览，多选要合并的 PDF"
              className="cursor-pointer"
              onClick={openSourcePicker}
            />
            <Button variant="outline" onClick={openSourcePicker}>
              浏览…
            </Button>
          </div>
        </Field>
        {sources.length > 0 && (
          <p className="break-all text-xs text-muted-foreground">
            已选：{sources.map((p) => p.split(/[\\/]/).pop()).join("、")}
          </p>
        )}
        <Field label="输出目录（必选）">
          <div className="file-picker-row flex gap-2 rounded-[12px]">
            <Input
              value={outDir}
              onChange={(e) => setOutDir(e.target.value)}
              placeholder="合并结果保存到该目录"
            />
            <Button variant="outline" onClick={openOutputPicker}>
              浏览…
            </Button>
          </div>
        </Field>
        <Field label="合并后文件名">
          <Input
            value={fileName}
            onChange={(e) => setFileName(e.target.value)}
            placeholder="默认 merged.pdf"
          />
        </Field>
        <div className="pt-1">
          <Button onClick={submit} disabled={busy}>
            开始合并
          </Button>
        </div>
        {error && <ErrorBanner message={error} />}
      </CardContent>
      {picker.element}
    </Card>
  );
}
