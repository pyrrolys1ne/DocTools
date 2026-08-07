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

/** PDF 转图片：单个 PDF，每页导出一张 PNG。 */
export default function PdfToImagesPage({ busy, onStart, variant }: Props) {
  const { recents, remember } = useRecents();
  const picker = usePicker();
  const [source, setSource] = useState("");
  const [outDir, setOutDir] = useState("");
  const [error, setError] = useState<string | null>(null);

  // 挂载时回填上次使用的源文件与输出目录
  useEffect(() => {
    setSource(recents.source?.["pdf-to-images"] ?? "");
    setOutDir(recents.output?.["pdf-to-images"] ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submit = () => {
    setError(null);
    if (!source.trim()) {
      setError("请选择要转图片的 .pdf 文件");
      return;
    }
    remember("source", "pdf-to-images", source);
    remember("output", "pdf-to-images", outDir);
    onStart({
      operation: "pdf-to-images",
      source_path: source,
      output_path: outDir,
      recursive: false,
      output_is_dir: false,
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
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="选择要转图片的 .pdf 文件"
            />
            <Button
              variant="outline"
              onClick={() =>
                picker.open({
                  initial: source,
                  title: "选择要转图片的 PDF 文件",
                  exts: ".pdf",
                  onSelectFile: (path) => {
                    setSource(path);
                    remember("source", "pdf-to-images", path);
                  },
                })
              }
            >
              浏览…
            </Button>
          </div>
        </Field>
        <Field label="输出目录（可选，默认生成在源路径旁）">
          <div className="file-picker-row flex gap-2 rounded-[12px]">
            <Input
              value={outDir}
              onChange={(e) => setOutDir(e.target.value)}
              placeholder="默认生成到源文件旁的 *_images 文件夹"
            />
            <Button
              variant="outline"
              onClick={() =>
                picker.open({
                  initial: outDir,
                  title: "选择输出目录",
                  onSelect: (dir) => {
                    setOutDir(dir);
                    remember("output", "pdf-to-images", dir);
                  },
                })
              }
            >
              浏览…
            </Button>
          </div>
        </Field>
        <div className="pt-1">
          <Button onClick={submit} disabled={busy}>
            开始转换
          </Button>
        </div>
        {error && <ErrorBanner message={error} />}
      </CardContent>
      {picker.element}
    </Card>
  );
}
