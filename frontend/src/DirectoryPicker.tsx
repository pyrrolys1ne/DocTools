import { useCallback, useEffect, useState, type ReactNode } from "react";
import {
  Download,
  FileText,
  Folder,
  FolderUp,
  HardDrive,
  Home,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { drives, explore } from "./api";
import type { ExploreResult, SpecialFolder } from "./types";

/** 「位置」区可点击快捷入口的统一样式。 */
const CHIP_CLASS =
  "inline-flex items-center gap-1 rounded-md border bg-background px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground";

const SPECIAL_ICONS: Record<string, ReactNode> = {
  桌面: <Home className="size-3.5" />,
  文档: <FileText className="size-3.5" />,
  下载: <Download className="size-3.5" />,
};

interface Props {
  initial: string;
  title: string;
  onSelect: (dir: string) => void;
  onClose: () => void;
  /** 提供时 .docx 文件可点击选中（选择单个文件模式）。 */
  onSelectFile?: (path: string) => void;
}

/** 文件系统浏览弹窗：通过后端 /api/explore 浏览本机目录或选择单个 .docx。 */
export default function DirectoryPicker({
  initial,
  title,
  onSelect,
  onClose,
  onSelectFile,
}: Props) {
  const [current, setCurrent] = useState<ExploreResult | null>(null);
  const [drivesList, setDrivesList] = useState<string[]>([]);
  const [special, setSpecial] = useState<SpecialFolder[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (dir: string) => {
    setLoading(true);
    setError(null);
    try {
      setCurrent(await explore(dir));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  // 加载可用盘符与常见用户目录（桌面/文档…）
  useEffect(() => {
    drives()
      .then((r) => {
        setDrivesList(r.drives);
        setSpecial(r.special);
      })
      .catch(() => {});
  }, []);

  // 打开时定位到当前值；为空则从 C:/ 根开始
  useEffect(() => {
    load(initial || "C:/");
  }, [load, initial]);

  const enter = (name: string) => {
    if (current) load(`${current.dir}/${name}`);
  };

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent className="sm:max-w-2xl">
        <DialogTitle>{title}</DialogTitle>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => current?.parent && load(current.parent)}
            disabled={!current?.parent}
            title="返回上级"
          >
            <FolderUp className="size-4" /> 上级
          </Button>
          <span
            className="min-w-0 flex-1 truncate rounded-md border bg-muted/40 px-3 py-1.5 font-mono text-xs text-muted-foreground"
            title={current?.dir}
          >
            {current?.dir ?? "…"}
          </span>
        </div>

        {/* 位置：特殊文件夹（桌面/文档…）与盘符，作为可点击的快捷入口 */}
        {(special.length > 0 || drivesList.length > 0) && (
          <div className="space-y-1.5">
            <p className="text-[11px] font-bold tracking-wider text-muted-foreground uppercase">
              位置
            </p>
            <div className="flex flex-wrap gap-1.5">
              {drivesList.map((d) => (
                <button
                  key={d}
                  type="button"
                  className={CHIP_CLASS}
                  onClick={() => load(`${d}/`)}
                  title={`${d}\\`}
                >
                  <HardDrive className="size-3.5" /> {d}
                </button>
              ))}
              {special.map((s) => (
                <button
                  key={s.path}
                  type="button"
                  className={CHIP_CLASS}
                  onClick={() => load(s.path)}
                  title={s.path}
                >
                  {SPECIAL_ICONS[s.name] ?? <Folder className="size-3.5" />}
                  {s.name}
                </button>
              ))}
            </div>
          </div>
        )}

        {error && <p className="text-sm text-destructive">⚠ {error}</p>}
        {current?.error && <p className="text-sm text-destructive">⚠ {current.error}</p>}

        <ScrollArea className="h-[340px] rounded-md border">
          {loading ? (
            <div className="grid grid-cols-2 divide-x p-3">
              <div className="space-y-2 pr-3">
                {[0, 1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-7 w-full" />
                ))}
              </div>
              <div className="space-y-2 pl-3">
                {[0, 1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-7 w-full" />
                ))}
              </div>
            </div>
          ) : current ? (
            <div className="grid grid-cols-2 divide-x">
              <div className="p-2">
                <p className="px-2 pb-1 text-[11px] font-bold tracking-wider text-muted-foreground uppercase">
                  文件夹
                </p>
                {current.dirs.length === 0 ? (
                  <p className="px-2 py-1.5 text-xs text-muted-foreground">（无子文件夹）</p>
                ) : (
                  <ul>
                    {current.dirs.map((d) => (
                      <li key={d}>
                        <button
                          type="button"
                          onClick={() => enter(d)}
                          className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent hover:text-accent-foreground"
                        >
                          <Folder className="size-4 shrink-0 text-muted-foreground" />
                          <span className="truncate">{d}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="p-2">
                <p className="px-2 pb-1 text-[11px] font-bold tracking-wider text-muted-foreground uppercase">
                  本目录 .docx {onSelectFile ? "（点击选择）" : "（预览）"}
                </p>
                {current.files.length === 0 ? (
                  <p className="px-2 py-1.5 text-xs text-muted-foreground">（无 .docx）</p>
                ) : (
                  <ul>
                    {current.files.map((f) =>
                      onSelectFile ? (
                        <li key={f}>
                          <button
                            type="button"
                            onClick={() => onSelectFile(`${current.dir}/${f}`)}
                            className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent hover:text-accent-foreground"
                          >
                            <FileText className="size-4 shrink-0 text-muted-foreground" />
                            <span className="truncate">{f}</span>
                          </button>
                        </li>
                      ) : (
                        <li
                          key={f}
                          className="flex items-center gap-2 px-2 py-1.5 text-sm text-muted-foreground"
                        >
                          <FileText className="size-4 shrink-0" />
                          <span className="truncate">{f}</span>
                        </li>
                      ),
                    )}
                  </ul>
                )}
              </div>
            </div>
          ) : (
            <div className="p-4 text-sm text-muted-foreground">加载中…</div>
          )}
        </ScrollArea>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          {!onSelectFile && (
            <Button disabled={!current} onClick={() => current && onSelect(current.dir)}>
              选择此目录
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
