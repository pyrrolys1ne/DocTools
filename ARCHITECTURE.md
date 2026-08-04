# DocTools 架构

> 定位：**本地优先的批量文档处理工具**。本地形态是"后端托管前端 + 按路径直读磁盘"，
> 结构上已预留线上 BS（前后端分离部署、任务存储抽象、API 版本化）的演进空间。

## 0. 核心原则

`doctools` 永远是**纯库**，Web / CLI 只是它的壳。

- `src/doctools/` 下不依赖任何 Web 或 CLI 框架，保证可被任何消费方复用。
- CLI 与 Web 后端共享同一套批量编排层（`batch.py`）与操作注册表，避免各实现一遍循环逻辑。
- 数据流是"本地磁盘 → 本地磁盘"：输入目录、输出目录都在用户机器上，文件不离开本机。
- 交互模型是**目录路径**而非文件上传：浏览器拿不到真实磁盘路径，本地场景下由用户填路径 /
  目录浏览（自研浏览器），后端直接按路径读盘。

## 1. 仓库结构

```
DocTools/
├── src/doctools/                  # 纯库（不依赖任何 Web/CLI 框架）
│   ├── model.py                   # 领域常量（各格式后缀表）+ FileResult / ProgressFn
│   ├── docx.py                    # Word 页眉/页脚移除（含横线）
│   ├── pdf.py                     # PDF 合并 / 拆分（pypdf）
│   ├── pdf_convert.py             # PDF → Word / PPT / 图片（pdf2docx / PyMuPDF）
│   ├── images.py                  # 图片多合一 PDF、图片压缩（Pillow）
│   ├── office.py                  # Word/PPT → PDF（Office COM，仅 Windows）
│   ├── batch.py                   # 编排层：discover / 计划构建 / 操作注册表 run_operation
│   └── cli.py                     # 瘦壳：注册全部命令，只消费 batch.py
├── web/                           # 本地 Web 后端（FastAPI）
│   ├── __init__.py
│   ├── config.py                  # pydantic-settings 配置（环境变量前缀 DOCTOOLS_）
│   ├── app.py                     # 组装：CORS + 路由挂载 + 静态托管 + /api/health
│   ├── schemas.py                 # Pydantic 请求/响应模型（JobRequest / JobResponse）
│   ├── jobs.py                    # Job 模型 + JobStore 协议 + 内存 JobManager
│   ├── routers/
│   │   ├── explore.py             # /drives /explore（目录浏览）
│   │   └── jobs.py                # /jobs 创建/查询/WS 进度流
│   └── __main__.py                # python -m web 启动本地服务
├── frontend/                      # 前端（React + Vite + TS，Tailwind v4 + shadcn/ui）
│   └── src/
│       ├── App.tsx                # 顶层壳：页面路由 + 任务状态展示
│       ├── api.ts                 # API 客户端（VITE_API_BASE 可配，默认同源 /api/v1）
│       ├── DirectoryPicker.tsx    # 自研目录浏览器弹窗
│       ├── config/operations.ts   # 操作注册表：宫格/占位文案/扩展名/类型
│       ├── hooks/                 # useJob / useRecents / usePicker
│       ├── components/            # BatchForm / JobStatus / OperationHeader / form 原语
│       └── pages/                 # HomePage / BatchPage / MergePdfPage / SplitPdfPage / …
├── tests/
├── ARCHITECTURE.md
└── pyproject.toml
```

## 2. 核心：操作注册表（batch.py）

所有功能都是"一个操作"，集中登记在 `OPERATION_HANDLERS` 注册表：

```python
# 每个 handler 签名：(op, params: OpParams) -> list[FileResult]
OPERATION_HANDLERS: dict[str, Callable[[str, OpParams], list[FileResult]]] = {
    "remove-headers": _handle_remove_parts,
    "word-to-pdf":    _handle_office_convert,
    "pdf-to-word":    _handle_pdf_to_office,
    "merge-pdf":      _handle_merge_pdf,
    "split-pdf":      _handle_split_pdf,
    # …共 13 个
}

def run_operation(operation, *, source_path, output_path, …, on_progress) -> list[FileResult]:
    handler = OPERATION_HANDLERS.get(operation)
    if handler is None:
        raise ValueError(f"未知操作：{operation}")
    return handler(operation, OpParams(…))
```

- **新增操作** = 写一个 handler + 在注册表登记一行；CLI 命令与 Web 表单复用同一注册表。
- **统一参数**：`OpParams`（源路径 / 输出路径 / 递归 / dry-run / 多选源 / 页码范围 / 质量）跨操作复用。
- **逐文件容错**：`process_batch` 单文件失败只记入 `FileResult.error`，不中断整批。
- **dry-run**：只构建处理计划、报告不执行，CLI 与 Web 共用。

### 操作清单

| 操作 | 说明 | 引擎 |
|------|------|------|
| `remove-headers` / `remove-footers` / `remove-headers-footers` | Word 去页眉/页脚（含横线） | python-docx |
| `word-to-pdf` / `ppt-to-pdf` | Office → PDF | Office COM（需本机 Office） |
| `image-to-pdf` | 图片多合一 PDF | Pillow |
| `pdf-to-word` / `pdf-to-ppt` | PDF → Office（有损） | pdf2docx / PyMuPDF |
| `pdf-to-images` | PDF 每页一张 PNG | PyMuPDF |
| `compress-images` | 图片压缩（可选质量） | Pillow |
| `merge-pdf` / `split-pdf` | PDF 合并 / 拆分 | pypdf |
| `to-pdf` | 混合转换（**已弃用**，兼容保留） | Office COM |

## 3. Web 后端（web/，绑定 127.0.0.1）

### 配置（config.py）

`DOCTOOLS_` 前缀环境变量 / `.env` 文件，`extra="ignore"` 容忍无关变量：

| 配置 | 默认 | 说明 |
|------|------|------|
| `DOCTOOLS_HOST` / `PORT` | `127.0.0.1` / `8000` | 监听地址 |
| `DOCTOOLS_SERVE_FRONTEND` | `true` | 后端是否一并托管前端构建产物 |
| `DOCTOOLS_FRONTEND_DIR` | `frontend/dist` | 前端构建产物目录 |
| `DOCTOOLS_CORS_ORIGINS` | `localhost:5173,…` | 前后端分离时允许的跨域来源 |

所有接口统一挂在 **`/api/v1`** 版本前缀下（见 `config.API_PREFIX`）。

### 端点

| 端点 | 作用 |
|------|------|
| `GET /api/health` | 健康检查（部署探测），返回服务信息 |
| `GET /api/v1/drives` | 盘符 + 特殊文件夹（桌面/文档/下载） |
| `GET /api/v1/explore?dir=&exts=` | 服务端列目录，供前端文件夹浏览 |
| `POST /api/v1/jobs` | `JobRequest` → 建 Job 后台处理，返回任务快照 |
| `GET /api/v1/jobs/{id}` | 查询状态 / 进度 / 逐文件结果 |
| `WS /api/v1/jobs/{id}/ws` | 实时进度流（状态变化即推送） |
| `GET /` | 托管前端构建产物（本地形态） |

- **Job 模型**（jobs.py）：内存字典 + 后台线程，本地单用户无需数据库。
  - `Job.to_dict()` 给出 GET 与 WS 共用的统一快照形状（`schemas.JobResponse` 由它构建）。
  - 每次进度更新或任务结束触发 `Job.updated` 事件，WS 处理器阻塞等待事件后推送一次，
    替代固定间隔轮询。
  - 已结束任务保留 `JOB_TTL_SECONDS`（1h）后自动清理，防常驻服务内存泄漏。
  - `JobStore` Protocol 抽象了存储接口：换成 Redis + 任务队列时接口形状不变。

#### 为什么自研目录浏览器，而不是调用系统文件对话框

本地/桌面工具（Word、资源管理器）能直接调系统文件对话框拿绝对路径，因为它们跑在
操作系统上、有系统权限。我们的界面跑在**浏览器**里，而浏览器出于安全**故意不暴露
文件的绝对路径**：

- `<input type="file">` 弹的是系统风格的对话框，但只返回一个 `File` 对象——**仅有
  文件名、没有路径**；旧版 Chrome 的 `file.path` 早已移除。
- File System Access API（`showOpenFilePicker`）同样只给受限的文件句柄，不给绝对
  路径，且仅 Chrome/Edge 支持。

而后端 `run_operation` 是**按路径直读本机磁盘**（"本地磁盘 → 本地磁盘"），所以必须
让后端知道"文件在哪"。两条路：

1. **自研目录浏览器**（本项目方案）：后端 `GET /api/v1/explore` 直接列目录，前端渲染
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

## 4. 前端（frontend/）

- 技术栈：React + Vite + TypeScript，Tailwind CSS v4 + shadcn/ui。
- **App.tsx 只是薄壳**：品牌头部 + 页面路由（首页宫格 / 各功能页）+ 统一的任务状态展示。
- **config/operations.ts 是操作注册表**：宫格条目、源/输出占位文案、扩展名过滤、质量档位，
  页面组件只读取、不重复维护。
- **hooks/**：`useJob`（创建任务 + WebSocket 进度 + 轮询回退）、`useRecents`（localStorage
  记住上次路径）、`usePicker`（目录浏览弹窗的统一封装）。
- **pages/**：每个功能一个页面，只管理自己的表单状态；`BatchPage` 复用 `BatchForm` 覆盖
  去页眉/去页脚、各转 PDF、图片转 PDF、图片压缩；`MergePdfPage` / `SplitPdfPage` /
  `PdfToImagesPage` 是各自独立的专用表单。
- **api.ts**：`VITE_API_BASE` 环境变量可配置 API 基地址（默认同源 `/api/v1`），
  支持前后端分离部署。
- 开发时 Vite dev server 代理 `/api` 到本地后端（含 WebSocket）；生产由 FastAPI 托管
  `frontend/dist`（单进程）。

## 5. 部署形态

**本地工具（默认）**：一个进程即完整可用。

```bash
cd frontend && npm run build   # 构建前端产物
python -m web                  # http://127.0.0.1:8000 即是界面
```

**纯 API / 前后端分离**：

```bash
DOCTOOLS_SERVE_FRONTEND=false python -m web        # 只提供 /api/v1，"/" 返回服务信息
# 前端由独立静态站托管，构建时指定后端地址：
VITE_API_BASE=https://api.example.com/api/v1 npm run build
```

## 6. 演进路径：本地 → 线上 BS

| 现在（本地 Web UI） | 将来（线上 BS） |
|---------------------|-----------------|
| 目录路径输入 | 文件上传 + 对象存储 |
| 内存 JobManager | Redis + 任务队列（实现同一 `JobStore` 协议） |
| `run_operation` 跑在后台线程 | 同一函数丢进 worker |
| 无认证 | 用户认证 |
| `/api/v1` 单版本 | 新增 `/api/v2`，`/api/v1` 兼容保留 |

`POST /api/v1/jobs` 接口形状不变，前端基本不动；核心 `batch.py` / 各引擎模块一行不改。

## 7. 已知边界

- 单目录/单线程是全量顺序处理；`process_batch` 未做并发（预留 `ThreadPoolExecutor` 扩展位）。
- 不做去重/幂等：每次全量重跑。
- 文件被 Word 占用会记为单文件 `[FAIL]`，不拖垮整批。
- 转 PDF 依赖本机 Microsoft Office（COM）；PDF → Word 为有损转换，扫描件需先 OCR。
