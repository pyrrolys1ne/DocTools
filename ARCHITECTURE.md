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
