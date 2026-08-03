/** 记住上次使用的源路径 / 输出目录（按操作分组），存在浏览器 localStorage。 */

const KEY = "doctools.recents.v1";

export interface Recents {
  /** 每个操作上次使用的源路径。 */
  source: Record<string, string>;
  /** 每个操作上次使用的输出目录。 */
  output: Record<string, string>;
  /** 合并 PDF 上次使用的输出文件名。 */
  mergeFileName?: string;
}

const EMPTY: Recents = { source: {}, output: {} };

export function loadRecents(): Recents {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return EMPTY;
    const parsed = JSON.parse(raw) as Partial<Recents>;
    return {
      source: parsed.source ?? {},
      output: parsed.output ?? {},
      mergeFileName: parsed.mergeFileName ?? "merged.pdf",
    };
  } catch {
    return EMPTY;
  }
}

export function saveRecents(r: Recents): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(r));
  } catch {
    // localStorage 不可用（隐私模式等）时静默忽略，不影响使用
  }
}
