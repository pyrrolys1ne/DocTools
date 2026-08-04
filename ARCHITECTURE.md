# DocTools 架构

> 定位：**本地优先的批量文档处理工具**。先做本地 Web UI，将来可演变成线上多用户服务（BS）。

## 0. 核心原则

`doctools` 永远是**纯库**，Web / CLI 只是它的壳。

- `src/doctools/` 下不依赖任何 Web 或 CLI 框架，保证可被任何消费方复用。
- CLI 与 Web 后端共享同一套批量编排层（`batch.py`），避免各实现一遍循环逻辑。
- 数据流是"本地磁盘 → 本地磁盘"：输入目录、输出目录都在用户机器上，文件不离开本机。

## 1. 仓库结构

```
DocTools/
├── src/doctools/            # 纯库
│   ├── __init__.py
│   ├── docx.py              # 文档处理原语：clear_headers / strip_headers
│   ├── batch.py             # 批量编排：discover / build_plan / process_batch
│   └── cli.py               # 瘦壳：只消费 batch.py，打印 [OK]/[FAIL]
├── web/                     # 本地 Web 后端（FastAPI）
│   ├── __init__.py
│   ├── app.py               # 路由：explore / scan / jobs / WS 进度流
│   ├── jobs.py              # Job 模型 + 内存 JobManager
│   └── __main__.py          # python -m web 启动本地服务
├── frontend/                # 前端源码（React + Vite + TS）
│   ├── src/
│   └── package.json
├── tests/
├── docs/                    # 用户原始 .docx（gitignore）
├── docs_cleaned/            # 处理输出（gitignore）
├── ARCHITECTURE.md
└── pyproject.toml
```

## 2. 分层依赖

```
frontend (React)
    │  HTTP / WebSocket
    ▼
web/ (FastAPI) ── 复用 ──► src/doctools/batch.py ──► docx.py
```

- `cli.py` 和 `web/app.py` 都调用 `batch.build_plan` / `batch.process_batch`，唯一的差别是进度回调（打印 vs 推 WebSocket）。
- 处理核心对消费者透明：同一个 `process_batch`，CLI 同步跑，Web 丢进后台线程。

## 3. 批量编排层（batch.py）

```python
@dataclass
class FileResult:
    src: Path
    dst: Path
    ok: bool
    error: str | None = None

ProgressFn = Callable[[int, int, FileResult], None]

def discover_docx(src: Path, recursive: bool = False) -> list[Path]   # glob / rglob
def build_plan(src, dst=None, recursive=False) -> list[tuple[Path, Path]]
def process_batch(plan, on_progress: ProgressFn | None = None) -> list[FileResult]
```

- **递归**：`discover_docx` 用 `rglob` 时，输出路径镜像源目录结构（`out_dir / f.relative_to(src)`）；非递归保持平铺。
- **隔离**：单文件失败捕获进 `FileResult.error`，不中断整批。
- **进度**：`on_progress(total, done, result)` 在每文件完成后回调。

## 4. Web 后端（web/，绑定 127.0.0.1）

| 端点 | 作用 |
|------|------|
| `GET /` | 托管前端构建产物 |
| `GET /api/explore?dir=...` | 服务端列目录，供前端文件夹浏览 |
| `POST /api/scan` | 预扫描，返回 `.docx` 清单（名称 / 大小 / 是否递归） |
| `POST /api/jobs` | `{source_dir, output_dir, recursive, dry_run}` → 建 Job 后台处理 |
| `GET /api/jobs/{id}` | 轮询：状态 / 进度 / 逐文件结果 |
| `WS /api/jobs/{id}/ws` | 实时进度流 |

- **Job 模型**：内存字典 + 后台线程，本地单用户无需数据库。
- **交互模型是"目录路径"而非"文件上传"**：浏览器拿不到真实磁盘路径，本地场景下由用户填路径 / 目录浏览，后端直接按路径读盘。

#### 为什么自研目录浏览器，而不是调用系统文件对话框

本地/桌面工具（Word、资源管理器）能直接调系统文件对话框拿绝对路径，因为它们跑在
操作系统上、有系统权限。我们的界面跑在**浏览器**里，而浏览器出于安全**故意不暴露
文件的绝对路径**：

- `<input type="file">` 弹的是系统风格的对话框，但只返回一个 `File` 对象——**仅有
  文件名、没有路径**；旧版 Chrome 的 `file.path` 早已移除。
- File System Access API（`showOpenFilePicker`）同样只给受限的文件句柄，不给绝对
  路径，且仅 Chrome/Edge 支持。

而后端 `process_batch` 是**按路径直读本机磁盘**（"本地磁盘 → 本地磁盘"），所以必须
让后端知道"文件在哪"。两条路：

1. **自研目录浏览器**（本项目方案）：后端 `GET /api/explore` 直接列目录，前端渲染
   出文件树。这正是 Jupyter、VS Code 网页版、Home Assistant 等所有本地网页工具的
   通用做法。优点：能拿到真实路径，可做盘符切换 / 按扩展名过滤 / 隐藏 `$` 系统目录，
   且文件全程不离开本机。缺点：UI 需要自己打磨，做不到系统对话框的原生观感。
2. **文件上传模式**：用 `<input type="file">` 把文件内容发给后端处理。代价是整份
   文件经 HTTP 复制（大文件低效）、目录批量需 Chrome 专用的 `webkitdirectory`、
   且与"文件不离开本机"的定位相悖。

**若将来要原生对话框体验**：只能把前端打包成桌面应用（Tauri / Electron），由底层
进程调用系统 API 拿绝对路径——代价是从"浏览器打开即用"变成"需安装应用"。

**结论**：在"本地优先、后端直读磁盘"的架构下，自研目录浏览器是正确的取舍；等真正
演变成线上 BS（文件上传 + 对象存储）时，再切换到 `<input type="file">` 即可
（见 §6 演进路径）。

## 5. 前端（frontend/）

- 技术栈：React + Vite + TypeScript。
- 页面流：目录选择 → 扫描预览（文件数 / 大小）→ 选项（dry-run / 输出目录 / 递归）→ 进度视图（进度条 + 逐文件 OK/FAIL）→ 完成。
- 开发时 Vite dev server 代理 `/api` 到本地后端；生产由 FastAPI 托管 `frontend/dist`。

## 6. 演进路径：本地 → 线上 BS

| 现在（本地 Web UI） | 将来（线上 BS） |
|---------------------|-----------------|
| 目录路径输入 | 文件上传 + 对象存储 |
| 内存 JobManager | Redis + 任务队列（ARQ / Celery） |
| `process_batch` 跑在后台线程 | 同一函数丢进 worker |
| 无认证 | 用户认证 |

`POST /api/jobs` 接口形状不变，前端基本不动；核心 `batch.py` / `docx.py` 一行不改。

## 7. 已知边界

- 单目录/单线程是全量顺序处理；`process_batch` 预留 `workers` 扩展位（`ThreadPoolExecutor`）但当前恒为 1。
- 不做去重/幂等：每次全量重跑。
- 文件被 Word 占用会记为单文件 `[FAIL]`，不拖垮整批。
