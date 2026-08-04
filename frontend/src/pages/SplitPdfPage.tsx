import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { CheckOption, ErrorBanner, Field } from "@/components/form";
import { usePicker } from "@/hooks/usePicker";
import { useRecents } from "@/hooks/useRecents";

import type { CreateJobParams } from "../types";

interface Props {
  busy: boolean;
  onStart: (params: CreateJobParams) => void;
}

/** 拆分 PDF：每页一个，或按自定义页码范围。 */
export default function SplitPdfPage({ busy, onStart }: Props) {
  const { recents, remember } = useRecents();
  const picker = usePicker();
  const [source, setSource] = useState("");
  const [outDir, setOutDir] = useState("");
  const [custom, setCustom] = useState(false);
  const [ranges, setRanges] = useState("");
  const [error, setError] = useState<string | null>(null);

  // 挂载时回填上次使用的输出目录
  useEffect(() => {
    setOutDir(recents.output?.["split-pdf"] ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submit = () => {
    setError(null);
    if (!source.trim()) {
      setError("请选择要拆分的 PDF 文件");
      return;
    }
    if (!outDir.trim()) {
      setError("请选择输出目录");
      return;
    }
    remember("output", "split-pdf", outDir);
    onStart({
      operation: "split-pdf",
      source_path: source,
      output_path: outDir,
      recursive: false,
      output_is_dir: false,
      page_ranges: custom ? ranges : "",
    });
  };

  return (
    <Card className="mt-4">
      <CardContent className="space-y-4 pt-6">
        <Field label="源文件">
          <div className="flex gap-2">
            <Input
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="选择要拆分的 .pdf 文件"
            />
            <Button
              variant="outline"
              onClick={() =>
                picker.open({
                  initial: source,
                  title: "选择要拆分的 PDF 文件",
                  exts: ".pdf",
                  onSelectFile: (path) => {
                    setSource(path);
                    remember("source", "split-pdf", path);
                  },
                })
              }
            >
              浏览…
            </Button>
          </div>
        </Field>
        <Field label="输出目录">
          <div className="flex gap-2">
            <Input
              value={outDir}
              onChange={(e) => setOutDir(e.target.value)}
              placeholder="默认生成到源文件旁的 *_split 文件夹"
            />
            <Button
              variant="outline"
              onClick={() =>
                picker.open({
                  initial: outDir,
                  title: "选择输出目录",
                  onSelect: (dir) => {
                    setOutDir(dir);
                    remember("output", "split-pdf", dir);
                  },
                })
              }
            >
              浏览…
            </Button>
          </div>
        </Field>
        <div className="space-y-2">
          <CheckOption checked={custom} onCheckedChange={setCustom}>
            自定义页码范围
          </CheckOption>
          <p className="text-xs text-muted-foreground">不勾选时每页拆成一个文件</p>
          {custom && (
            <Input
              value={ranges}
              onChange={(e) => setRanges(e.target.value)}
              placeholder="如 1-3,5,8-12"
            />
          )}
        </div>
        <div className="pt-1">
          <Button onClick={submit} disabled={busy}>
            开始拆分
          </Button>
        </div>
        {error && <ErrorBanner message={error} />}
      </CardContent>
      {picker.element}
    </Card>
  );
}
