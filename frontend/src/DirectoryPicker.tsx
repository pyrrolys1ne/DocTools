import { useCallback, useEffect, useState } from "react";
import { drives, explore } from "./api";
import type { ExploreResult } from "./types";

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

  // 加载可用盘符
  useEffect(() => {
    drives()
      .then(setDrivesList)
      .catch(() => {});
  }, []);

  // 打开时定位到当前值；为空则从 C:/ 根开始
  useEffect(() => {
    load(initial || "C:/");
  }, [load, initial]);

  // 当前路径所在的盘符（D:\... -> "D:"），用于盘符下拉框的高亮
  const currentDrive = current ? current.dir.split(/[/\\]/)[0] : "";

  const enter = (name: string) => {
    if (current) load(`${current.dir}/${name}`);
  };

  const up = () => {
    if (current?.parent) load(current.parent);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{title}</h3>
        <div className="picker-path">
          <button onClick={up} disabled={!current?.parent} title="返回上级">
            ⬆ 上级
          </button>
          {drivesList.length > 1 && (
            <select
              className="drive-select"
              value={currentDrive}
              onChange={(e) => load(`${e.target.value}/`)}
              title="切换磁盘"
            >
              {drivesList.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          )}
          <span className="path" title={current?.dir}>
            {current?.dir ?? "…"}
          </span>
        </div>

        {error && <p className="error">⚠ {error}</p>}
        {current?.error && <p className="error">⚠ {current.error}</p>}

        <div className="picker-body" key={current?.dir ?? "init"}>
          {current && (
            <div className="picker-cols">
              <div className="picker-col">
                <h4>文件夹</h4>
                <ul className="picker-list">
                  {current.dirs.map((d) => (
                    <li key={d}>
                      <button className="dir" onClick={() => enter(d)}>
                        <span className="dir-icon" aria-hidden="true">
                          📁
                        </span>
                        <span className="dir-name">{d}</span>
                      </button>
                    </li>
                  ))}
                  {current.dirs.length === 0 && <li className="dim">（无子文件夹）</li>}
                </ul>
              </div>
              <div className="picker-col">
                <h4>本目录 .docx {onSelectFile ? "（点击选择）" : "（预览）"}</h4>
                <ul className="picker-list">
                  {current.files.map((f) =>
                    onSelectFile ? (
                      <li key={f}>
                        <button className="dir" onClick={() => onSelectFile(`${current.dir}/${f}`)}>
                          <span className="dir-icon" aria-hidden="true">
                            📄
                          </span>
                          <span className="dir-name">{f}</span>
                        </button>
                      </li>
                    ) : (
                      <li key={f} className="dim">
                        📄 {f}
                      </li>
                    ),
                  )}
                  {current.files.length === 0 && <li className="dim">（无 .docx）</li>}
                </ul>
              </div>
            </div>
          )}
          {loading && <div className="picker-loading">加载中…</div>}
        </div>

        <div className="modal-actions">
          <button onClick={onClose}>取消</button>
          {!onSelectFile && (
            <button
              className="primary"
              disabled={!current}
              onClick={() => current && onSelect(current.dir)}
            >
              选择此目录
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
