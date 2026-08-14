# DocTools

本地优先的批量文档处理工具，提供命令行、Windows 桌面客户端与本地 Web API。支持 Word 页眉/页脚移除、Office 与 PDF 互转、扫描 OCR、PDF 表格提取、图片处理等 15 项操作，所有文件均在本机处理，不上传。

## 目录

- [功能特性](#功能特性)
- [环境要求](#环境要求)
- [安装](#安装)
- [命令行使用](#命令行使用)
- [桌面客户端使用](#桌面客户端使用)
- [Web API 调试](#web-api-调试)
- [服务配置](#服务配置)
- [架构](#架构)
- [开发](#开发)
- [许可](#许可)

## 功能特性

| 功能 | CLI 命令 | 说明 |
|------|----------|------|
| Word 去页眉 | `remove-headers` | 含文字旁横线（段落边框 + Header 样式边框） |
| Word 去页脚 | `remove-footers` | 同上 |
| Word 去页眉页脚 | `remove-headers-footers` | 一次完成 |
| Word → PDF | `word-to-pdf` | 优先 Office COM，回退 LibreOffice |
| PPT → PDF | `ppt-to-pdf` | 同上 |
| 图片 → PDF | `image-to-pdf` | 多张图片合成一个 PDF（每张一页，可调整顺序） |
| PDF → Word | `pdf-to-word` | pdf2docx 有损转换；引擎失败回退文字提取；扫描件自动 OCR |
| PDF → PPT | `pdf-to-ppt` | 每页渲染为一张幻灯片 |
| PDF → Excel | `pdf-to-excel` | 表格提取到一个 Excel（每张表一个 sheet） |
| PDF → Markdown | `pdf-to-markdown` | MinerU 在线解析（可选，需配置 API） |
| PDF → 图片 | `pdf-to-images` | 每页导出一张 PNG |
| 图片压缩 | `compress-images` | JPEG 重编码，其余转优化 PNG，可选质量 |
| 图片格式互转 | `convert-images` | png / jpg / webp / bmp / gif / tiff 互转 |
| PDF 合并 | `merge-pdf` | 按命令行顺序合并为单个 PDF |
| PDF 拆分 | `split-pdf` | 每页一个，或按自定义页码范围 |

通用能力：

- **递归处理**子目录（`--recursive`），输出目录镜像源目录结构；
- **单文件失败不中断整批**，逐文件上报 OK/FAIL（带稳定错误码）；
- **结构化错误码**：CLI / Web / 桌面端共用（如 `PDF_NO_TEXT`、`OFFICE_NOT_INSTALLED`、`RESOURCE_LIMIT_EXCEEDED`）；
- **资源预算**：PDF 页数上限、图片合并像素预算等（`DOCTOOLS_*` 环境变量可调）；
- **双引擎转 PDF**：Word/PPT → PDF 优先 Office COM（保真度最高），未装时自动回退 LibreOffice；
- **扫描 OCR**：扫描版 PDF 转 Word 时自动 OCR 识别（RapidOCR，需 `[ocr]`）。

## 环境要求

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | ≥ 3.10 | 核心库、CLI 与 Web API 运行环境 |
| .NET 8 SDK（可选） | ≥ 8.0 | 构建桌面客户端 |
| Microsoft Office（可选） | Windows 桌面版 | `word-to-pdf` / `ppt-to-pdf` 优先走 COM |
| LibreOffice（可选） | 便携版或系统安装 | `word-to-pdf` / `ppt-to-pdf` 的回退引擎 |

## 安装

从源码安装（推荐）：

```bash
git clone git@github.com:pyrrolys1ne/DocTools.git
cd DocTools
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev,web]"    # 完整安装（含测试工具与 Web 后端）
pip install -e ".[office]"     # 启用 Word/PPT → PDF（优先 Office COM）
pip install -e ".[ocr]"        # 启用扫描件 OCR（RapidOCR，模型首次运行自动下载）
```

可用 extras：

| Extra | 内容 |
|-------|------|
| （默认） | 核心处理功能（pdf2docx、PyMuPDF、python-docx、python-pptx、pypdf、Pillow、Typer） |
| `dev` | pytest、reportlab、ruff |
| `web` | FastAPI、uvicorn、pydantic-settings |
| `office` | pywin32（Word/PPT → PDF，仅 Windows） |
| `ocr` | rapidocr、onnxruntime（扫描件 OCR） |

## 命令行使用

去页眉 / 页脚（单文件或目录批量）：

```bash
doctools remove-headers 文档.docx -o 文档_clean.docx
doctools remove-headers ./docs -o ./docs_cleaned
doctools remove-footers ./docs -o ./docs_cleaned
doctools remove-headers-footers ./docs -o ./docs_cleaned --recursive
```

Office → PDF：

```bash
doctools word-to-pdf 文档.docx -o 输出目录
doctools ppt-to-pdf ./slides -o ./slides_pdf --recursive
```

图片处理：

```bash
doctools image-to-pdf ./图片 -o 输出目录      # 目录内所有图片合成一个 PDF
doctools compress-images ./图片 -o 输出目录 -q 60
doctools convert-images ./图片 -o 输出目录 --to webp
```

PDF → Word / PPT / Excel / Markdown / 图片：

```bash
doctools pdf-to-word 文档.pdf -o 输出目录
doctools pdf-to-ppt 幻灯片.pdf -o 输出目录
doctools pdf-to-excel 表格.pdf -o 输出目录
doctools pdf-to-markdown 文档.pdf -o 输出目录   # 需配置 MinerU API
doctools pdf-to-images 文档.pdf -o 输出目录
```

PDF 合并 / 拆分：

```bash
doctools merge-pdf 1.pdf 2.pdf 3.pdf -o merged.pdf
doctools split-pdf 文档.pdf -o ./拆分结果
doctools split-pdf 文档.pdf -o ./拆分结果 --ranges "1-3,5,8-12"
```

> 旧命令 `doctools to-pdf ...` 已弃用（混合转换），请改用 `word-to-pdf` / `ppt-to-pdf`。

各命令详细选项见 `doctools <命令> --help`。

## 桌面客户端使用

桌面客户端是 C/S 形态：`DocTools.exe`（WPF）启动时自动拉起随包的本地 API 服务 `docserver\docserver.exe`（由 `web/` 后端用 PyInstaller 打包），处理完成后随程序退出关闭。交互模型与命令行一致：填写/浏览本地路径，不涉及文件上传。

界面特点：

- 卡片式主页按输入格式分类（PDF / Word / 图片 / PPT），点击进入具体功能；
- 自动检测本机引擎能力，不可用的操作自动禁用并提示原因；
- 图片转 PDF 支持队列上移/下移，页序跟随队列；
- 浅色/深色主题（默认跟随系统），主题与各操作最近使用的路径自动记住（`%AppData%\DocTools\settings.json`）；
- 启动静默检查更新（标题栏"检查更新"按钮可手动触发），标题栏"导出诊断报告"一键导出版本/能力/环境诊断。

构建与打包（Windows，需 .NET 8 SDK）：

```bash
.\packaging\package.ps1            # 构建 docserver + DocTools.exe 并打包为 zip
.\packaging\build_installer.ps1    # 额外生成 Inno Setup 安装器（需 Inno Setup 6）
.\packaging\smoke_test.ps1         # 对打包产物做冒烟测试（真实跑一次 pdf-to-word）
.\packaging\download_libreoffice.ps1 -Url <paf.exe>  # 下载便携版 LibreOffice 作兜底引擎
```

产物为 `dist\DocTools-win-x64.zip`（解压即用）与 `dist\DocTools-Setup-{version}-x64.exe`（安装器，含快捷方式与卸载入口）。目录结构：

```
DocTools.exe        桌面客户端
docserver\          本地 API 服务（PyInstaller onedir）
README.txt          使用说明
```

### 发布新版本

打 tag 自动触发 CI 构建并发布（tag 需 `v*` 前缀）：

```bash
git tag v1.3.0
git push origin v1.3.0
```

`.github/workflows/package.yml` 在 `windows-latest` 上构建 docserver + WPF 客户端，组装
`DocTools-win-x64.zip` 与 `DocTools-Setup-{version}-x64.exe` 后自动创建 GitHub Release。
正式包以 CI 产物为准；本地 `dist\` 构建仅用于发布前预演。

## Web API 调试

`web/` 后端保留为个人开发调试工具：提供 `/api/v1` 接口与 `/docs` 调试文档，不托管前端。

```bash
python -m web                           # http://127.0.0.1:8000，打开 /docs 调试
python -m web --port 0                  # 自动选择空闲端口，stdout 打印 DOCSERVER_PORT=<port>
```

桌面客户端即通过该 API 通信（REST 创建/查询任务 + WebSocket 进度流），接口形状见 `web/schemas.py`。

## 服务配置

Web 服务通过环境变量配置（前缀 `DOCTOOLS_`，也支持 `.env` 文件），全部配置见 `web/config.py`：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `DOCTOOLS_HOST` | `127.0.0.1` | 监听地址 |
| `DOCTOOLS_PORT` | `8000` | 监听端口；桌面客户端传 `--port 0` 自动选端口 |
| `DOCTOOLS_RELOAD` | `false` | 开发调试时热重载（打包环境必须关闭） |
| `DOCTOOLS_CORS_ORIGINS` | `http://localhost:5173,…` | 浏览器跨域调试来源（逗号分隔） |
| `DOCTOOLS_MAX_PDF_PAGES` | `1000` | PDF 转换页数上限（超限报 `PDF_PAGE_LIMIT`） |
| `DOCTOOLS_PDF_IMAGE_MAX_PIXELS` | `50000000` | PDF 单页渲染像素预算 |
| `DOCTOOLS_IMAGE_TO_PDF_MAX_PIXELS` | `100000000` | 图片合并 PDF 累计解码预算 |
| `DOCTOOLS_MINERU_API_URL` | （空） | MinerU 在线 API 地址（自建 mineru-api 或 mineru.net） |
| `DOCTOOLS_MINERU_TOKEN` | （空） | mineru.net 官方 API Token（可选） |
| `DOCTOOLS_LIBREOFFICE_PATH` | （空） | 手动指定 soffice.exe 路径 |

API 统一挂在 `/api/v1` 前缀下；健康检查为 `GET /api/health`。
辅助接口：`GET /api/v1/capabilities`（引擎能力 + 资源预算）、`GET /api/v1/diagnostics`（诊断报告）。

## 架构

见 [ARCHITECTURE.md](ARCHITECTURE.md)。要点：

- 核心为纯库（`src/doctools/`），不依赖任何 Web / CLI 框架，可被任意消费方复用；
- 所有操作集中在 `OPERATION_HANDLERS` 注册表，CLI 与 Web（以及桌面客户端经 API）共享同一编排层（`batch.py`）；
- 引擎抽象：Word/PPT → PDF 走 `create_pdf_engine()`（COM 优先、LibreOffice 兜底）；扫描 OCR、MinerU 为可选引擎，惰性加载；
- 三种消费形态：CLI（`src/doctools/cli.py`）、本地 Web API（`web/`，开发调试）、Windows 桌面客户端（`desktop/`，C/S 产品形态）。

## 开发

```bash
pytest                                            # 运行后端与库测试
ruff check .                                      # 代码检查
dotnet build desktop\DocTools\DocTools.csproj     # 桌面客户端编译检查
dotnet run --project desktop\DocTools\DocTools.csproj  # 桌面客户端 UI 预览
```

提交规范见 [CONTRIBUTING.md](CONTRIBUTING.md)（Conventional Commits，提交消息统一英文）。

## 许可

[MIT](LICENSE) © 2026 pyrrolys1ne
