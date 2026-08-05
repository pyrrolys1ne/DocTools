# DocTools 架构

> 定位：**本地优先的批量文档处理工具**。产品形态是 Windows 桌面客户端（C/S）：
> `DocTools.exe` 拉起随包的本机 API 服务（`docserver.exe`），按路径直读磁盘。
> Web 后端保留为个人开发调试工具；线上 BS（前后端分离、任务队列）作为远期演进空间。

## 0. 核心原则

`doctools` 永远是**纯库**，Web API / CLI / 桌面客户端只是它的壳。

- `src/doctools/` 下不依赖任何 Web 或 CLI 框架，保证可被任何消费方复用。
- CLI 与 Web 后端共享同一套批量编排层（`batch.py`）与操作注册表；桌面客户端经
  `/api/v1` 复用同一编排层，三端不会各实现一遍循环逻辑。
- 数据流是"本地磁盘 → 本地磁盘"：输入目录、输出目录都在用户机器上，文件不离开本机。
- 交互模型是**目录路径**而非文件上传：桌面客户端用系统原生对话框拿绝对路径，
  Web 调试用自研目录浏览 API（`/api/v1/explore`），后端一律按路径读盘。

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
├── web/                           # 本地 API 服务（FastAPI，开发调试）
│   ├── __init__.py
│   ├── config.py                  # pydantic-settings 配置（环境变量前缀 DOCTOOLS_）
│   ├── app.py                     # 组装：CORS + 路由挂载 + /api/health + 根路径服务信息
│   ├── schemas.py                 # Pydantic 请求/响应模型（JobRequest / JobResponse）
│   ├── jobs.py                    # Job 模型 + JobStore 协议 + 内存 JobManager
│   ├── routers/
│   │   ├── explore.py             # /drives /explore（目录浏览，Web 调试用）
│   │   └── jobs.py                # /jobs 创建/查询/WS 进度流
│   └── __main__.py                # python -m web；--port 0 时打印 DOCSERVER_PORT=
├── desktop/                       # 桌面客户端（C# / .NET 8 / WPF，Windows）
│   └── DocTools/
│       ├── App.xaml(.cs)          # 启动：拉起 docserver.exe，退出时关闭
│       ├── MainWindow.xaml(.cs)   # 主窗口（操作列表 + 表单 + 进度 + 结果表）
│       ├── Models/                # JobRequest / JobStatus / FileResult / 操作定义
│       ├── Services/              # DocServer（子进程管理）/ DocToolsApi（HTTP）/ JobWatcher（WS+轮询）
│       └── ViewModels/            # MainViewModel / RelayCommand
├── packaging/                     # 打包与分发脚本
│   ├── docserver_entry.py         # PyInstaller 入口（复用 web/__main__.main）
│   ├── docserver.spec             # PyInstaller spec（onedir 控制台程序）
│   ├── build_server.ps1           # 构建 docserver.exe
│   ├── build_client.ps1           # dotnet publish 桌面客户端
│   ├── package.ps1                # 组装 DocTools-win-x64.zip
│   └── README.txt                 # 随分发包的使用说明
├── frontend/                      # 旧 React 前端（已归档，tag archive/frontend-v0.3）
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
| `pdf-to-word` / `pdf-to-ppt` | PDF → Office | pdf2docx / PyMuPDF / python-pptx |
| `pdf-to-images` | PDF 每页导出 PNG | PyMuPDF |
| `compress-images` | 图片压缩 | Pillow |
| `merge-pdf` / `split-pdf` | PDF 合并 / 拆分 | pypdf |

## 3. 桌面客户端（desktop/）

C/S 形态：客户端只负责交互，处理全部由本地 API 服务完成。

- **服务生命周期**（`Services/DocServer.cs`）：启动时在应用目录下查找
  `docserver\docserver.exe`（或同目录 `docserver.exe`），以 `--port 0` 拉起，
  从 stdout 读取 `DOCSERVER_PORT=<port>` 确定实际端口；应用退出时 `Kill` 子进程。
- **API 客户端**（`Services/DocToolsApi.cs`）：REST 创建/查询任务；
  **进度订阅**（`Services/JobWatcher.cs`）优先 WebSocket，失败回退 500ms 轮询。
- **表单模型**：12 个操作（后端 13 个中除遗留 `to-pdf`），批量操作复用统一表单，
  合并 / 拆分 / PDF 转图片用专用表单；路径选择用系统原生对话框。
- **任务状态**：`MainViewModel` 维护 `idle / running / done / failed` 状态机，
  进度条按 `done/total` 推进，结果表逐文件展示 OK/FAIL。

## 4. Web 后端（web/，开发调试）

无头本地服务：只提供 `/api/v1` 接口与 `/docs` 调试文档，不托管前端。
桌面客户端与浏览器调试共用同一套 API。

### 配置

`web/config.py`：`DOCTOOLS_` 前缀环境变量 / `.env` 文件，`extra="ignore"` 容忍无关变量：

| 配置 | 默认 | 说明 |
|------|------|------|
| `DOCTOOLS_HOST` / `PORT` | `127.0.0.1` / `8000` | 监听地址 |
| `DOCTOOLS_RELOAD` | `false` | 开发调试热重载（打包环境必须关闭） |
| `DOCTOOLS_CORS_ORIGINS` | `localhost:5173,…` | 浏览器跨域调试来源（桌面客户端不走 CORS） |

所有接口统一挂在 **`/api/v1`** 版本前缀下（见 `config.API_PREFIX`）。

### 端点

| 端点 | 作用 |
|------|------|
| `GET /api/health` | 健康检查（部署探测），返回服务信息 |
| `GET /api/v1/drives` | 盘符 + 特殊文件夹（桌面/文档/下载） |
| `GET /api/v1/explore?dir=&exts=` | 服务端列目录（Web 调试用） |
| `POST /api/v1/jobs` | `JobRequest` → 建 Job 后台处理，返回任务快照 |
| `GET /api/v1/jobs/{id}` | 查询状态 / 进度 / 逐文件结果 |
| `WS /api/v1/jobs/{id}/ws` | 实时进度流（状态变化即推送） |
| `GET /` | 服务信息（调试确认服务就绪） |

- **启动契约**：`python -m web --port 0` 自动选择空闲端口，并在 stdout 首行打印
  `DOCSERVER_PORT=<port>`，供桌面客户端（子进程）读取；固定端口调试用
  `DOCTOOLS_PORT` 或 `--port`。
- **Job 模型**（jobs.py）：内存字典 + 后台线程，本地单用户无需数据库。
  - `Job.to_dict()` 给出 GET 与 WS 共用的统一快照形状（`schemas.JobResponse` 由它构建）。
  - 每次进度更新或任务结束触发 `Job.updated` 事件，WS 处理器阻塞等待事件后推送一次，
    替代固定间隔轮询。
  - 已结束任务保留 `JOB_TTL_SECONDS`（1h）后自动清理，防常驻服务内存泄漏。
  - `JobStore` Protocol 抽象了存储接口：换成 Redis + 任务队列时接口形状不变。

### 目录浏览 API 与原生对话框（历史决策）

早期 Web UI 运行在浏览器里，浏览器出于安全**故意不暴露文件的绝对路径**
（`<input type="file">` 只有文件名、没有路径），所以后端提供了自研目录浏览器
（`GET /api/v1/explore`，隐藏 `$` 系统目录、按扩展名过滤）。

**现状**：桌面客户端跑在操作系统上，直接使用系统原生对话框
（WPF `OpenFolderDialog` / `OpenFileDialog`）拿绝对路径，不再需要目录浏览 API；
`explore` 端点保留给 Web 调试场景。若将来演变成线上 BS（文件上传 + 对象存储），
再切换到文件上传模型即可（见 §8）。

## 5. 前端（frontend/，已归档）

- 技术栈：React + Vite + TypeScript，Tailwind CSS v4 + shadcn/ui。
- 已随 C/S 化归档，tag `archive/frontend-v0.3`；源码保留但不构建、不随后端托管。
- 历史结构备忘：`App.tsx` 薄壳 + `config/operations.ts` 操作注册表 + `hooks/`
  （`useJob` WS+轮询回退）、`pages/` 每功能一页、`api.ts`（`VITE_API_BASE` 可配）。

## 6. 打包与分发（packaging/）

- **docserver**（PyInstaller onedir，控制台程序）：`docserver.spec` 以
  `docserver_entry.py` 为入口，显式 `import web.app` 让 FastAPI 应用进包；
  `hiddenimports` 覆盖 uvicorn / pydantic-settings / 各引擎惰性导入的三方库。
  **必须是 console 程序**——客户端要从 stdout 读端口行。
- **桌面客户端**（dotnet publish）：`build_client.ps1` 用 `win-x64` 自包含
  单文件发布，用户无需安装 .NET。
- **分发包**：`package.ps1` 组装 `dist\DocTools-win-x64\`（`DocTools.exe` +
  `docserver\` + `README.txt`）并压缩为 zip。
- CI：`.github/workflows/package.yml` 在 tag `v*` / 手动触发时于 windows-latest
  构建并上传 artifact。

## 7. 部署形态

**产品形态（桌面分发包）**：

```powershell
.\packaging\package.ps1     # 构建 docserver + DocTools.exe 并打包 zip
```

解压 `dist\DocTools-win-x64.zip` 后运行 `DocTools.exe`，本地服务随包自动启动与退出。

**开发调试（源码运行）**：

```bash
python -m web               # http://127.0.0.1:8000/docs 调试 API
python -m web --port 0      # 自动选端口，stdout 打印 DOCSERVER_PORT=<port>
doctools <操作> <路径>      # CLI 直接调试引擎
```

## 8. 演进路径

| 现在（C/S 桌面 + 本地调试） | 将来（线上 BS） |
|---------------------|-----------------|
| 目录路径输入 + 原生对话框 | 文件上传 + 对象存储 |
| 内存 JobManager | Redis + 任务队列（实现同一 `JobStore` 协议） |
| `run_operation` 跑在后台线程 | 同一函数丢进 worker |
| 无认证 | 用户认证 |
| `/api/v1` 单版本 | 新增 `/api/v2`，`/api/v1` 兼容保留 |

`POST /api/v1/jobs` 接口形状不变，桌面客户端基本不动；核心 `batch.py` / 各引擎模块一行不改。

## 9. 已知边界

- 单目录/单线程是全量顺序处理；`process_batch` 未做并发（预留 `ThreadPoolExecutor` 扩展位）。
- 不做去重/幂等：每次全量重跑。
- 文件被 Word 占用会记为单文件 `[FAIL]`，不拖垮整批。
- 转 PDF 依赖本机 Microsoft Office（COM）；PDF → Word 为有损转换，扫描件需先 OCR。
- 分发包体积较大（随包 Python 运行时 + PyMuPDF/pdf2docx 等），约为百 MB 级。
- 本地 API 服务固定绑定 `127.0.0.1`，仅本机可访问；docserver 端口由客户端随机指定。