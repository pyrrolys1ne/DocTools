import { useState, type ReactNode } from "react";

import DirectoryPicker from "../DirectoryPicker";

export interface PickerOptions {
  initial?: string;
  title: string;
  exts?: string;
  multi?: boolean;
  /** 选择目录（或点击「选择此目录」按钮）。 */
  onSelect?: (dir: string) => void;
  /** 提供时文件可点击选中（选择单个文件模式）。 */
  onSelectFile?: (path: string) => void;
  /** multi 模式确认选择时回调（绝对路径数组）。 */
  onSelectFiles?: (paths: string[]) => void;
}

/** 目录/文件浏览弹窗：各页面只负责传入选项与回调，弹窗渲染统一在这里。 */
export function usePicker() {
  const [opts, setOpts] = useState<PickerOptions | null>(null);

  const open = (o: PickerOptions) => setOpts(o);
  const close = () => setOpts(null);

  const element: ReactNode = opts ? (
    <DirectoryPicker
      initial={opts.initial ?? ""}
      title={opts.title}
      exts={opts.exts}
      multi={opts.multi}
      onSelect={opts.onSelect ?? close}
      onSelectFile={opts.onSelectFile}
      onSelectFiles={opts.onSelectFiles}
      onClose={close}
    />
  ) : null;

  return { open, close, element };
}
