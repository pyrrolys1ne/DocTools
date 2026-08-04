import { useCallback, useState } from "react";

import { loadRecents, saveRecents, type Recents } from "../recents";

/**
 * localStorage 记住的路径（按操作分组）。页面在挂载 / 切换去页眉去页脚
 * 目标时用它回填上次使用的源路径与输出目录。
 */
export function useRecents() {
  const [recents, setRecents] = useState<Recents>(loadRecents);

  const updateRecents = useCallback((fn: (r: Recents) => Recents) => {
    setRecents((prev) => {
      const next = fn(prev);
      saveRecents(next);
      return next;
    });
  }, []);

  const remember = useCallback(
    (kind: "source" | "output", op: string, value: string) => {
      if (!value) return;
      updateRecents((r) => ({ ...r, [kind]: { ...r[kind], [op]: value } }));
    },
    [updateRecents],
  );

  return { recents, updateRecents, remember };
}
